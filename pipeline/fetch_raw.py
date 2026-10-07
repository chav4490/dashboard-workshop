"""Fetch the monthly trip files from the live source into data/raw/, the local cache.

Run from the repo root:

    uv run pipeline/fetch_raw.py

The source is the NYC Taxi and Limousine Commission trip record page, which is public and
needs no key. This script reads that page for the High Volume For-Hire Vehicle files it
lists, keeps the most recent MONTHS of them, and downloads only the ones that are not
already in the cache. A file that is already there is never downloaded again.

The files are served from a CDN that blocks clients making repeated or parallel requests,
so downloads run one at a time with a pause between them.
"""

import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_PAGE = "https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page"
FILE_LINK = re.compile(r'https://[^"\s]+/(fhvhv_tripdata_(\d{4}-\d{2})\.parquet)')
MONTHS = 12
PAUSE_SECONDS = 5
USER_AGENT = "Mozilla/5.0 (dashboard-workshop data refresh)"

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SUMMARIES = ROOT / "data" / "summaries"


def open_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=60)


def published_files():
    """The trip files the source page lists, as {month: url}."""
    with open_url(SOURCE_PAGE) as response:
        page = response.read().decode("utf-8", errors="replace")
    return {match.group(2): match.group(0) for match in FILE_LINK.finditer(page)}


def cached_months():
    """Months already in the cache, wherever under data/raw/ the file sits."""
    return {path.stem.rsplit("_", 1)[1] for path in RAW.rglob("fhvhv_tripdata_*.parquet")}


def download(url, destination):
    """Download one file. It only takes its final name once it has arrived whole."""
    partial = destination.with_name(destination.name + ".part")
    with open_url(url) as response, open(partial, "wb") as out:
        headers = dict(response.headers.items())
        expected = int(headers.get("Content-Length", 0))
        received = 0
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
            received += len(chunk)
    if expected and received != expected:
        partial.unlink()
        raise IOError(f"{destination.name}: got {received} bytes, expected {expected}")
    partial.replace(destination)
    # The response headers record when the source last changed the file.
    with open(destination.with_name(destination.name + ".headers.json"), "w", newline="\n") as f:
        json.dump(headers, f, indent=2)
        f.write("\n")
    return received


def main():
    published = published_files()
    if not published:
        sys.exit(f"No trip files found on {SOURCE_PAGE}. The page layout may have changed.")
    wanted = sorted(published)[-MONTHS:]
    have = cached_months()
    missing = [month for month in wanted if month not in have]
    print(f"Source lists {len(published)} months, latest {wanted[-1]}.")
    print(f"Cache has {len(have & set(wanted))} of the latest {len(wanted)}. To download: {len(missing)}.")

    for i, month in enumerate(missing):
        if i:
            time.sleep(PAUSE_SECONDS)
        url = published[month]
        name = url.rsplit("/", 1)[1]
        print(f"  downloading {name} ...", flush=True)
        size = download(url, RAW / name)
        print(f"  saved {name} ({size / 1e6:.0f} MB)")

    SUMMARIES.mkdir(parents=True, exist_ok=True)
    with open(SUMMARIES / "source.json", "w", newline="\n") as f:
        json.dump(
            {
                "source_page": SOURCE_PAGE,
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "latest_published_month": wanted[-1],
                "months_downloaded": missing,
            },
            f,
            indent=2,
        )
        f.write("\n")
    if missing:
        print("New data arrived. Rebuild the summaries: uv run pipeline/build_summaries.py")
    else:
        print("Nothing new. The cache is up to date with the source.")


if __name__ == "__main__":
    main()
