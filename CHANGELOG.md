# Changelog

All notable changes to the model are recorded here. Versions follow the rules in [GOVERNANCE.md](GOVERNANCE.md).

## Unreleased

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
