# Dashboard plan

This is the plan for your dashboard. Fill it in with Claude **before** any code is written,
one section at a time, in plain words. Keep every answer short: a line or two is plenty.
When something changes, change it here first, then build.

Why bother: a dashboard built without a plan is the "vibecoded" kind. It looks finished, nobody
can say whether it is right, and nobody knows what to fix when it breaks. Ten minutes here saves
an afternoon later.

The order follows the engineering process: requirements, a plan with success criteria, build,
test and verify, then maintain.

---

## Who it is for

Name one real person, not "users". Then work backwards from what they are trying to do.
The `jobs-quote-ux` skill is the standard for this section.

- **The person:** a chief operating officer (COO), or someone in a similar role, who needs the state of operations at a glance rather than row-level detail
- **What they are trying to do:** "Tell me in one screen whether the business is growing, whether riders are being served well, what a trip earns, and whether I can believe the numbers."
- **How often they look:** monthly, before an operations review, when the new month's file lands
- **What they do today instead:** _not confirmed yet. Assumed: a monthly report someone rebuilds by hand._

## The questions it answers

Three to five questions. If a chart does not answer one of these, it does not belong.

| # | Question the person asks | How they will know the answer at a glance |
|---|---|---|
| 1 | Is demand growing? | Trips per day for the latest month with the change from the month before, and a daily trend over twelve months |
| 2 | Are riders picked up quickly? | Median wait from request to pickup with the change from the month before, a daily trend, and the hours of the week when demand peaks |
| 3 | What does a trip earn, and who gets it? | Base fare per trip and the share paid to drivers, by month |
| 4 | How do the two companies compare? | One Company filter (All, Uber, Lyft); every chart shows both side by side when All is chosen |
| 5 | Can we trust these numbers? | Share of checks passed, then every check with its failing count, rate and what the finding is |

## Data quality checks

Pick the dimensions that matter from the framework you use. If you have none, tell Claude to
use the data quality dimensions in the DAMA-DMBOK. The `/analyze-data-quality` skill walks
through this step.

| Dimension | The rule, in plain words | Where it shows on the dashboard |
|---|---|---|
| Completeness | every trip names its originating base, starts in a real city zone and ends in a known zone (CMP-01 to CMP-03) | the checks table and the rule detail panel |
| Validity | fares and driver pay are not negative and distance is above zero (VAL-01 to VAL-03) | the checks table and the rule detail panel |
| Consistency | request, driver arrival, pickup and dropoff are in order, and trip time matches the timestamps (CON-01 to CON-04) | the checks table, the rule detail panel and the monthly failure trend |
| Reasonableness | speed is 80 miles an hour or less and the wait is under an hour (REA-01, REA-02) | the checks table and the rule detail panel |
| Timeliness | every trip is in the right month's file (TIM-01) | the checks table |

Framework: the DAMA-DMBOK dimensions, used as the default because no other was named. Uniqueness
is left out because trips carry no identifier. The rules live in `pipeline/rules.py`.

## What is on screen

One page, top to bottom, with one Company filter (All, Uber, Lyft) that drives everything.

1. A one-line summary: the period, total trips and total base fares.
2. Four headline tiles for the latest month, each with the change from the month before: trips
   per day, median wait, base fare per trip, driver pay share of fares.
3. Demand: trips per day as a seven-day average over the twelve months.
4. Service: median wait as a seven-day average, and a weekday by hour grid of trips.
5. Economics: base fare per trip and driver pay share, by month, plus a table of the trip mix
   (airport, congestion zone, out of city, shared, wheelchair accessible).
6. Data quality: four tiles, every check in one table, and a closer look at one check with its
   monthly failure rate, plain-words meaning, the SQL that defines it and example rows.

Data: the latest twelve monthly High Volume For-Hire Vehicle files published by the NYC Taxi
and Limousine Commission, about 252 million trips. `pipeline/fetch_raw.py` reads the public
source page (no key needed) and downloads any of those months not already in `data/raw/`.
`pipeline/build_summaries.py` then writes the small files in `data/summaries/` that the page
reads. `npm run refresh` runs both. The page footer says when the source was last checked.

## Success criteria

How we will know it is done and right. Each one is something we can check, not a feeling.

- [ ] Every question in "The questions it answers" is answered on screen
- [ ] The headline numbers match the source (spot-check two of them by hand)
- [ ] Every check in "Data quality checks" runs and shows its result
- [ ] Looked at on the live dev site, at the size the person will use it, and it is both correct and pleasing
- [ ] A pass against the ten usability heuristics, with nothing serious left open
- [ ] The security review under "Test and verify" passes
- [ ] _add your own_

## Test and verify

- **Look at it.** Open the live dev site and look at every view, the way the person will. Reading
  the code is not checking. The `closed-loop-visual-feedback` skill covers how.
- **Check the numbers.** Compare the headline numbers against the source.
- **Usability.** Run the `ux-heuristics` skill (Nielsen's ten heuristics) and fix anything serious.
- **Security review.** Ask Claude to review the project as an attacker would, then fix what it finds:
  - [ ] No key or password anywhere in the code or the git history
  - [ ] The browser never receives a key; anything that needs one runs on the server side
  - [ ] Nothing personal or sensitive is sent to the page
  - [ ] Dependencies checked for known problems (`npm audit`)
  - [ ] Who can open the dashboard is a decision you made, not an accident

## Items that will require maintenance

Fill this in as you build: anything that will need attention later, such as a key that
expires or a data source that changes. Include a plan for dependencies that will need to be updated.
