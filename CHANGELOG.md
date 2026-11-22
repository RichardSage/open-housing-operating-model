# Changelog

All notable changes to the model are recorded here. Versions follow the rules in [GOVERNANCE.md](GOVERNANCE.md).

## Unreleased

**Layers**
- New layer `tsm` v2026.11: the 22 Tenant Satisfaction Measures, linked to the work that drives or influences each one. Three lenses (TSM theme, link strength and how it's measured), and a list of the measures in the atlas's layer panel. Adds a third layer kind, `measures`.

**TSM data**
- A new **TSM data** GitHub Action finds every edition of the Regulator of Social Housing's Tenant Satisfaction Measures on GOV.UK, converts each year's full dataset to CSV in `data/tsm/` (results by landlord, tenure and measure, plus landlord details and how each survey was run), and opens a pull request when the data change. Tested against the 2025/26 full dataset: 9,918 results for 356 landlords, all 22 measures. `scripts/fetch_tsm.py --file` converts a dataset you've downloaded yourself. It runs on Mondays in November and December, and monthly to catch revisions. See `data/tsm/README.md`.

**Navigation**
- The main navigation is now Atlas, Tools, Data and Contribute. A new Tools page lists every tool and overlay with who it's for, and the tool pages share a second row of tabs. A new Data page brings together every download, the layers, versions and how to cite the model.

**Branding**
- A logo: an open outline of a house with tiles inside. The gap is the open part. It's in the navigation bar on every page and at the top of the README, with files and usage rules in `site/brand/`.
- Browser tab and home screen icons, and a preview image with title and description tags, so links to any page show a proper card when shared.

**Tools**
- **Assess:** product coverage now handles several products. Add, rename and remove products, and rate one at a time. The results combine them (the best support any product gives), with a new Figure A3 comparing every product function by function and filters for gaps and overlaps. You can also view the results for one product. Downloads gain a `product` column, and older single-product saves and CSVs still load.
- **Assess:** add a product by typing its name and selecting Add product, rather than getting a numbered placeholder. Each product has its own colour. While you rate, a bar stays at the top of the screen showing which product you're rating, with a quick way to switch, and the function list is edged in that product's colour.

## 0.3.0 - 2026-11-21

**Tools (new)**
- The atlas is now one of four pages, with shared navigation and a "Use the model" section. Each tool page says who it's for and how to use it.
- **Patterns & components:** the six interaction patterns, 15 shared components ranked by how many requests use them, and a grid of which services use which components.
- **Pressure map:** function areas plotted by regulatory change against AI opportunity, with the detail for any area or function, and a sortable table.
- **Assess:** rate your organisation's capability, or a product's coverage, by function or activity. See a heat map and how well the work behind each service is supported. Saved in the browser only, with CSV download and upload and a printable view.
- New `model/components.yaml` and `open-housing-components.csv`.

**Services**
- 16 new requests and one new service, following a review of Anchor Housing's customer journey catalogue, with thanks:
  - S01 Rent a home: check my housing application, update my housing application, ask for a review of a housing decision
  - S08 Repair my home: check or change my repair appointment, check if a repair is my responsibility
  - S09 Keep my home safe: move out while my home is made safe, get help when an emergency affects my building
  - S15 Get help with my finances: get help if I'm facing eviction
  - S18 Keep my details up to date: let someone act on my behalf, get help if I can't go online
  - S20 Manage my lease: challenge my service charge, take over management of my building
  - S25 Get support to live independently: book a guest room, arrange meals or housekeeping
  - S30 Get information from my landlord: get a landlord reference or proof of rent, correct or delete my personal data
  - New service S42 Report tenancy fraud

**Specialist provision (new)**
- New `model/specialist.yaml` lists kinds of provision that only some providers offer: retirement and extra care, supported housing, shared ownership and sales, and commercial property
- Services, requests and functions can be tagged with `specialist`. The CSVs gain a `specialist` column.
- Atlas: a new **Specialist provision** bar. Untick a kind of provision and it drops out of every figure. Links can open with provision switched off (for example `?without=older-people`).

**Layers**

- New optional layers: a point of view on top of the model, kept in `layers/` with its own version, sources and caveats. Layers are validated against the model and published separately (`layers/<id>.csv` and `.json`).
- Layer `regulation` v2026.11: a register of 48 laws, regulatory standards and codes for registered providers in England, with 267 links to functions and activities. Two lenses (legal basis, and what's changing) plus a "Coming up" timeline of dated changes. Not legal advice.
- Regulation watcher: a weekly GitHub Action checks the register against GOV.UK and legislation.gov.uk and opens `regulation-watch` issues for review. It never edits the register. See `layers/regulation/WATCH.md`.
- Layer `ai-impact` v2026.11. AI impact, a governance tier and a suggested route for all 667 activities, drawing on the NHF AI code of practice and the Regulator's statements.
- Atlas: a new **Layer** bar, off by default. Choosing a layer colours activities in every figure, and links can open with a layer applied (for example `?layer=ai-impact:route`).

## 0.2.0 - 2026-10-30

Adds an outside-in view of services, following feedback from a service designer.

**Services (new)**
- New `model/services.yaml`: 41 services and 100 requests, named the way residents and colleagues would say them, in 10 groups
- Every request is tagged with an interaction pattern (Apply, Book, Pay, Request, Tell, Check) and linked to the functions or activities it relies on
- Service names and patterns adapted from the Design Patterns for Social Housing service list (Dave Skinner), with pattern groups from TPXImpact's local government work
- 11 colleague services, alongside 30 for residents, communities and businesses

**Operating model**
- Renamed levels: "service area" is now **function area** and "service" is now **function**. Codes are unchanged.
- Files moved from `model/areas/` to `model/function-areas/`, and the `services:` key is now `functions:`
- Added 10.8 Right to Buy and Right to Acquire, 10.9 Market sales & Rent to Buy, and 13.10 Commercial property
- Added 01.8.4 Record and share compliments and feedback, 08.1.9 Promote home contents insurance, and 22.2.4 Handle residents' claims for damage to their belongings
- Added 14.9 Tenant access to information (STAIRs) (contributed 21 October)
- Renamed 22.3.1 to "Respond to subject access requests"

**Atlas and data**
- New figures: the services people use, and what sits behind each service
- The operating model figure can now show which activities support a service and which are backstage
- New `open-housing-services.csv`; the activities CSV gains a `supports_services` column
- Counts on the atlas and in the README now update automatically
- New "Help improve it" section, with "Suggest a change" links on each service and function area

## 0.1.0 - 2026-10-21

First public draft.

- 2 domains, 22 service areas, 173 services and 643 activities for a generic housing association in England
- Interactive atlas, CSV and JSON outputs
- Contribution guide, suggestion form and automatic validation
