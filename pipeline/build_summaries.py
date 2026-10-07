"""Read the raw trip files in data/raw/ and write the small summary files in data/summaries/.

Run from the repo root:

    uv run pipeline/build_summaries.py

Every query runs over every row. Only counts, rates, medians and a few example rows are
written out, so the summaries can be committed while the raw files stay on this laptop.

Two runs over the same files write the same summaries, so a change in a summary always means
a change in the data. That is why medians are exact (read off a count of trips at each value)
rather than approximate, and why money sums are rounded to whole cents.
"""

import json
import time
from pathlib import Path

import duckdb

from rules import RULES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MONTHS = 12
OUT = ROOT / "data" / "summaries"

# A wait is only measured when the request is not after the pickup and the gap is under
# two hours. Anything else is a data quality finding, not a wait.
VALID_WAIT = "wait_s BETWEEN 0 AND 7200"

METRICS = f"""
    count(*) AS trips,
    count(*) FILTER (WHERE wait_s > 600 AND {VALID_WAIT}) AS waits_over_10min,
    count(*) FILTER (WHERE {VALID_WAIT}) AS waits_measured,
    round(sum(base_passenger_fare), 2) AS fares,
    round(sum(driver_pay), 2) AS driver_pay,
    round(sum(tips), 2) AS tips
"""

WAIT_COLUMNS = {"wait_p50_s": 0.5, "wait_p90_s": 0.9}


def quantiles(hist, keys, columns):
    """SQL for exact quantiles per group and company (plus 'All'), read off a table of counts.

    `hist` has one row per group, company and value `v`, with `n` trips at that value.
    `keys` maps each output column to the expression that builds it from `hist`.
    `columns` maps each output column to the quantile it holds, such as 0.5 for the median.
    """
    select = ", ".join(f"{expr} AS {name}" for name, expr in keys.items())
    names = ", ".join(keys)
    picks = ", ".join(f"min(v) FILTER (WHERE cum >= {q} * total) AS {name}" for name, q in columns.items())
    return f"""
        SELECT {names}, company, {picks}
        FROM (
            SELECT
                *,
                sum(n) OVER (PARTITION BY {names}, company ORDER BY v) AS cum,
                sum(n) OVER (PARTITION BY {names}, company) AS total
            FROM (
                SELECT {names}, coalesce(company, 'All') AS company, v, sum(n) AS n
                FROM (SELECT {select}, company, v, n FROM {hist})
                GROUP BY GROUPING SETS (({names}, company, v), ({names}, v))
            )
        )
        GROUP BY {names}, company
    """


