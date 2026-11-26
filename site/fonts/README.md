# Fonts

The site hosts its own fonts, so pages don't wait on another server and visitors' details aren't sent to a font provider.

- **Literata** (headings): the variable weight version, Latin characters only
- **IBM Plex Sans** (body text): weights 400, 500 and 600, Latin characters only
- **IBM Plex Mono** (numbers and codes): weight 500, Latin characters only

The files come from [Fontsource](https://fontsource.org) (`@fontsource-variable/literata`, `@fontsource/ibm-plex-sans` and `@fontsource/ibm-plex-mono`, version 5.3.0). Both families are under the SIL Open Font License 1.1: see `OFL.txt`. The `@font-face` rules are in `site/partials/base.css`.
