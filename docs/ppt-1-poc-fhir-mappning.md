# PowerPoint 1: Så mappade vi mot FHIR i pocken

**Syfte:** Förklara hur kataraktpiloten mappade mot FHIR.
**Längd:** ca 10–12 slides. Håll det enkelt. En tanke per slide.

---

## Slide 1 — Titel
- Rubrik: "Så mappade vi mot FHIR i pocken"
- Underrubrik: Kataraktpiloten med Västra Götalandsregionen
- Talarstöd: Det här är ett bevis på att metoden fungerar.

## Slide 2 — Vad vi gjorde
- Vi tog regionens väntetidsdata.
- Vi mappade den till FHIR R4.
- Vi gjorde det på aggregerad nivå (statistik, inte enskilda patienter).
- Talarstöd: Ett första, avgränsat steg. Inte hela flödet.

## Slide 3 — Hur vi körde det
- Koden kördes i regionens egen miljö.
- Regionen behöll kontrollen över sin data.
- Bara resultatet skickades vidare.
- Resultatet sammanställdes centralt.
- Talarstöd: Detta kallas federerad körning.

## Slide 4 — Metoden i sju steg
1. Inventera nyckeltalen.
2. Slå mot FHIR R4-specen.
3. Slå mot svenska profiler och OID-register.
4. Fatta designbesluten.
5. Skapa VQL-vyn.
6. Testa mot testdata.
7. Logga osäkerheterna.
- Talarstöd: Stegen är nedskrivna och kan återanvändas.

## Slide 5 — Hur vi mappade varje variabel
- Vi tog en kolumn i taget.
- Vi läste vad FHIR-specen säger att fältet betyder.
- Vi jämförde med vad kolumnen faktiskt innehåller.
- Bara om de betyder samma sak kopplade vi ihop dem.
- Talarstöd: Vi prövar betydelse, inte bara form.

## Slide 6 — Fyra grunder för varje koppling
- 1. Bekräftad mot FHIR R4-specen.
- 2. Bekräftad svensk URI med källa.
- 3. Provisorisk URI (samlad på ett ställe, byts senare).
- 4. Eget designbeslut med motivering.
- Talarstöd: Varje val har en uttalad grund. Inget är gissat i tysthet.

## Slide 7 — Kvaliteten testades
- Fem mappningar var giltig FHIR men fel element.
- Vi hittade dem och rättade dem.
- Talarstöd: Det visar att kontrollen fångar verkliga fel.

## Slide 8 — Det blev körbar kod
- Vi byggde en referens i Python.
- Den producerade en FHIR Bundle.
- Den validerades mot R4.
- Talarstöd: Från beskrivning till något som faktiskt kör.

## Slide 9 — Den ärliga gränsen
- Ingen maskin kan bevisa att en mappning är "rätt".
- En människa som kan både källan och målet måste granska.
- Maskinen sänker arbetet och gör besluten spårbara.
- Talarstöd: Var ärlig med detta. Det gör grunden trovärdig.

## Slide 10 — Vad piloten bevisade
- En mappning kan byggas, dokumenteras och verifieras.
- Samma kod kan köras i regionen och sammanställas centralt.
- Ett nytt målformat kan kopplas in utan att byta metod.
- Talarstöd: Tre saker som hela målbilden vilar på.

## Slide 11 — Vad piloten inte bevisade
- Inte openEHR-kärnan.
- Inte patientnivå (bara aggregerad statistik).
- Inte återanvändning över alla fyra pass.
- Talarstöd: Säg det rakt. Det visar att vi vet var vi står.

## Slide 12 — Avslut
- Piloten är en tidig, handkörd version av motorn.
- Metoden, verifierbarheten och federationen är bevisade.
- Nästa steg är att skala upp med en motor.
- Talarstöd: Brygga över till presentation 2 om helheten.
