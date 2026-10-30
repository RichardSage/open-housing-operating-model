# Changelog

All notable changes to the model are recorded here. Versions follow the rules in [GOVERNANCE.md](GOVERNANCE.md).

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
