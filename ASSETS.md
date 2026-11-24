# Assets — origin and terms

What the application ships besides its code: images, fonts and data tables. Unless a line says otherwise, a file is
part of the project and is covered by its licence, the [GNU AGPL-3.0-or-later](LICENSE). No image depicts a real person.

## The brand — `app/static/assets/marque/`

`apple-touch-icon.png`, `favicon.ico`, `favicon.svg`, `icone-192.png`, `icone-512.png`, `insigne-mission-plan.svg`,
`insigne-mission-tools.svg`, `insigne-ready-room.svg`, `pictogramme-16.svg`, `pictogramme.svg`

The Squadron Ready Room family: insignia, pictograms and icons. Original artwork of the project; lettering from Oswald
(SIL Open Font License 1.1), converted to outlines.

## Images — `app/static/assets/img/`

| files | what | origin |
|---|---|---|
| `landing-bg.jpg`, `landing-bg-light.jpg`, `landing-bg-portrait.jpg`, `landing-bg-light-portrait.jpg` | backgrounds of the home and sign-in screens | generated for the project with Google Gemini, retouched by the project |
| `tile-planning.jpg`, `tile-planning-light.jpg`, `tile-debrief.jpg`, `tile-debrief-light.jpg`, `tile-command.webp`, `tile-command-light.webp`, `tile-manuel.webp`, `tile-mission-plan.webp`, `tile-mission-tools.webp` | the tiles of the home screen | generated for the project with Google Gemini, retouched by the project |
| `rr_photo_1.webp`, `rr_photo_2.webp`, `rr_photo_3.webp`, `rr_photo_4.webp`, `rr_photo_5.webp`, `rr_photo_6.webp`, `rr_pilote_h1.webp`, `rr_pilote_h2.webp`, `rr_pilote_h3.webp`, `rr_pilote_h4.webp`, `rr_pilote_h5.webp`, `rr_pilote_h6.webp`, `rr_pilote_j1.webp`, `rr_pilote_j2.webp`, `rr_pilote_j3.webp`, `rr_pilote_j4.webp`, `rr_pilote_j5.webp`, `rr_pilote_j6.webp` | ambience photos and pilot portraits of the files | generated for the project with Google Gemini, retouched by the project; no real person |
| `rr_ac_f1.png`, `rr_ac_f16.png`, `rr_ac_f4e.png`, `rr_ac_f5.png`, `rr_ac_mi24.png`, `rr_ac_mi8.png`, `rr_ac_uh1.png`, `rr_ac_f1_filaire.png`, `rr_ac_f16_filaire.png`, `rr_ac_f4e_filaire.png`, `rr_ac_f5_filaire.png`, `rr_ac_mi24_filaire.png`, `rr_ac_mi8_filaire.png`, `rr_ac_uh1_filaire.png` | wireframe aircraft of the squadrons and their masks | generated for the project with Google Gemini, masks drawn by the project |
| `rr_paper_dark.webp`, `rr_paper_light.webp`, `rr_grain.webp`, `grain.png`, `rr_scotch_1.webp`, `rr_scotch_2.webp`, `rr_scotch_3.webp`, `rr_scotch_4.webp`, `rr_trombone_1.webp`, `rr_trombone_2.webp`, `rr_stamp_copie.webp`, `rr_stamp_secret.webp` | paper, grain, tape, paper clips and stamps of the “file” look | made for the project with AI image tools (Google Gemini, Claude Design), retouched by the project |
| `rr_target-aa.png`, `rr_target-artillerie.png`, `rr_target-avion.png`, `rr_target-blinde-leger.png`, `rr_target-char.png`, `rr_target-helicoptere.png`, `rr_target-inconnu.png`, `rr_target-infanterie.png`, `rr_target-navire.png`, `rr_target-static.png`, `rr_target-vehicule.png` | target categories of the debriefings | made for the project with AI image tools (Google Gemini, Claude Design), retouched by the project |
| `emblem-default.png` | the default emblem of a wing that has not set its own | original artwork of the project (the Squadron Ready Room insignia) |
| `rr_otan_emblem.webp`, `rr_otan_emblem_light.webp` | the NATO emblem, in the Cold War look of the files | **not covered by the AGPL licence**: the NATO emblem belongs to NATO, whose use of it is reserved; it is shipped as a period element of the design, and a fork can remove it |

## Theatre thumbnails — `app/static/assets/img/cartes/`

`AFG.webp`, `CAU.webp`, `CHN.webp`, `GCW.webp`, `IRQ.webp`, `KOL.webp`, `M44.webp`, `MAR.webp`, `NEV.webp`, `NOR.webp`,
`PGF.webp`, `SAT.webp`, `SIN.webp`, `SYR.webp`

Drawn for the project from the coastlines, borders and rivers of GSHHG (Global Self-consistent, Hierarchical,
High-resolution Geography Database, P. Wessel and W. H. F. Smith), distributed under the LGPL by the
`basemap-data-hires` package; the extents of the theatres are approximate. No artwork from the game. The detail is in
`cartes/SOURCES.txt`.

## Pilot's Manual figures — `manuel/contenu/figures/`

`fig_0-1.svg`, `fig_1-1.svg`, `fig_1-2.svg`, `fig_1-3.svg`, `fig_1-4.svg`, `fig_2-1.svg`, `fig_2-2.svg`, `fig_2-3.svg`, `fig_2-4.svg`, `fig_2-5.svg`, `fig_2-6.svg`, `fig_2-7.svg`, `fig_3-1.svg`, `fig_3-2.svg`, `fig_3-3.svg`, `fig_3-4.svg`, `fig_A-1.svg`

Drawings of the application's screens made by the project, on fictional data (the squadrons of the
“Example Air Wing”).

## Fonts — `app/static/assets/fonts/`

Oswald, Zilla Slab and JetBrains Mono under the SIL Open Font License 1.1; Special Elite under the Apache License 2.0.
Each font with its copyright and its licence text: [`fonts/LICENSES.md`](app/static/assets/fonts/LICENSES.md).

## Data tables

| file | what | origin and terms |
|---|---|---|
| `app/data/object_db_v2_index.json` | DCS unit types (name shown, attributes, family) read by the debriefings | the type names and attributes of DCS World's unit database and of the add-on packs named in each entry's `source` field; they belong to Eagle Dynamics and to those packs' authors, and are **not covered by the AGPL licence** — listed so that a debriefing can name what it saw |
| `app/static/dcs_types_livrees.json` | DCS aircraft types and their default liveries | from [DCS Mission Plan](https://github.com/MirabelleBenou/dcs-mission-plan) (`data/liveries_default.json`, same author, AGPL-3.0-or-later); the livery and type names are those of DCS World |

---

*DCS World is a trademark of Eagle Dynamics. This project is not affiliated with or endorsed by Eagle Dynamics.*
