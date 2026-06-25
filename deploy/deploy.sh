#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Bygg/uppdatera v1 på servern. Kör som den användare som äger /opt/mappning.
# Idempotent: kan köras om vid varje ny version.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Inställningar (ändra vid behov) ──────────────────────────────────
APP_DIR=/opt/mappning
REPO=https://github.com/kchd-se/mapping.git
BRANCH=claude/amazing-carson-mnoy2i      # byt till "main" när PR #5 är mergad
# ─────────────────────────────────────────────────────────────────────

# 1. Hämta/uppdatera koden
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

# 2. Python-miljö för API:t
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 3. Bygg webben → statiska filer i apps/web/ui/dist
#    Tom VITE_API_BASE_URL = samma domän som API:t (nginx proxar /projects + /catalog).
cd "$APP_DIR/apps/web/ui"
export VITE_API_BASE_URL=""
npm ci
npm run build

echo
echo "✅ Byggt. Webben ligger i $APP_DIR/apps/web/ui/dist, API:t startas via systemd."
echo "   Första gången: installera systemd-tjänsten + nginx-konfigen (se deploy/README.md)."
echo "   Vid uppdatering: kör om detta skript och 'sudo systemctl restart mappning-api'."
