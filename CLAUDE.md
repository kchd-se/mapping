# CLAUDE.md

Orientering för Claude Code (och människor) i det här repot. Läs detta först.

## Vad det här är

Ett **schema-till-schema-verktyg för mappning av vårddata** (v1) plus en **dokumentationsdel** som
beskriver den bredare målbilden för "mappning i den regiongemensamma utvecklingsmiljön".

- **Koden** = den körbara v1-realiseringen av en avgränsad del av målbilden (främst Spår C): import
  av källschema, katalogbläddring, fält-mappningsförslag, validering och artefaktexport.
- **Dokumenten** (`docs/`) = strategin, målbilden, jämförelser och presentationer.
- **Showcase-webben** (`apps/showcase/`) = en fristående, statisk sajt (zero-build) som visar tre
  interaktiva illustrationer av mappning till FHIR. Separat från v1-verktyget.
- **Driftpaketet** (`deploy/`) = filer för att köra v1 på en egen server (nginx + systemd + lösenord).

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
- **`apps/showcase/`** — fristående statisk webb (ingen byggkedja, ingen backend): `index.html`
  (grid + hash-router) + tre `window.kuComponents`-komponenter i `components/`. React/Babel **vendoras**
  i `vendor/` (Babel v7, classic JSX-runtime) → självförsörjande. Samma komponentkällor driver även
  presentationsserien. Körs lokalt via valfri http-server, eller dra-och-släpps som ZIP i Netlify.
- **`deploy/`** — driftpaket för v1 på egen server: `deploy.sh` (klona/bygg), `mappning-api.service`
  (uvicorn via systemd, port 8010, `--workers 1` pga in-memory state), `nginx-mappning.conf`
  (lösenordsskyddad subdomän som proxar `/projects` + `/catalog` till API:t). Se `deploy/README.md`.

End-to-end-flöde (användare): skapa projekt → importera källschema → välj målschema → få förslag →
granska & skapa mappningsversion → validera → exportera artefakt + SQL.

> **Insikt — två plan (byggt vs. målbild):** jämförelsen delas i *dataplanet* (pass · kunskapslager ·
> lagring · federation — där målbilden är den större och bygget en delmängd) och *styrplanet* (roller ·
> version/godkänn · audit/proveniens · valideringspolicy — där bygget tvärtom **föregår** målbilden och
> har prototypat kontroll som en federerad nationell tjänst behöver). Se `docs/kchd-vision-vs-build.md`
> §4b och kunskapskällan §10b.

## Publicering (status & beslut, 2026-06-25)

Två separata saker att publicera, med olika vägar:

- **Showcase-webben** — ren statik. Netlify-sajten `kchd-mappning-illustrationer` finns redan i kontot.
  **Git-koppling i Netlify funkar inte** här: `kchd-se` är en privat GitHub-org och Netlifys GitHub-app
  kräver org-admin-godkännande. **Filuppladdning från CI/sandlåda blockeras** av nätverkspolicy (403).
  Fungerande vägar: (a) **dra-och-släpp** ZIP av `apps/showcase/`-innehållet i Netlify (Deploys →
  drag & drop), eller (b) köra en **enfils-HTML** lokalt (allt inlinat; dubbelklick) — komponenterna
  laddas via `fetch` så `file://` kräver annars en lokal http-server.
- **v1-verktyget** — webb + Python-API. Kan **inte** ligga på Netlify (API:t behöver en server). Vägen
  är `deploy/` på en **egen server** (t.ex. Hetzner), bakom **nginx-lösenord** — vilket samtidigt
  täcker att v1:s inloggning bara är **simulerad** (roll via header). Driften körs **från servern**
  (Claude-sessioner saknar SSH/credentials dit; varje session är en ny, isolerad container).
  Kvar för skarp drift: riktig inloggning + databas (in-memory nollställs vid omstart).

## Dokumentindex (`docs/`)

