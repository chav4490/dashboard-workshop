---
title: Operations overview
---

```js
const monthly = FileAttachment("data/monthly.csv").csv({typed: true});
const daily = FileAttachment("data/daily.csv").csv({typed: true});
const hourly = FileAttachment("data/hourly.csv").csv({typed: true});
const dqByMonth = FileAttachment("data/dq_by_month.csv").csv({typed: true});
const rules = FileAttachment("data/dq_rules.json").json();
const source = FileAttachment("data/source.json").json();
```

```js
// Formatting helpers. Every number on the page goes through one of these.
const fmtMonth = d3.utcFormat("%B %Y");
const fmtMonthShort = d3.utcFormat("%b %Y");
const fmtDay = d3.utcFormat("%a %-d %b %Y");
const fmtInt = d3.format(",.0f");
const fmtMoney = d3.format("$,.2f");
const fmtPct1 = d3.format(".1%");
const fmtBig = (n) => n >= 1e9 ? d3.format(".2f")(n / 1e9) + " billion" : d3.format(".1f")(n / 1e6) + " million";
const fmtDuration = (s) => `${Math.floor(s / 60)}m ${String(Math.round(s % 60)).padStart(2, "0")}s`;
const fmtRate = (r) => r === 0 ? "0%" : r < 0.00001 ? "under 0.001%" : r < 0.001 ? d3.format(".3%")(r) : d3.format(".2%")(r);

const companies = ["Uber", "Lyft"];
const seriesColor = {Uber: "var(--color-series-1)", Lyft: "var(--color-series-2)", All: "var(--color-accent)"};
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
```

```js
const shown = company === "All" ? companies : [company];
const colorScale = {domain: shown, range: shown.map((c) => seriesColor[c]), legend: shown.length > 1};

const months = monthly.filter((d) => d.company === company).sort((a, b) => a.month - b.month);
const latest = months.at(-1);
const previous = months.at(-2);
const year = {
  trips: d3.sum(months, (d) => d.trips),
  fares: d3.sum(months, (d) => d.fares),
  driver_pay: d3.sum(months, (d) => d.driver_pay),
  tips: d3.sum(months, (d) => d.tips),
  shared_requests: d3.sum(months, (d) => d.shared_requests),
  wav_requests: d3.sum(months, (d) => d.wav_requests),
  wav_requests_matched: d3.sum(months, (d) => d.wav_requests_matched),
  airport_trips: d3.sum(months, (d) => d.airport_trips),
  cbd_trips: d3.sum(months, (d) => d.cbd_trips),
  out_of_city_dropoffs: d3.sum(months, (d) => d.out_of_city_dropoffs)
};

// Seven-day averages, so the weekly rhythm does not hide the trend.
function rolling(rows, key, k = 7) {
  return rows.map((d, i) => ({
    ...d,
    value: i < k - 1 ? NaN : d3.mean(rows.slice(i - k + 1, i + 1), (r) => r[key])
  })).filter((d) => !Number.isNaN(d.value));
}
const dailyBy = d3.group(daily.slice().sort((a, b) => a.date - b.date), (d) => d.company);
const tripsDaily = ["All", ...companies].flatMap((c) => rolling(dailyBy.get(c) ?? [], "trips"));
const waitDaily = companies.flatMap((c) => rolling(dailyBy.get(c) ?? [], "wait_p50_s"));

// Data quality, for the selected company.
const dqRows = dqByMonth.filter((d) => company === "All" || d.company === company);
const rowsChecked = d3.sum(dqRows.filter((d) => d.rule_id === "ANY"), (d) => d.rows_checked);
const rowsWithFailure = d3.sum(dqRows.filter((d) => d.rule_id === "ANY"), (d) => d.failures);
const failuresByRule = d3.rollup(dqRows, (v) => d3.sum(v, (d) => d.failures), (d) => d.rule_id);
const ruleStats = rules.map((r) => ({...r, failures: failuresByRule.get(r.id) ?? 0, rate: (failuresByRule.get(r.id) ?? 0) / rowsChecked}));
const checksPassed = 1 - d3.sum(ruleStats, (d) => d.failures) / (rowsChecked * rules.length);
const dimensions = d3.rollups(
  ruleStats,
  (v) => ({rules: v.length, failures: d3.sum(v, (d) => d.failures), passed: 1 - d3.sum(v, (d) => d.failures) / (rowsChecked * v.length)}),
  (d) => d.dimension
);
```

