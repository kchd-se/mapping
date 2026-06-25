# Showcase — illustrationer av mappning till FHIR

En **statisk** sajt (ingen byggkedja, ingen backend) som visar de tre interaktiva
illustrationerna i ett grid och öppnar var och en som helsida.

```
apps/showcase/
├── index.html                         # förstasida (grid) + hash-router
└── components/
    ├── mappning-flode.jsx             # #5  MappningFlode      — pilotens flöde
    ├── mappning-byggt-verktyg.jsx     # #6  MappningByggtVerktyg — verktyget i v1 (byggt)
    └── mappning-vision-helhet.jsx     # #7  MappningVisionHelhet  — målbilden (vision)
```

Varje komponent är en fristående IIFE som registrerar sig i `window.kuComponents[...]`
(samma format som presentationsserien "Mappning till FHIR"). `index.html` laddar
React + Babel från CDN, kör snippetsen, och renderar grid/helsida. JSX transformeras
i webbläsaren — därför behövs ingen byggkedja.

## Kör lokalt

Filerna laddas via `fetch`, så det krävs en http-server (inte `file://`):

```bash
cd apps/showcase
python -m http.server 5050
# öppna http://localhost:5050
```

Routing: `#/` = grid, `#/MappningFlode` = helsida för en komponent.

## Publicera (statiskt, gratis)

Sajten är ren statik → lägg upp mappen `apps/showcase/` på valfri statisk host.

| Host | Gratis kommersiellt | Hur |
|---|---|---|
| **Cloudflare Pages** | Ja | Koppla repot. Build command: *(tomt)*. Output dir: `apps/showcase`. |
| **Netlify** (Starter) | Ja | Koppla repot. Publish directory: `apps/showcase`. (`netlify.toml` kan läggas till.) |
| Vercel | **Nej** för KCHD | Hobby är endast icke-kommersiellt; kommersiellt kräver Pro. |
| GitHub Pages | Endast publika repon | Privat org-repo kräver betald GitHub-plan. |

Ingen `build` behövs — peka bara hostens *output/publish directory* på `apps/showcase`.

### Not om CDN-beroenden
React, ReactDOM och Babel hämtas från `unpkg.com` vid sidladdning. Det fungerar direkt,
men kräver att klientens webbläsare når unpkg. För en helt självförsörjande sajt (eller
om man vill bli av med Babel-transformen i klienten) är nästa steg att flytta in
illustrationerna i en riktig Vite-build — men det kräver att snippetsen skrivs om från
`window.kuComponents`-IIFE till ES-moduler, vilket vi medvetet **inte** gjort i detta
MVP för att behålla ett enda format mellan presentation och webb.

## Lägga till en illustration

1. Lägg en ny `components/<namn>.jsx` som registrerar `window.kuComponents['NyttNamn'] = Komp;`.
2. Lägg till `<script type="text/babel" src="./components/<namn>.jsx"></script>` i `index.html`.
3. Lägg till en post i `KATALOG`-arrayen i `index.html` (nyckel = registreringsnamnet).
