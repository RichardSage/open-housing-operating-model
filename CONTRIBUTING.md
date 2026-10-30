# Contributing

Thank you for helping improve the Open Housing Operating Model. Contributions from anyone who works in, lives in or works with social housing are welcome: residents, frontline staff, managers, service designers, consultants, suppliers and researchers.

New to GitHub? The [step-by-step guide](HOW-TO-CONTRIBUTE.md) walks you through your first suggestion.

## Three ways to take part

| If you want to… | Do this | Git needed? |
|---|---|---|
| Point out something missing, wrong or misplaced | Fill in the [suggestion form](../../issues/new/choose) | No |
| Talk through a bigger idea (a new layer, a regional version) | Start a thread in [Discussions](../../discussions) | No |
| Make the change yourself | Edit a file in `model/` on GitHub and propose it as a pull request | A little |

Maintainers turn agreed suggestions into updates, so the form is always a good option.

## The two views

The model describes the same organisation two ways:

- **Services** (`model/services.yaml`) are the outside-in view: what people are trying to get done. Services contain **requests**.
- **The operating model** (`model/function-areas/`) is the inside-out view: how the work is done. Function areas contain **functions**, which contain **activities**.

Each request lists the functions or activities it relies on, under `uses`.

## Editing services

```yaml
- code: "S08"
  name: Repair my home
  group: my-home
  users: [tenants]
  goal: Get things fixed properly, first time
  requests:
  - code: "S08.4"
    name: Repair damp and mould
    pattern: book
    uses: ["11.5", "12.9.1"]
```

- `group`, `users` and `pattern` must be one of the values listed at the top of `services.yaml`.
- `uses` can list a function code (e.g. `"11.5"`, meaning all its activities) or individual activity codes (e.g. `"12.9.1"`).

### Naming services and requests

Services follow the GOV.UK Service Manual's approach: a service helps someone do something.

- **Name it the way the person would say it**, usually a verb and "my": "Repair my home", "End my tenancy", "Get help with my finances". Not "Responsive repairs" or "Tenancy termination".
- **A service is a goal; a request is a step towards it.** "Rent a home" is a service. "View a home and accept an offer" is a request within it.
- **Avoid organisation language.** No team names, system names or internal jargon. If a resident wouldn't search for it, rename it.
- Each request has one **pattern**:

| Pattern | Use it when someone wants to… |
|---|---|
| Apply | ask for something that needs a decision about eligibility or suitability |
| Book | arrange for something to happen at a time that suits |
| Pay | pay money, or agree how to pay it |
| Request | ask for help, permission or something to be provided |
| Tell | report something or let the organisation know about a change |
| Check | find out information or the status of something |

## Editing the operating model

Each function area has its own file in `model/function-areas/`, named `<code>-<name>.yaml`:

```yaml
code: "11"
name: Responsive Repairs
domain: homes-and-customers
description: Day-to-day repairs, damp and mould, and disrepair
functions:
- code: "11.5"
  name: Damp & mould
  activities:
  - code: "11.5.1"
    name: Triage damp and mould reports
```

### Naming functions and activities

**Activities**
- Start with a verb and describe one task: "Inspect fire doors", not "Fire doors" or "Inspect and repair fire doors and alarms".
- Describe the work, not the system or team that does it.
- Stay generic. Avoid product names, local team names and unfamiliar acronyms. Statutory terms (HHSRS, LOLER, Section 20) are fine.
- Aim for under 90 characters, with no full stop at the end.

**Functions and function areas**
- Use nouns: "Damp & mould", "Responsive Repairs".
- A function should have a recognisable outcome and usually 2–8 activities.

**Placement**
- Each activity belongs to exactly one function. If it seems to fit two, put it where the work is mostly done and mention the other in `notes`.
- Prefer improving an existing function over creating a new one.

### Optional fields

Any service, request, function area, function or activity can have `description` and `notes`. Most can have `references` (a list of links or citations). Activities and requests can have `aliases`: other names people use for the same thing.

## How to edit

**On GitHub:** open the file, click the pencil icon, make your change, then choose **Propose changes**. An automatic check runs on every pull request and tells you if anything needs fixing.

**Locally:** `pip install pyyaml`, then `python scripts/build.py --check`. Running `python scripts/build.py` without `--check` also builds the CSVs, JSON and atlas page (open `site/index.html`) and refreshes the tables in the README.

Only edit files in `model/`. Everything in `dist/` and `site/index.html` is generated.

## How codes work

Codes are permanent identifiers that other people's spreadsheets and products may rely on.

1. **Never renumber.** Leave gaps rather than closing them.
2. **New items take the next free number** in their parent: the next service after S41 is S42, and a new activity after 11.5.5 is 11.5.6.
3. **Moving an item gives it a new code.** Retire the old code in `model/retired.yaml` with a note like "Moved to 12.3.6".
4. **Removing or merging** an item also means adding it to `model/retired.yaml`. Retired codes are never reused, and the check enforces this.
5. **Renaming keeps the code**, as long as it's still the same thing.

If you remove or move an activity, also update any `uses` in `services.yaml` that pointed to it. The check will tell you if you miss one.

## What makes a good suggestion

- It reflects how many providers work, not just one organisation's structure.
- It explains *why*, ideally with evidence: regulation, guidance, research with residents, or contact-reason data.
- It keeps the level of detail consistent with what's around it.

## Code of conduct

Everyone taking part is expected to follow the [code of conduct](CODE_OF_CONDUCT.md).

## Licence of contributions

By contributing, you agree that your contribution is published under the project's licences: CC BY 4.0 for the model and documentation, MIT for code.
