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

## Servern finns redan (delad med katalog)

Den delade Hetzner-servern är uppbyggd (`deploy-combined.yml` i entryscape, run #2, 2026-06-25):
katalog + Caddy (två domäner) + `edge`-nät körs. `mapping.kchd.se` → serverns IP (A-record) är satt.

## 🔒 Åtkomst: org-låsningen och den nyckellösa vägen

kchd-se-organisationen blockerar **både deploy-nycklar och personliga SSH-nycklar**, så servern kan
**inte** SSH-hämta detta privata repo. Deploy sker därför via en **postbuild-hook i entryscape**
(`server-mapping-hook.mjs`) som klonar detta repo **PUBLIKT över HTTPS (nyckellöst)** och startar stacken.

**Deploy-flöde (öppna → pusha → stäng), enklast från en lokal Claude Code-session:**

```bash
gh repo edit kchd-se/mapping --visibility public          # 1. öppna tillfälligt
# i entryscape-repot:
git push origin main:live                                 # 2. trigga serverns self-update (hooken kör ~2 min)
curl -s https://mapping.kchd.se/health                    # 3. vänta på {"status":"ok"}
gh repo edit kchd-se/mapping --visibility private          # 4. stäng igen (mapping fortsätter köra)
```

`live`-grenen i detta repo finns (= main). Hooken lämnar en körande stack orörd om en framtida
pull misslyckas (privat) — så privat-igen är säkert.

## Backup-notis

`mapping-data`-volymen överlever omstart/redeploy men **inte** en full server-recreate.
Innan en recreate: säkra volymen, eller acceptera att skarp mapping-data nollställs
(schema-/mappnings-metadata, ingen patientdata). En schemalagd volym-backup är nästa steg.