| Fil | Innehåll |
|---|---|
| `kchd_mappning_kunskapskalla.md` | Konsoliderad kunskapskälla: målbilden, den bevisade grunden (kataraktpiloten), terminologi. |
| `kchd_mappning_plan.md` | Färdvägen i fyra spår (A–D), bockas av löpande. |
| `kchd-vision-vs-build.md` | Gap- och konvergensanalys: byggt verktyg ↔ målbild, med filhänvisningar. Inkl. **styrplanet** (§4b) — roller/version/audit/policy som en under-ritad dimension av målbilden. |
| `flode-byggt-vs-malbild.md` | Pedagogisk, illustrationsfärdig jämförelse av de två flödena + diagram (`docs/img/`). |
| `ppt-1-poc-fhir-mappning.md` | Manus, presentation 1 (POC/kataraktpiloten). |
| `ppt-2-helheten-malbild.md` | Manus, presentation 2 (hela maskinen / målbilden). |
| `Helheten - presentation.pptx` | Byggd PowerPoint av presentation 2, på KCHD-mallen. |
| `oppna-fragor.md` | **Logg över sakfrågor under verifiering.** Läs vid arbete med pilotens narrativ. |

## Öppna frågor (läs `docs/oppna-fragor.md`)

- **ÖF-01 — Vem/vad upptäckte de fem semantiska felen i kataraktpiloten?** ✅ **Avgjord 2026-06-18.**
  Bekräftat mot pilotens källfiler (`fhir_mappning_metod.md` §5, `fhir_mappning_analys.md`): det var ett
  **separat AI-verifieringssteg** — inte en mänsklig granskare — som fångade alla fem felen. Människan i
  loopen kvarstår som den som slutligt **godkänner**. Texterna i `ppt-1-poc-fhir-mappning.md` och
  `kchd_mappning_kunskapskalla.md` (§11–§13) är uppdaterade; loggen ligger i `docs/oppna-fragor.md`.

## Deploy / drift (skarpt på Hetzner)

Mapping körs skarpt på **https://mapping.kchd.se**, på **samma Hetzner-server** som
katalog.kchd.se (entryscape) — ingen extra serverkostnad, apparna frikopplade. Full guide:
[`docs/DEPLOY.md`](docs/DEPLOY.md).

- **Paketering:** `Dockerfile.api` (FastAPI/uvicorn :8000) + `Dockerfile.web` (Vite→nginx,
  same-origin API-proxy) + `docker-compose.hetzner.yml` (externt `edge`-nät, `mapping-data`-volym).
- **Lagring:** tillstånd sparas till `MAPPING_DATA_DIR=/data` (snapshot.json i named volume) →
  skarp data överlever omstart/redeploy. Health: `GET /health`.
- **Deploy = git push:** servern (cron) hämtar `live`-grenen var 2:e min och bygger om.
  `git push origin main:live`.
- **Server-orkestreringen** (delad Caddy/två domäner, self-update) ligger i entryscape-repot:
  `deploy/combined/` + workflow `deploy-combined.yml`.
- **✅ ÅTKOMST LÖST (2026-07-02) — deploy-nyckel.** Grundorsaken var att kchd-se (ny org) hade **deploy-nycklar
  avstängda som standard** (GitHub GA okt-2024) → "Disabled by kchd-se". **Fixat:** org-ägaren slog på
  Org → Settings → Security → **Deploy keys → Enabled** och lade serverns nyckel i **detta repo → Settings →
  Deploy keys** (read-only). Serverns cron (`update_mapping()` i entryscapes cloud-init) SSH-klonar detta repo
  var 2:e min → bygger + startar stacken automatiskt. **Deploy = `git push origin main:live` här** (servern
  hämtar via nyckeln; repot kan vara **privat**). Varje server-recreate ger ny nyckel som måste läggas in igen.
- **ℹ️ Överflödig workaround:** entryscapes `server-mapping-hook.mjs` (publik-HTTPS-klon) byggdes innan
  deploy-nyckeln löstes — inte längre nödvändig, men ofarlig (guardad). Ignorera.

## Arbetssätt i det här repot

- Var **källtrogen**: i dokument som skiljer på byggt och målbild — markera bara det som verkligen
  finns i koden som "byggt". Hitta inte på funktioner (jfr stubbade adaptrar).
- **Verifiera innan du flippar ett påstående.** Öppna frågor loggas i `oppna-fragor.md` och flaggas
  in-line; de skrivs inte om förrän de är bekräftade.
- Terminologi: "den regiongemensamma utvecklingsmiljön" (helheten), "den centrala noden" (central
  komponent). Undvik "hubb"/"vårddatahubb" i formell text.
