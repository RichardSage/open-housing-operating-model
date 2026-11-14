# The regulation watcher

Laws and regulatory standards change. The regulation layer is only useful if it keeps up, so a GitHub Action checks it once a week and tells maintainers when something may need updating.

**It never changes the register itself.** It opens issues labelled [`regulation-watch`](../../../../issues?q=label%3Aregulation-watch) for a person to check. Every change to the register still goes through a pull request and a review.

## What it checks

| Check | How | What you get |
|---|---|---|
| **A source has been updated** | For each obligation, the GOV.UK pages in `watch:` (or its `url`) via the GOV.UK Content API. If the page has a major update after the entry's `last_checked` date, that counts. | One issue per update, with GOV.UK's change note |
| **An Act or regulations have been amended** | For each legislation.gov.uk link, the changes (effects) that legislation.gov.uk has recorded against it since `last_checked` | One issue listing the amending legislation |
| **A dated change has passed** | Any entry under `changes` whose date is now in the past | One issue asking whether it happened as planned |
| **An entry is getting old** | Any entry whose `last_checked` is more than 180 days ago | One checklist issue covering all of them |
| **New publications** | New items in the last 9 days from the Regulator of Social Housing, MHCLG and the Building Safety Regulator on GOV.UK, and new Acts and statutory instruments with housing words in the title | One digest issue per week, as a checklist |
| **A source can't be reached** | Any link that fails | One issue listing them |

It won't raise the same thing twice, even after an issue is closed.

Entries without a GOV.UK or legislation.gov.uk link, such as the Housing Ombudsman's Complaint Handling Code, are only covered by the "getting old" check. The run summary lists them.

## Dealing with an issue

1. Read the source and decide whether the register needs to change. Most of the time it won't.
2. If it does, edit `register.yaml` (and `links.csv` if different activities are affected) in a pull request that mentions the issue, for example "Closes #42".
3. Either way, set `last_checked` to today for the entries you looked at. That's how the watcher knows they've been seen.

## Changing what it watches

- **Watch a more specific page for an obligation:** add a `watch:` list to the entry in `register.yaml`. Organisation home pages are ignored because they change for unrelated reasons.
- **Change the publication filters:** edit `watch.yaml`. It holds the organisations to follow, keywords to keep or skip, and the words to look for in new legislation titles.

## Running it

- It runs every Monday morning. You can also run it from the **Actions** tab: choose **Regulation watch**, then **Run workflow**. Tick "dry run" to see the report in the run summary without opening issues.
- To run it locally: `python scripts/check_regulation.py --dry-run`
- It's free for public repositories. GitHub pauses scheduled workflows in repositories with no activity for 60 days. If that happens, re-enable it from the Actions tab.

## Data sources

[GOV.UK Content API](https://content-api.publishing.service.gov.uk/) and Search API, and the [legislation.gov.uk API](https://legislation.github.io/data-documentation/), used under the Open Government Licence. The watcher identifies itself and pauses between requests, in line with legislation.gov.uk's fair use policy.

It's a prompt to check, not a source of truth, and none of this is legal advice.
