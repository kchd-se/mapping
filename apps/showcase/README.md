# Showcase — illustrationer av mappning till FHIR

En **statisk, självförsörjande** sajt (ingen byggkedja, ingen backend, inga externa
CDN-beroenden) som visar de tre interaktiva illustrationerna i ett grid och öppnar var
och en som helsida.

```
apps/showcase/
├── index.html                         # förstasida (grid) + hash-router
├── vendor/                            # React, ReactDOM, Babel v7 (lokala kopior)
└── components/
    ├── mappning-flode.jsx             # #5  MappningFlode        — pilotens flöde
    ├── mappning-byggt-verktyg.jsx     # #6  MappningByggtVerktyg — verktyget i v1 (byggt)
    └── mappning-vision-helhet.jsx     # #7  MappningVisionHelhet  — målbilden (vision)
```

Varje komponent är en fristående IIFE som registrerar sig i `window.kuComponents[...]`
(samma format som presentationsserien "Mappning till FHIR"). `index.html` laddar React +
Babel **från `vendor/`** (inte CDN), kör snippetsen och renderar grid/helsida. JSX
transformeras i webbläsaren av Babel — därför behövs ingen byggkedja.

> **Babel pinnas till v7** (classic JSX-runtime, `React.createElement`). v8 defaultar till
> automatic runtime som genererar `import`-satser och kraschar i ett klassiskt `<script>`.

## Kör lokalt

Filerna laddas via `fetch`, så det krävs en http-server (inte `file://`):

```bash
cd apps/showcase
python -m http.server 5050
# öppna http://localhost:5050
```

Routing: `#/` = grid, `#/MappningFlode` = helsida för en komponent.

## Publicera (statiskt, gratis)

Sajten är ren statik och självförsörjande → lägg upp mappen `apps/showcase/` på valfri
statisk host. Ingen `build` behövs — peka hostens *publish directory* på `apps/showcase`.

| Host | Gratis kommersiellt | Hur |
|---|---|---|
| **Netlify** (Starter) | Ja | Git-koppla repot — `netlify.toml` i repo-roten sätter `base = apps/showcase` och publicerar mappen. Ingen base-katalog behöver anges manuellt. |
| **Cloudflare Pages** | Ja | Koppla repot. Build command: *(tomt)*. Output dir: `apps/showcase`. |
| Vercel | **Nej** för KCHD | Hobby endast icke-kommersiellt; kommersiellt kräver Pro. |
| GitHub Pages | Endast publika repon | Privat org-repo kräver betald GitHub-plan. |

`netlify.toml` i **repo-roten** styr en git-kopplad Netlify-deploy: välj bara repo + branch
i Netlify-UI:t, så byter Netlify till `apps/showcase` och publicerar mappen direkt.

## Lägga till en illustration

1. Lägg en ny `components/<namn>.jsx` som registrerar `window.kuComponents['NyttNamn'] = Komp;`.
2. Lägg till `<script type="text/babel" data-presets="react" src="./components/<namn>.jsx"></script>` i `index.html`.
3. Lägg till en post i `KATALOG`-arrayen i `index.html` (nyckel = registreringsnamnet).

## Framtida väg (om man vill bli av med Babel-i-klienten)

Flytta in illustrationerna i en riktig Vite-build. Det kräver att snippetsen skrivs om från
`window.kuComponents`-IIFE till ES-moduler — vilket vi medvetet **inte** gjort i detta MVP
för att behålla ett enda format mellan presentation och webb.