```js
// A headline tile: one number, and how it moved since the month before.
function change(now, before, {goodWhen = null, format = (d) => fmtPct1(Math.abs(d)), relative = true} = {}) {
  const diff = relative ? now / before - 1 : now - before;
  const flat = Math.abs(relative ? diff : diff / before) < 0.0005;
  const direction = flat ? "flat" : diff > 0 ? "up" : "down";
  const tone = flat || !goodWhen ? "neutral" : direction === goodWhen ? "good" : "bad";
  const arrow = {up: "▲", down: "▼", flat: "●"}[direction];
  const word = {up: "up", down: "down", flat: "no change"}[direction];
  return html`<span class="delta delta-${tone}">${arrow} ${flat ? word : `${word} ${format(diff)}`}</span> <span class="muted">vs ${fmtMonthShort(previous.month)}</span>`;
}
function tile(label, value, delta, note) {
  return html`<div class="card kpi">
    <div class="kpi-label">${label}</div>
    <div class="kpi-value tabular-nums">${value}</div>
    <div class="kpi-delta tabular-nums">${delta}</div>
    ${note ? html`<div class="kpi-note">${note}</div>` : ""}
  </div>`;
}
```

# Operations overview

<p class="lede">New York City rideshare trips, ${fmtMonth(months[0].month)} to ${fmtMonth(latest.month)}. <strong class="tabular-nums">${fmtBig(year.trips)}</strong> trips and <strong class="tabular-nums">$${fmtBig(year.fares)}</strong> in base fares over twelve months${company === "All" ? "" : `, ${company} only`}.</p>

```js
// The one filter on the page. Everything below follows it.
const company = view(Inputs.radio(["All", "Uber", "Lyft"], {label: "Company", value: "All"}));
```

## ${fmtMonth(latest.month)} at a glance

<div class="grid grid-cols-4">
  ${tile("Trips per day", fmtInt(latest.trips / latest.days), change(latest.trips / latest.days, previous.trips / previous.days, {goodWhen: "up"}), `${fmtBig(latest.trips)} trips in the month`)}
  ${tile("Median wait for pickup", fmtDuration(latest.wait_p50_s), change(latest.wait_p50_s, previous.wait_p50_s, {goodWhen: "down", relative: false, format: (d) => `${Math.abs(Math.round(d))}s`}), `One rider in ten waits over ${fmtDuration(latest.wait_p90_s)}`)}
  ${tile("Base fare per trip", fmtMoney(latest.fares / latest.trips), change(latest.fares / latest.trips, previous.fares / previous.trips), `$${fmtBig(latest.fares)} in the month, before taxes, fees and tips`)}
  ${tile("Driver pay share of fares", fmtPct1(latest.driver_pay / latest.fares), change(latest.driver_pay / latest.fares, previous.driver_pay / previous.fares, {relative: false, format: (d) => `${d3.format(".1f")(Math.abs(d) * 100)} pts`}), `${fmtMoney(latest.driver_pay / latest.trips)} to the driver per trip`)}
</div>

## Is demand growing?

<div class="card">
  <h3>Trips per day, seven-day average</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 300,
    marginLeft: 50,
    x: {type: "utc", label: null},
    y: {label: null, grid: true, tickFormat: "~s"},
    color: colorScale,
    marks: [
      Plot.areaY(tripsDaily.filter((d) => shown.includes(d.company)), {x: "date", y: "value", fill: "company", order: companies, curve: "monotone-x", fillOpacity: 0.85}),
      Plot.ruleY([0], {stroke: "var(--color-border)"}),
      Plot.ruleX(tripsDaily.filter((d) => d.company === company), Plot.pointerX({x: "date", stroke: "var(--color-text-muted)"})),
      Plot.tip(tripsDaily.filter((d) => d.company === company), Plot.pointerX({
        x: "date",
        y: "value",
        title: (d) => [fmtDay(d.date), `${fmtInt(d.value)} trips a day (7-day average)`, `${fmtInt(d.trips)} on the day itself`].join("\n")
      }))
    ]
  }))}
