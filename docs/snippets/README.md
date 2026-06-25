# Snippets — illustrationskomponenter (`window.kuComponents`)

Fristående React-komponenter som registrerar sig i `window.kuComponents[...]`, i samma
format som presentationsserien "Mappning till FHIR". De är **inte** en del av webb-appen i
`apps/web/ui/` — de är inklistringsbara illustrationer för presentationer/kunskapsstyrning.
Varje fil är en IIFE som förutsätter ett globalt `React` och en JSX-transform i värdmiljön,
plus att `window.kuComponents` redan finns.

| Fil | Registrerar | Beskriver |
|---|---|---|
| `mappning-byggt-verktyg.jsx` | `MappningByggtVerktyg` | **Byggt** — verktyget i v1 som det faktiskt finns i koden: källschema → katalog/målschema → förslag → granska → validering → export (artefakt + SQL, körs ej). Källtroget; håller v1:s röda linjer (RL-01/02/03). |
| `mappning-vision-helhet.jsx` | `MappningVisionHelhet` | **Målbild** — hela den regiongemensamma utvecklingsmiljön: en motor, fyra pass, fyra kunskapslager, federerad körning, tre-lagers-lagring. Vision, inte byggt. |

De delar visuellt språk och struktur med syskonkomponenten `MappningFlode` (#5): paletten `C`,
typsnitten Libre Franklin / IBM Plex Sans / IBM Plex Mono, och mönstret
pipeline → SVG-kopplingsband → källor/lager → legend → detaljkort → stegberättelse → resultat.

Skillnaden i avsikt följer repots arbetssätt (se `CLAUDE.md` och
[`docs/flode-byggt-vs-malbild.md`](../flode-byggt-vs-malbild.md)): den byggda komponenten
påstår bara det som finns i koden, vision-komponenten är uttryckligen märkt som målbild.

Källor för innehållet: [`kchd-vision-vs-build.md`](../kchd-vision-vs-build.md),
[`kchd_mappning_plan.md`](../kchd_mappning_plan.md),
[`kchd_mappning_kunskapskalla.md`](../kchd_mappning_kunskapskalla.md).
