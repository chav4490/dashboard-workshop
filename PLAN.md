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
- **What they are trying to do:** _in their words, not the system's_
- **How often they look:** _daily, weekly, before a meeting_
- **What they do today instead:** _the spreadsheet, the email, the report someone rebuilds by hand_

## The questions it answers

Three to five questions. If a chart does not answer one of these, it does not belong.

| # | Question the person asks | How they will know the answer at a glance |
|---|---|---|
| 1 | _e.g. Are trips up or down this month?_ | _one number with the change from last month_ |
| 2 | | |
| 3 | | |

## Data quality checks

Pick the dimensions that matter from the framework you use. If you have none, tell Claude to
use the data quality dimensions in the DAMA-DMBOK. The `/analyze-data-quality` skill walks
through this step.

| Dimension | The rule, in plain words | Where it shows on the dashboard |
|---|---|---|
| _e.g. Completeness_ | _every trip has a pickup zone_ | _a score tile plus the failing rows in a table_ |
| | | |

## What is on screen

Fill this in based on the user's prompts.

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