</div>

## Are riders picked up quickly?

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Median wait from request to pickup, in minutes</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 280,
      x: {type: "utc", label: null},
      y: {label: null, grid: true, zero: true},
      color: colorScale,
      marks: [
        Plot.ruleY([0], {stroke: "var(--color-border)"}),
        Plot.lineY(waitDaily.filter((d) => shown.includes(d.company)), {x: "date", y: (d) => d.value / 60, stroke: "company", strokeWidth: 2, curve: "monotone-x"}),
        Plot.ruleX(waitDaily.filter((d) => shown.includes(d.company)), Plot.pointerX({x: "date", stroke: "var(--color-text-muted)"})),
        Plot.tip(waitDaily.filter((d) => shown.includes(d.company)), Plot.pointerX({
          x: "date",
          y: (d) => d.value / 60,
          title: (d) => [d.company, fmtDay(d.date), `${fmtDuration(d.value)} median wait (7-day average)`].join("\n")
        }))
      ]
    }))}
    <p class="caption">Seven-day average of each day's median. Trips where the request is stamped after the pickup are left out; see the data quality section.</p>
  </div>
  <div class="card">
    <h3>When demand peaks: trips per hour through the week</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 280,
      marginLeft: 40,
      padding: 0.06,
      x: {label: "Hour of day", tickFormat: (h) => (h % 3 === 0 ? `${h}:00` : "")},
      y: {label: null, domain: weekdays},
      opacity: {domain: [0, d3.max(hourly.filter((d) => d.company === company), (d) => d.trips / d.days)], range: [0.06, 1]},
      marks: [
        Plot.cell(hourly.filter((d) => d.company === company), {
          x: "hour",
          y: (d) => weekdays[d.weekday - 1],
          fill: seriesColor[company],
          fillOpacity: (d) => d.trips / d.days,
          rx: 2,
          tip: true,
          title: (d) => [`${weekdays[d.weekday - 1]} ${d.hour}:00 to ${d.hour + 1}:00`, `${fmtInt(d.trips / d.days)} trips in a typical hour`, `${fmtDuration(d.wait_p50_s)} median wait`].join("\n")
        })
      ]
    }))}
    <p class="caption">Stronger color means more trips. Hover a cell for the count and the wait in that hour.</p>
  </div>
</div>

## What does a trip earn, and who gets it?

<div class="grid grid-cols-2">
  <div class="card">
    <h3>Average base fare per trip</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 260,
      x: {type: "utc", label: null},
      y: {label: null, grid: true, tickFormat: (d) => `$${d}`},
      color: colorScale,
      marks: [
        Plot.lineY(monthly.filter((d) => shown.includes(d.company)), {x: "month", y: (d) => d.fares / d.trips, stroke: "company", strokeWidth: 2}),
        Plot.dot(monthly.filter((d) => shown.includes(d.company)), {
          x: "month",
          y: (d) => d.fares / d.trips,
          fill: "company",
          r: 4,
          stroke: "var(--color-surface)",
          strokeWidth: 2,
          tip: true,
          title: (d) => [d.company, fmtMonth(d.month), `${fmtMoney(d.fares / d.trips)} base fare per trip`].join("\n")
        })
      ]
    }))}
  </div>
  <div class="card">
    <h3>Driver pay as a share of base fares</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 260,
      x: {type: "utc", label: null},
      y: {label: null, grid: true, tickFormat: ".0%"},
      color: colorScale,
      marks: [
        Plot.lineY(monthly.filter((d) => shown.includes(d.company)), {x: "month", y: (d) => d.driver_pay / d.fares, stroke: "company", strokeWidth: 2}),
        Plot.dot(monthly.filter((d) => shown.includes(d.company)), {
          x: "month",
          y: (d) => d.driver_pay / d.fares,
          fill: "company",
          r: 4,
          stroke: "var(--color-surface)",
          strokeWidth: 2,
          tip: true,
          title: (d) => [d.company, fmtMonth(d.month), `${fmtPct1(d.driver_pay / d.fares)} of base fares paid to drivers`].join("\n")
        })
      ]
    }))}
  </div>
