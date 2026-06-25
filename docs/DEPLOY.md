# Deploy: mapping på Hetzner (delad server med katalog)

Mapping körs skarpt på **https://mapping.kchd.se** på **samma Hetzner-server** som
katalog.kchd.se (entryscape) — ingen extra serverkostnad. Apparna är frikopplade:
om mapping är nere påverkas inte katalogen och tvärtom.

## Arkitektur

```
                      Hetzner-server (en maskin)
  Internet ──▶ Caddy (80/443, auto-HTTPS)
                 ├─ katalog.kchd.se ─▶ entryscape-frontend ─▶ EntryStore
                 └─ mapping.kchd.se ─▶ mapping-web (nginx) ─▶ mapping-api (FastAPI)
                                                                   └─ /data (named volume)
```

- **mapping-web** (`Dockerfile.web`): bygger Vite-frontend, servar SPA + proxar API-prefixen
  (`/projects`, `/catalog`, `/health`, `/openapi.json`, `/docs`, `/redoc`) till mapping-api.
  Samma origin → inga CORS-problem.
- **mapping-api** (`Dockerfile.api`): FastAPI/uvicorn på :8000. Lagrar tillstånd i
  `MAPPING_DATA_DIR=/data` (snapshot.json i named volume `mapping-data`) → **skarp data
  överlever omstart och redeploy**.
- Caddy (i entryscapes stack) når mapping-web via det externa docker-nätet **`edge`**.

## Deploy = git push (noll GitHub Actions)

Servern har en self-update-cron som var 2:e minut hämtar `live`-grenen och bygger om.

```bash
git checkout -B live origin/main   # eller din gren
git push origin live
```

~2 min senare är mapping uppdaterad. (Samma mönster som entryscape.)

## Engångs-uppsättning (delar servern)

Görs en gång, från entryscape-repot (det äger serverns livscykel):

1. **Sekret:** `HETZNER_SECRET` finns redan i detta repo. Entryscape-repot har
   `HETZNER_TOKEN` + `RAILWAY_ENTRYSTORE_PW`.
2. **DNS:** `mapping.kchd.se` → serverns IP (A-record). *(Klart.)*
3. **Kör** `deploy-combined.yml` i entryscape-repot (bygger om servern: katalog +
   mapping, katalog återställs från färskaste backupen).
4. Workflowen skriver ut en **deploy-nyckel** → lägg in den i **detta repo**:
   Settings → Deploy keys → Add deploy key (read-only räcker).
5. Skapa `live`-grenen här (`git push origin main:live`). Servern startar mapping ~2 min senare.

## Backup-notis

`mapping-data`-volymen överlever omstart/redeploy men **inte** en full server-recreate.
Innan en recreate: säkra volymen, eller acceptera att skarp mapping-data nollställs
(schema-/mappnings-metadata, ingen patientdata). En schemalagd volym-backup är nästa steg.
