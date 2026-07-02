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

## ✅ Åtkomst (LÖST 2026-07-02): deploy-nyckel

**Grundorsaken** till allt strul: kchd-se är en ny org, och GitHub stänger av **deploy-nycklar som
standard** för nya orgar (GA okt-2024) → "Disabled by kchd-se". Servern kunde därför inte SSH-hämta
detta privata repo.

**Fixat en gång för alla** (org-ägaren):
1. Org → Settings → **Security → Deploy keys → Enabled** (`github.com/organizations/kchd-se/settings/deploy_keys`).
2. La serverns publika nyckel (från `deploy-combined.yml`-körningens Summary) i **detta repo →
   Settings → Deploy keys** (read-only).

Serverns cron (`update_mapping()` i entryscapes `deploy/combined/cloud-init.combined.yml`) SSH-klonar
detta repo var 2:e minut och bygger/startar stacken automatiskt. Repot kan vara **privat**.

**Deploy framöver = git push:**

```bash
git push origin main:live          # servern hämtar via deploy-nyckeln, bygger om ~2-6 min
curl -s https://mapping.kchd.se/health   # → {"status":"ok"}
```

> **⚠️ Vid server-recreate** (`deploy-combined.yml`) genereras en NY deploy-nyckel → lägg in den nya
> i detta repos Deploy keys igen.
>
> **ℹ️ Överflödig workaround:** entryscapes `server-mapping-hook.mjs` (publik-HTTPS-klon) byggdes innan
> deploy-nyckeln löstes. Behövs inte längre men är ofarlig (guardad). Ignorera / städa i egen entryscape-PR.

## Backup-notis

`mapping-data`-volymen överlever omstart/redeploy men **inte** en full server-recreate.
Innan en recreate: säkra volymen, eller acceptera att skarp mapping-data nollställs
(schema-/mappnings-metadata, ingen patientdata). En schemalagd volym-backup är nästa steg.
