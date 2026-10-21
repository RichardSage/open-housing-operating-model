# Contributing

Thank you for helping improve the Open Housing Operating Model. Contributions from anyone who works in or with social housing are welcome: frontline staff, managers, residents, consultants, suppliers and researchers.

## Three ways to take part

| If you want to… | Do this | Git needed? |
|---|---|---|
| Point out something missing, wrong or misplaced | Fill in the [suggestion form](../../issues/new/choose) | No |
| Talk through a bigger idea (a new layer, a regional version) | Start a thread in [Discussions](../../discussions) | No |
| Make the change yourself | Edit a file in `model/areas/` on GitHub and propose it as a pull request | A little |

Maintainers turn agreed suggestions into updates, so the form is always a good option.

## Editing the model

Each service area has its own file in `model/areas/`, named `<code>-<name>.yaml`:

```yaml
code: "11"
name: Responsive Repairs
domain: homes-and-customers
description: Day-to-day repairs, damp and mould, and disrepair
services:
- code: "11.5"
  name: Damp & mould
  activities:
  - code: "11.5.1"
    name: Triage damp and mould reports
```

To edit on GitHub: open the file, click the pencil icon, make your change, then choose **Propose changes**. An automatic check runs on every pull request and tells you if anything needs fixing.

To check locally: `pip install pyyaml`, then `python scripts/build.py --check`. Running `python scripts/build.py` without `--check` also builds the CSV, JSON and atlas page so you can preview them (open `site/index.html`).

Only edit files in `model/`. Everything in `dist/` and `site/index.html` is generated.

### Optional fields

These can be added to any area, service or activity: `description`, `notes`, and `references` (a list of links or citations). Activities can also have `aliases`, a list of other names people use for the same task.

```yaml
  - code: "11.5.4"
    name: Monitor against Awaab's Law timescales
    description: Track each damp and mould case against the statutory investigation and repair deadlines.
    references:
    - https://www.legislation.gov.uk/
    aliases:
    - Awaab's Law case tracking
```

## How codes work

Codes are permanent identifiers that other people's spreadsheets and products may rely on.

1. **Never renumber.** Leave gaps rather than closing them.
2. **New items take the next free number** in their parent. A new activity after `11.5.5` is `11.5.6`, even if `11.5.3` was retired.
3. **Moving an item gives it a new code.** Retire the old code in `model/retired.yaml` with a note like "Moved to 12.3.6".
4. **Removing or merging** an item also means adding it to `model/retired.yaml`. Retired codes are never reused, and the check enforces this.
5. **Renaming keeps the code**, as long as it's still the same piece of work.

## Naming rules

**Activities**
- Start with a verb and describe one task: "Inspect fire doors", not "Fire doors" or "Inspect and repair fire doors and alarms".
- Describe the work, not the system or team that does it: "Book repair appointments", not "Use the scheduling system".
- Stay generic. Avoid product names, local team names and acronyms people outside your organisation won't know. Statutory terms (HHSRS, LOLER, Section 20) are fine.
- Aim for under 90 characters, with no full stop at the end.

**Services and service areas**
- Use nouns: "Damp & mould", "Responsive Repairs".
- A service should have a recognisable outcome and usually 2–8 activities. If it grows beyond about 10, consider splitting it.

**Placement**
- Each activity belongs to exactly one service. If it seems to fit two, put it where the work is mostly done and mention the other in `notes`.
- Prefer improving an existing service over creating a new one.

## What makes a good suggestion

- It reflects how many providers work, not just one organisation's structure.
- It explains *why*, ideally with a link to regulation, guidance or common practice.
- It keeps the level of detail consistent with what's around it.

## Code of conduct

Everyone taking part is expected to follow the [code of conduct](CODE_OF_CONDUCT.md).

## Licence of contributions

By contributing, you agree that your contribution is published under the project's licences: CC BY 4.0 for the model and documentation, MIT for code.
