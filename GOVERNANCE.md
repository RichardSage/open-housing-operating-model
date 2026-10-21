# Governance

This is a small, open project. These rules keep it trustworthy as more people contribute.

## Roles

- **Maintainers** review suggestions, merge changes and publish releases. The project starts with its founder as sole maintainer. Regular, constructive contributors may be invited to become maintainers.
- **Contributors** are anyone who suggests, discusses or edits.

## How decisions are made

| Change | How it's decided |
|---|---|
| Typos, wording, descriptions, references | Any maintainer can merge |
| New, renamed or moved activities | Merged after at least one review, open for comment for 7 days |
| New, merged or removed services | Open for comment for at least 14 days, with a short rationale |
| Changes to service areas or domains | Proposed in Discussions first, open for at least 30 days, then decided by the maintainers |

Maintainers aim for consensus. When views differ, the deciding question is: *does this reflect how most housing providers actually work, and does it make the model more useful to the sector?* Decisions are explained in the issue or pull request.

## Versions and releases

The model uses [semantic versioning](https://semver.org/):

- **Patch** (0.1.**1**): wording, descriptions and references only
- **Minor** (0.**2**.0): activities or services added, moved or retired
- **Major** (**1**.0.0): changes to service areas or domains, or to the file format

Each release updates `version` in `model/meta.yaml`, adds an entry to `CHANGELOG.md`, and is published as a GitHub release with the CSV and JSON attached. Version 1.0.0 should mark the point where the model has had broad review from people across the sector.

## Independence

The model is vendor-neutral. Suggestions that promote a specific product, supplier or consultancy method won't be accepted. Optional layers that map products or methods to the model can live in separate repositories that reference its codes.