def main():
    start = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    # The most recent MONTHS monthly files in the cache, wherever under data/raw/ they sit.
    by_name = {path.name: path for path in RAW.rglob("fhvhv_tripdata_*.parquet")}
    files = [by_name[name].as_posix() for name in sorted(by_name)[-MONTHS:]]
    if not files:
        raise SystemExit("No trip files in data/raw/. Run: uv run pipeline/fetch_raw.py")
    print(f"  reading {len(files)} files, {Path(files[0]).stem[-7:]} to {Path(files[-1]).stem[-7:]}")

    con.execute(f"""
        CREATE VIEW trips AS
        SELECT
            *,
            CASE hvfhs_license_num
                WHEN 'HV0003' THEN 'Uber'
                WHEN 'HV0005' THEN 'Lyft'
                ELSE hvfhs_license_num
            END AS company,
            strftime(pickup_datetime, '%Y-%m') AS month,
            regexp_extract(filename, '(\\d{{4}}-\\d{{2}})\\.parquet$', 1) AS file_month,
            date_diff('second', request_datetime, pickup_datetime) AS wait_s
        FROM read_parquet({files}, union_by_name = true, filename = true)
    """)

    # Counts of trips at each value, which the exact medians are read from.
    con.execute(f"""
        CREATE TEMP TABLE wait_hist AS
        SELECT
            CAST(pickup_datetime AS DATE) AS date,
            hour(pickup_datetime) AS hour,
            company,
            wait_s AS v,
            count(*) AS n
        FROM trips
        WHERE {VALID_WAIT}
        GROUP BY ALL
    """)
    con.execute("""
        CREATE TEMP TABLE time_hist AS
        SELECT month, company, trip_time AS v, count(*) AS n FROM trips GROUP BY ALL
    """)
    con.execute("""
        CREATE TEMP TABLE miles_hist AS
        SELECT month, company, round(trip_miles, 2) AS v, count(*) AS n FROM trips GROUP BY ALL
    """)
    print(f"  counted waits, trip times and distances ({time.time() - start:.0f}s)")

    def write_csv(name, sql):
        con.execute(f"COPY ({sql}) TO '{(OUT / name).as_posix()}' (HEADER, DELIMITER ',')")
        print(f"  wrote {name} ({time.time() - start:.0f}s)")

    # One row per month and company, plus an 'All' row per month.
    write_csv("monthly.csv", f"""
        SELECT a.*, w.wait_p50_s, w.wait_p90_s, m.miles_p50, t.trip_time_p50_s
        FROM (
            SELECT
                month,
                coalesce(company, 'All') AS company,
                count(DISTINCT CAST(pickup_datetime AS DATE)) AS days,
                {METRICS},
                count(*) FILTER (WHERE shared_request_flag = 'Y') AS shared_requests,
                count(*) FILTER (WHERE wav_request_flag = 'Y') AS wav_requests,
                count(*) FILTER (WHERE wav_request_flag = 'Y' AND wav_match_flag = 'Y') AS wav_requests_matched,
                count(*) FILTER (WHERE airport_fee > 0) AS airport_trips,
                count(*) FILTER (WHERE cbd_congestion_fee > 0) AS cbd_trips,
                count(*) FILTER (WHERE DOLocationID = 265) AS out_of_city_dropoffs
            FROM trips
            GROUP BY GROUPING SETS ((month, company), (month))
        ) a
        JOIN ({quantiles("wait_hist", {"month": "strftime(date, '%Y-%m')"}, WAIT_COLUMNS)}) w USING (month, company)
        JOIN ({quantiles("miles_hist", {"month": "month"}, {"miles_p50": 0.5})}) m USING (month, company)
        JOIN ({quantiles("time_hist", {"month": "month"}, {"trip_time_p50_s": 0.5})}) t USING (month, company)
        ORDER BY month, company
    """)

    write_csv("daily.csv", f"""
        SELECT a.*, w.wait_p50_s, w.wait_p90_s
        FROM (
            SELECT
                CAST(pickup_datetime AS DATE) AS date,
                coalesce(company, 'All') AS company,
                {METRICS}
            FROM trips
            GROUP BY GROUPING SETS ((CAST(pickup_datetime AS DATE), company), (CAST(pickup_datetime AS DATE)))
        ) a
        JOIN ({quantiles("wait_hist", {"date": "date"}, WAIT_COLUMNS)}) w USING (date, company)
        ORDER BY date, company
    """)

    # Hour of the week: weekday 1 is Monday, 7 is Sunday.
    write_csv("hourly.csv", f"""
        SELECT a.*, w.wait_p50_s, w.wait_p90_s
        FROM (
            SELECT
                isodow(pickup_datetime) AS weekday,
                hour(pickup_datetime) AS hour,
                coalesce(company, 'All') AS company,
                count(DISTINCT CAST(pickup_datetime AS DATE)) AS days,
                {METRICS}
            FROM trips
            GROUP BY GROUPING SETS (
                (isodow(pickup_datetime), hour(pickup_datetime), company),
                (isodow(pickup_datetime), hour(pickup_datetime))
            )
        ) a
        JOIN ({quantiles("wait_hist", {"weekday": "isodow(date)", "hour": "hour"}, WAIT_COLUMNS)}) w
            USING (weekday, hour, company)
        ORDER BY weekday, hour, company
    """)

    # Data quality: every rule over every row, in one pass.
    fails = ",\n            ".join(
        f"count(*) FILTER (WHERE {r['predicate']}) AS \"{r['id']}\"" for r in RULES
    )
    any_fail = " OR ".join(f"({r['predicate']})" for r in RULES)
    rows = con.execute(f"""
        SELECT
            month,
            company,
            count(*) AS rows_checked,
            count(*) FILTER (WHERE {any_fail}) AS rows_with_a_failure,
            {fails}
        FROM trips
        GROUP BY month, company
        ORDER BY month, company
    """).fetchall()
    columns = [d[0] for d in con.description]
    with open(OUT / "dq_by_month.csv", "w", newline="\n") as f:
        f.write("month,company,rule_id,rows_checked,failures\n")
        for row in rows:
            rec = dict(zip(columns, row))
            for r in RULES:
                f.write(f"{rec['month']},{rec['company']},{r['id']},{rec['rows_checked']},{rec[r['id']]}\n")
            f.write(f"{rec['month']},{rec['company']},ANY,{rec['rows_checked']},{rec['rows_with_a_failure']}\n")
    print(f"  wrote dq_by_month.csv ({time.time() - start:.0f}s)")

    # A few example failing rows per rule. The source holds no rider or driver identifiers,
    # and only the columns the rule is about are kept.
    rules_out = []
    for r in RULES:
        cols = ["month", "company"] + r["example_columns"]
        select = ", ".join(f"CAST({c} AS VARCHAR) AS {c}" for c in cols)
        cur = con.execute(f"SELECT {select} FROM trips WHERE {r['predicate']} LIMIT 3")
        names = [d[0] for d in cur.description]
        examples = [dict(zip(names, row)) for row in cur.fetchall()]
        rule = {k: v for k, v in r.items() if k != "example_columns"}
        rule["examples"] = examples
        rules_out.append(rule)
    with open(OUT / "dq_rules.json", "w", newline="\n") as f:
        json.dump(rules_out, f, indent=2)
        f.write("\n")
    print(f"  wrote dq_rules.json ({time.time() - start:.0f}s)")


if __name__ == "__main__":
    main()
