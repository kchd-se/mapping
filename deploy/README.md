# Driftsätta v1 på en egen server (t.ex. Hetzner)

Den här mappen sätter upp v1 — **webben + API:t bakom en lösenordsskyddad
adress** — på en Linux-server som redan kör nginx. Den samexisterar med andra
projekt på samma server (eget server-block, egen subdomän, API:t lyssnar bara
lokalt på `127.0.0.1:8010`).

## Förutsättningar på servern
- nginx, git, `python3` + `python3-venv`, och Node.js (för att bygga webben)
- En subdomän som pekar mot serverns IP, t.ex. `mappning.dindomän.se`
- Git-åtkomst till `kchd-se/mapping` (samma som för dina andra repon där)

## Engångsinstallation

```bash
# 0. En plats för appen, ägd av din användare
sudo mkdir -p /opt/mappning && sudo chown "$USER" /opt/mappning

# 1. Bygg koden (klonar repot, installerar Python-deps, bygger webben)
cd /opt/mappning
curl -sSL https://raw.githubusercontent.com/kchd-se/mapping/claude/amazing-carson-mnoy2i/deploy/deploy.sh -o deploy.sh
bash deploy.sh
# (alternativt: klona repot manuellt och kör deploy/deploy.sh därifrån)

# 2. Lösenordsskydd — skapa en användare (du får ange lösenord)
sudo apt-get install -y apache2-utils      # om htpasswd saknas
sudo htpasswd -c /etc/nginx/.htpasswd-mappning kchd

# 3. API:t som tjänst
sudo cp /opt/mappning/deploy/mappning-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mappning-api

# 4. nginx — kopiera, ÄNDRA server_name till din subdomän, aktivera
sudo cp /opt/mappning/deploy/nginx-mappning.conf /etc/nginx/sites-available/mappning
sudo nano /etc/nginx/sites-available/mappning      # byt mappning.EXEMPEL.se
sudo ln -s /etc/nginx/sites-available/mappning /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 5. HTTPS (rekommenderas — annars går lösenordet i klartext)
sudo certbot --nginx -d mappning.dindomän.se
```

Klart: gå till `https://mappning.dindomän.se`, logga in med lösenordet från steg 2.

## Uppdatera till ny version

```bash
cd /opt/mappning && bash deploy.sh
sudo systemctl restart mappning-api
```

## Bra att veta
- **Tillstånd i minnet.** v1 sparar projekt/mappningar i RAM (medvetet i v1).
  Startas API:t om (`systemctl restart`) nollställs allt. Bra för demo/intern
  användning; en databas är ett separat steg om det ska bli skarp drift.
- **En worker.** Tjänsten kör `--workers 1` just därför — flera workers skulle
  ha varsitt minne och ge osammanhängande sessioner.
- **Inloggningen i v1 är simulerad** (roll sätts via header). Lösenordsskyddet i
  nginx är det som faktiskt håller obehöriga ute. Håll sajten bakom det tills
  riktig inloggning finns.
- **Port 8010** valdes för att inte krocka med annat. Krockar den ändå: ändra
  porten i både `mappning-api.service` och `nginx-mappning.conf`.
