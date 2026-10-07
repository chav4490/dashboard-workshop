"""Read the raw trip files in data/raw/ and write the small summary files in data/summaries/.

Run from the repo root:

    uv run pipeline/build_summaries.py

Every query runs over every row. Only counts, rates, medians and a few example rows are
written out, so the summaries can be committed while the raw files stay on this laptop.
Medians and percentiles are DuckDB approximations (approx_quantile), which is accurate to
well under one percent at this volume and far faster than an exact sort.
"""

import json
import time
from pathlib import Path

import duckdb

from rules import RULES

ROOT = Path(__file__).resolve().parent.parent
RAW = (ROOT / "data" / "raw").as_posix() + "/**/*.parquet"
OUT = ROOT / "data" / "summaries"

# A wait is only measured when the request is not after the pickup and the gap is under
# two hours. Anything else is a data quality finding, not a wait.
VALID_WAIT = "wait_s BETWEEN 0 AND 7200"

METRICS = f"""
    count(*) AS trips,
    approx_quantile(wait_s, 0.5) FILTER (WHERE {VALID_WAIT}) AS wait_p50_s,
    approx_quantile(wait_s, 0.9) FILTER (WHERE {VALID_WAIT}) AS wait_p90_s,
    count(*) FILTER (WHERE wait_s > 600 AND {VALID_WAIT}) AS waits_over_10min,
    count(*) FILTER (WHERE {VALID_WAIT}) AS waits_measured,
    sum(base_passenger_fare) AS fares,
    sum(driver_pay) AS driver_pay,
    sum(tips) AS tips
"""


def main():
    start = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

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
        FROM read_parquet('{RAW}', union_by_name = true, filename = true)
    """)

    def write_csv(name, sql):
        con.execute(f"COPY ({sql}) TO '{(OUT / name).as_posix()}' (HEADER, DELIMITER ',')")
        print(f"  wrote {name} ({time.time() - start:.0f}s)")

    # One row per month and company, plus an 'All' row per month.
    write_csv("monthly.csv", f"""
        SELECT
            month,
            coalesce(company, 'All') AS company,
            count(DISTINCT CAST(pickup_datetime AS DATE)) AS days,
            {METRICS},
            approx_quantile(trip_miles, 0.5) AS miles_p50,
            approx_quantile(trip_time, 0.5) AS trip_time_p50_s,
            count(*) FILTER (WHERE shared_request_flag = 'Y') AS shared_requests,
            count(*) FILTER (WHERE wav_request_flag = 'Y') AS wav_requests,
            count(*) FILTER (WHERE wav_request_flag = 'Y' AND wav_match_flag = 'Y') AS wav_requests_matched,
            count(*) FILTER (WHERE airport_fee > 0) AS airport_trips,
            count(*) FILTER (WHERE cbd_congestion_fee > 0) AS cbd_trips,
            count(*) FILTER (WHERE DOLocationID = 265) AS out_of_city_dropoffs
        FROM trips
        GROUP BY GROUPING SETS ((month, company), (month))
        ORDER BY month, company
    """)

    write_csv("daily.csv", f"""
        SELECT
            CAST(pickup_datetime AS DATE) AS date,
            coalesce(company, 'All') AS company,
            {METRICS}
        FROM trips
        GROUP BY GROUPING SETS ((CAST(pickup_datetime AS DATE), company), (CAST(pickup_datetime AS DATE)))
        ORDER BY date, company
    """)

    # Hour of the week: weekday 1 is Monday, 7 is Sunday.
    write_csv("hourly.csv", f"""
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
