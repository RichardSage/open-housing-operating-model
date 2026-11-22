# Tenant Satisfaction Measures data

Converted copies of the Regulator of Social Housing's published Tenant Satisfaction Measures (TSMs). They're made by `scripts/fetch_tsm.py`, which the **TSM data** GitHub Action runs. The Action opens a pull request whenever the data changes, so a person checks it before it's merged.

To convert a full dataset you've downloaded yourself: `python scripts/fetch_tsm.py --file 2026_TSM_Full_Dataset.xlsx`

## Files, per reporting year (such as `2025-26`)

**`<year>.csv`**: the results. One row per landlord, tenure and measure.
- `tenure`: LCRA (tenants), LCHO (shared owners), Combined (the few landlords allowed to report both together), or All (management information that covers all homes)
- `measure` and `part`: CH01, CH02, RP02 and NM01 have two parts each. For CH01 and CH02 they're stage one and stage two complaints; for RP02, non-emergency and emergency repairs; for NM01, all ASB cases and cases involving hate incidents. `part_name` says which
- `unit`: `%` (0 to 100, as published) or `per 1,000 homes` (CH01 and NM01)
- `value` and `status`: if the value is missing, `status` says why, using the Regulator's markers. `[E]` means the Regulator excluded the data (see `rsh_notes` in the landlords file); `[X]` means the landlord left it blank; `[S]` means it was suppressed. Results that don't apply (`[U]`, for example complaints from shared owners at a landlord with none) are left out

**`<year>-landlords.csv`**: one row per landlord. Type (PRP or LARP), size band, predominant region, whether more than 30% of its rented homes are supported housing, the link to its own TSM publication, its repair target timescales, and any notes from the Regulator.

**`<year>-surveys.csv`**: how each landlord ran its tenant survey, per tenure. Population, required and achieved sample, margin of error, sample or census, responses by method, and whether a contractor was used.

**`sources.json`**: where each file came from, when it was published, and a checksum. **`STRUCTURE.md`**: which source column each result came from, with sample rows, to check the conversion. **`SUMMARY.md`**: counts for each year.

The script keeps only each measure's headline result. Respondent counts, results by survey method, and numerators and denominators stay in the Regulator's file.

## Things to know

- The Regulator publishes data for landlords with 1,000 or more homes. Smaller landlords aren't included.
- Shared owners aren't asked TP02, TP03 or TP04, because they're responsible for most of their own repairs.
- Perception results depend partly on how each landlord ran its survey (see the surveys file), so compare with care.
- Landlords report these figures themselves. The Regulator notes that non-decent homes (RP01) in particular depend on how complete each landlord's stock condition surveys are.
- 2025/26 is the first year the Regulator has published TSMs as official statistics.

Source: Regulator of Social Housing, [Tenant Satisfaction Measures](https://www.gov.uk/government/statistics/tenant-satisfaction-measures-202526), under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
