# Optional layers

The Open Housing Operating Model describes **what** a housing association does: services, function areas, functions and activities. Layers add a **point of view** about that work without changing the model itself.

Each layer:
- lives in its own folder here, e.g. `layers/ai-impact/`
- has a `layer.yaml` that names it, gives it its own version, explains its basis and sources, and defines its fields and allowed values
- has a CSV with one row per activity code, holding that layer's values
- is checked automatically: every code must exist in the model and every value must be one the layer defines
- appears in the atlas as an optional lens that is **off by default**

A layer's version changes independently of the model. Changing a layer never changes the model's version.

## Current layers

| Layer | What it adds | Version |
|---|---|---|
| [`ai-impact`](ai-impact/) | Where AI could change each activity (Rannoch's five impact categories), a governance tier, and a suggested route, based on the NHF AI code of practice and the Regulator's statements | 2026.11 |
| [`regulation`](regulation/) | A register of 48 laws, regulatory standards and codes for registered providers in England, linked to the functions and activities they require or shape. Two lenses: the legal basis for each activity, and what's changing and when | 2026.11 |

## Ideas for new layers

- Typical roles or teams that carry out each activity
- The systems or data each activity depends on
- Performance measures, such as Tenant Satisfaction Measures, linked to activities

## Two kinds of layer

- **Value layers** (like `ai-impact`) give each activity one value per field, in a CSV keyed by activity code.
- **Register layers** (like `regulation`, with `kind: register`) hold a list of things, such as obligations, in `register.yaml`, and link them to functions or activities in `links.csv`. A link to a function applies to all its activities. The build works out the lenses from those links, so nobody edits the lens values by hand.

## Improving the regulation layer

- **Add or correct an obligation** in `regulation/register.yaml`. Include a source link and update `last_checked`.
- **Add a dated change** under an obligation's `changes`, marked `confirmed` or `expected`. The atlas's "Coming up" list and "What's changing" lens update themselves.
- **Add or refine links** in `regulation/links.csv`. Use `requires` when the activity exists because of the obligation, and `shapes` when the obligation sets how it's done. Prefer activity-level links where only part of a function is affected.
- It's **not legal advice**. If you're a housing lawyer or compliance specialist, a review of any section is especially welcome.

## Making a layer

1. Copy `ai-impact/layer.yaml` into a new folder and change the `id`, `name`, `version`, `summary`, `caveat`, `sources` and `fields`.
2. Create the data CSV with a `code` column, an optional `activity` column for readability, and one column per field.
3. Run `python scripts/build.py --check`. It lists any unknown codes or values, and any activities the layer doesn't cover yet.
4. Propose it as a pull request, or describe it in [Discussions](../../../discussions) first.

Layers are opinions. Say clearly in `summary` and `caveat` what yours is based on, and how sure it is.
