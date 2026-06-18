# CLAUDE.md

Orientering för Claude Code (och människor) i det här repot. Läs detta först.

## Vad det här är

Ett **schema-till-schema-verktyg för mappning av vårddata** (v1) plus en **dokumentationsdel** som
beskriver den bredare målbilden för "mappning i den regiongemensamma utvecklingsmiljön".

- **Koden** = den körbara v1-realiseringen av en avgränsad del av målbilden (främst Spår C): import
  av källschema, katalogbläddring, fält-mappningsförslag, validering och artefaktexport.
- **Dokumenten** (`docs/`) = strategin, målbilden, jämförelser och presentationer.

## Röda linjer i v1 (icke förhandlingsbara)

- **Ingen exekvering** av transformationsskript. SQL genereras men körs aldrig (RL-01).
- **Ingen patient-/individdata** läses in (RL-02). Allt sker på schema-/metadatanivå.
- **Standarder är öppna/konfigurerbara** (FHIR, OMOP …) — inte hårdkodade (RL-03).
- **UI är kontraktsdrivet** — allt beteende härleds ur `apps/api/openapi.json`.

## Kommandon

```bash
# Python-miljö
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Kör allt (API + webb)
npm run dev            # API på :8000, webb via Vite

# Tester
npm test               # api + web
npm run test:api       # pytest (apps/api + packages/*)
npm run test:web       # vitest

# Regenerera OpenAPI-kontraktet
npm run openapi
```

## Arkitektur i korthet

- **`apps/api`** — FastAPI. `main.py::create_app()` komponerar sju routrar:
  projects · schemas · catalog · suggestions · mappings · validation · export.
  Tillstånd är **in-memory** (`apps/api/state.py`), injicerat via `deps.py`. RBAC är **simulerad**
  via `X-User-Id` / `X-User-Role` (roller: viewer/analyst/approver/admin).
- **`apps/web/ui`** — React + Vite + TanStack Query, kontraktsdrivet mot OpenAPI.
- **`packages/`** — domänlogik, format-oberoende:
  - `core/` — `CanonicalSchema`/`CanonicalField` (navet), `MappingProject/Version/Rule`, `AuditEvent`, artefakt-serialisering.
  - `adapters/` — input-parsers. **Fungerar:** JSON Schema, CSV. **Stubbar:** FHIR-profil, OMOP, openEHR, SQL DDL, Parquet.
  - `catalog/` — schemaregistrering, versionshantering, pinning.
  - `suggestions/` — `SuggestionEngine` + viktade strategier (namn/typ/kardinalitet/constraints) + valfri semantisk provider (default lexikal; Azure OpenAI om nyckel finns).
  - `validation/` — regler + policy (allvarlighetsgrad per anrop, ej hårdkodad).
  - `script_gen/` — `SqlInsertSelectGenerator` (deterministisk SQL, **körs ej**).
- **`apps/api/standards/`** — förinlästa **målscheman**: FHIR R4 (9 resurser) + OMOP CDM 5.4 (11 tabeller), laddas vid uppstart.

End-to-end-flöde (användare): skapa projekt → importera källschema → välj målschema → få förslag →
granska & skapa mappningsversion → validera → exportera artefakt + SQL.

## Dokumentindex (`docs/`)

| Fil | Innehåll |
|---|---|
| `kchd_mappning_kunskapskalla.md` | Konsoliderad kunskapskälla: målbilden, den bevisade grunden (kataraktpiloten), terminologi. |
| `kchd_mappning_plan.md` | Färdvägen i fyra spår (A–D), bockas av löpande. |
| `kchd-vision-vs-build.md` | Gap- och konvergensanalys: byggt verktyg ↔ målbild, med filhänvisningar. |
| `flode-byggt-vs-malbild.md` | Pedagogisk, illustrationsfärdig jämförelse av de två flödena + diagram (`docs/img/`). |
| `ppt-1-poc-fhir-mappning.md` | Manus, presentation 1 (POC/kataraktpiloten). |
| `ppt-2-helheten-malbild.md` | Manus, presentation 2 (hela maskinen / målbilden). |
| `Helheten - presentation.pptx` | Byggd PowerPoint av presentation 2, på KCHD-mallen. |
| `oppna-fragor.md` | **Logg över sakfrågor under verifiering.** Läs vid arbete med pilotens narrativ. |

## Öppna frågor (läs `docs/oppna-fragor.md`)

- **ÖF-01 — Vem/vad upptäckte de fem semantiska felen i kataraktpiloten?** Dokumenten säger idag att
  en **människa** fångade dem ("en dator hade sagt godkänt, en människa såg felet"). Det utreds om
  det i praktiken var en **AI i ett kvalitetssäkringssteg**. Detta är ett *bärande* argument för
  människan-i-loopen — **ändra inte** påståendena i `ppt-1-poc-fhir-mappning.md` eller
  `kchd_mappning_kunskapskalla.md` (§11/§13) förrän frågan är avgjord. Berörda ställen är flaggade
  med "🔎 Under verifiering (ÖF-01)".

## Arbetssätt i det här repot

- Var **källtrogen**: i dokument som skiljer på byggt och målbild — markera bara det som verkligen
  finns i koden som "byggt". Hitta inte på funktioner (jfr stubbade adaptrar).
- **Verifiera innan du flippar ett påstående.** Öppna frågor loggas i `oppna-fragor.md` och flaggas
  in-line; de skrivs inte om förrän de är bekräftade.
- Terminologi: "den regiongemensamma utvecklingsmiljön" (helheten), "den centrala noden" (central
  komponent). Undvik "hubb"/"vårddatahubb" i formell text.