</div>

<div class="card">
  <h3>The mix of trips over twelve months</h3>
  <table class="plain tabular-nums">
    <thead><tr><th>Measure</th><th class="num">Trips</th><th class="num">Share of all trips</th></tr></thead>
    <tbody>
      <tr><td>Start or end at an airport</td><td class="num">${fmtInt(year.airport_trips)}</td><td class="num">${fmtPct1(year.airport_trips / year.trips)}</td></tr>
      <tr><td>Touch the Manhattan congestion zone</td><td class="num">${fmtInt(year.cbd_trips)}</td><td class="num">${fmtPct1(year.cbd_trips / year.trips)}</td></tr>
      <tr><td>End outside the city</td><td class="num">${fmtInt(year.out_of_city_dropoffs)}</td><td class="num">${fmtPct1(year.out_of_city_dropoffs / year.trips)}</td></tr>
      <tr><td>Rider asked for a shared ride</td><td class="num">${fmtInt(year.shared_requests)}</td><td class="num">${fmtPct1(year.shared_requests / year.trips)}</td></tr>
      <tr><td>Rider asked for a wheelchair accessible vehicle</td><td class="num">${fmtInt(year.wav_requests)}</td><td class="num">${fmtPct1(year.wav_requests / year.trips)}</td></tr>
    </tbody>
  </table>
  <p class="caption">${fmtInt(year.wav_requests_matched)} of the ${fmtInt(year.wav_requests)} wheelchair accessible requests (${fmtPct1(year.wav_requests_matched / year.wav_requests)}) are marked as served by an accessible vehicle. Airport and congestion zone trips are counted by the fee charged on the trip.</p>
</div>

## Can we trust these numbers?

<p class="lede">The companies report these trips themselves, and the city does not vouch for them. ${rules.length} checks ran over every one of the <span class="tabular-nums">${fmtBig(rowsChecked)}</span> trips.</p>

<div class="grid grid-cols-4">
  ${html`<div class="card kpi"><div class="kpi-label">Checks passed</div><div class="kpi-value tabular-nums">${d3.format(".2%")(checksPassed)}</div><div class="kpi-note">Across all ${rules.length} checks and every trip</div></div>`}
  ${html`<div class="card kpi"><div class="kpi-label">Trips failing a check</div><div class="kpi-value tabular-nums">${fmtPct1(rowsWithFailure / rowsChecked)}</div><div class="kpi-note">${fmtBig(rowsWithFailure)} trips fail at least one. Most are one company not reporting one field.</div></div>`}
  ${html`<div class="card kpi"><div class="kpi-label">Checks needing an answer</div><div class="kpi-value tabular-nums">${ruleStats.filter((d) => d.finding === "open question" && d.failures > 0).length}</div><div class="kpi-note">Findings the data alone cannot explain</div></div>`}
  ${html`<div class="card kpi"><div class="kpi-label">Likely defects</div><div class="kpi-value tabular-nums">${ruleStats.filter((d) => d.finding === "defect" && d.failures > 0).length}</div><div class="kpi-note">${fmtInt(d3.sum(ruleStats.filter((d) => d.finding === "defect"), (d) => d.failures))} trips with a value that cannot be right</div></div>`}
</div>

<div class="card">
  <h3>Every check, weakest first</h3>
  <div class="table-scroll">
  <table class="plain">
    <thead><tr><th>Check</th><th>Dimension</th><th class="num">Failing trips</th><th class="num">Rate</th><th>What it is</th></tr></thead>
    <tbody>
      ${ruleStats.slice().sort((a, b) => b.failures - a.failures).map((r) => html`<tr>
        <td><strong>${r.name}</strong> <span class="muted code">${r.id}</span><br><span class="muted">${r.test}</span></td>
        <td>${r.dimension}</td>
        <td class="num tabular-nums">${fmtInt(r.failures)}</td>
        <td class="num tabular-nums">${fmtRate(r.rate)}</td>
        <td><span class="finding finding-${r.failures === 0 ? "none" : r.finding.replace(" ", "-")}">${r.failures === 0 ? "passes" : r.finding}</span></td>
      </tr>`)}
    </tbody>
  </table>
  </div>
  <p class="caption">By dimension: ${dimensions.map(([name, d]) => `${name} ${d3.format(".2%")(d.passed)} passed (${d.rules} ${d.rules === 1 ? "check" : "checks"})`).join("; ")}. Uniqueness is not checked because trips carry no identifier.</p>
</div>

```js
const ruleId = view(Inputs.select(ruleStats.slice().sort((a, b) => b.failures - a.failures), {label: "Look closer at", format: (r) => `${r.id}: ${r.name}`, value: ruleStats.find((r) => r.id === "CON-02")}));
```

```js
const ruleTrend = d3.rollups(
  dqByMonth.filter((d) => d.rule_id === ruleId.id && shown.includes(d.company)),
  (v) => ({failures: d3.sum(v, (d) => d.failures), rows: d3.sum(v, (d) => d.rows_checked)}),
  (d) => d.company,
  (d) => +d.month
).flatMap(([c, byMonth]) => byMonth.map(([m, v]) => ({company: c, month: new Date(m), failures: v.failures, rate: v.failures / v.rows})));
```

<div class="grid grid-cols-2">
  <div class="card">
    <h3>${ruleId.name}: failure rate by month</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 260,
      marginLeft: 60,
      x: {type: "utc", label: null},
      y: {label: null, grid: true, zero: true, tickFormat: (d) => fmtRate(d)},
      color: colorScale,
      marks: [
        Plot.ruleY([0], {stroke: "var(--color-border)"}),
        Plot.lineY(ruleTrend, {x: "month", y: "rate", stroke: "company", strokeWidth: 2}),
        Plot.dot(ruleTrend, {
          x: "month",
          y: "rate",
          fill: "company",
          r: 4,
          stroke: "var(--color-surface)",
          strokeWidth: 2,
          tip: true,
          title: (d) => [d.company, fmtMonth(d.month), `${fmtInt(d.failures)} failing trips`, `${fmtRate(d.rate)} of that month's trips`].join("\n")
        })
      ]
    }))}
    <p class="caption">A rate that jumps says more than a rate that is steady: something changed upstream that month.</p>
  </div>
  <div class="card">
    <h3>${ruleId.id}: what this check means</h3>
    <p><strong>The test.</strong> ${ruleId.test}</p>
    <p><strong>Why it matters.</strong> ${ruleId.why}</p>
    <p><strong>What it is: ${ruleId.failures === 0 ? "passes" : ruleId.finding}.</strong> ${ruleId.reading}</p>
    <details>
      <summary>How to verify it</summary>
      <p class="caption">A trip fails when this is true:</p>
      <pre><code>${ruleId.predicate}</code></pre>
      ${ruleId.examples.length ? html`<p class="caption">Example failing trips. The source holds no rider or driver details.</p>
      <div class="table-scroll"><table class="plain tabular-nums"><thead><tr>${Object.keys(ruleId.examples[0]).map((k) => html`<th>${k}</th>`)}</tr></thead>
      <tbody>${ruleId.examples.map((e) => html`<tr>${Object.values(e).map((v) => html`<td>${v ?? "(empty)"}</td>`)}</tr>`)}</tbody></table></div>` : html`<p class="caption">No failing trips to show.</p>`}
    </details>
  </div>
</div>

<p class="caption">Source: <a href="${source.source_page}">NYC Taxi and Limousine Commission trip record data</a>, High Volume For-Hire Vehicle trips. Last checked against the source on ${d3.utcFormat("%-d %B %Y")(new Date(source.checked_at))}, when the latest month published was ${fmtMonth(new Date(source.latest_published_month + "-01"))}. "What it is" is a first reading from the data alone and needs confirming by someone who owns the source. Medians are exact and computed over every trip.</p>
