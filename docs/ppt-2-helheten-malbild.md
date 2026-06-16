# PowerPoint 2: Helheten — vart vi är på väg

**Syfte:** Förklara hur allt hänger ihop när vi är klara.
**Längd:** ca 11–13 slides. Håll det enkelt. En tanke per slide.

---

## Slide 1 — Titel
- Rubrik: "Helheten — vart vi är på väg"
- Underrubrik: Mappning i den regiongemensamma utvecklingsmiljön
- Talarstöd: Det här är målbilden. Inte allt är byggt än.

## Slide 2 — Problemet vi löser
- Data finns i regionernas källsystem.
- Många mottagare vill ha den i olika format.
- Mottagare: kvalitetsregister, Socialstyrelsen, forskning, Europa.
- Idag görs det manuellt och tar månader.
- Talarstöd: Vi vill göra det snabbare och mer enhetligt.

## Slide 3 — Grundidén
- En mappningsmotor som körs i flera pass.
- En uppsättning kunskapskällor som motorn frågar.
- Regionerna kör koden i sin egen miljö.
- Den centrala noden tar emot och sammanställer.
- Talarstöd: Samma federerade princip som i pocken.

## Slide 4 — Två saker att hålla isär
- Referenskällor: vad något betyder och var det hamnar.
- Målscheman: hur en viss mottagare vill ha sin data.
- Ny mottagare = nytt målschema kopplas in.
- Motorn behöver inte byggas om.
- Talarstöd: Detta är det som gör modellen utbyggbar.

## Slide 5 — Flödet i sex steg
- 1. Hämta källdata i regionen.
- 2. Pass 1: källa → standardmodell.
- 3. Pass 2: standardmodell → utgående format.
- 4. Centralt: Pass 3 tar emot och normaliserar.
- 5. Pass 4: standardmodell → OMOP för analys.
- 6. Data tillgängliggörs och beskrivs i kataloger.
- Talarstöd: Fyra av stegen är pass genom motorn.

## Slide 6 — Motorn
- En kodbas med utbytbara moduler.
- Varje pass: läs in, fråga kunskapskällor, skriv ut.
- Bevarar ursprungskoder (t.ex. ICD-10, KVÅ).
- Talarstöd: Samma motor, olika pass.

## Slide 7 — De fyra kunskapslagren
- Organik: vad mottagaren vill ha.
- Terminologitjänsten: vad något heter i standard.
- Datakatalogen: var data finns i källsystemet.
- AI-assistenten: vad mappningen borde bli.
- Talarstöd: Under en transformation frågar motorn alla fyra.

## Slide 8 — AI med människan i loopen
- Assistenten föreslår en mappning.
- Visar direkt när den är säker.
- Visar en rankad lista när den är osäker.
- Människan godkänner eller rättar.
- Varje rättning gör maskinen bättre.
- Talarstöd: Maskinen gör grovarbetet, människan kvalitetssäkrar.

## Slide 9 — Lagring i tre lager
- openEHR: den löpande journalen (operativt).
- OMOP: populationsanalys och forskning.
- Rålogg: rådata landar först, normaliseras sedan.
- Talarstöd: Olika lager för olika behov.

## Slide 10 — Oberoende av plattform
- Koden körs i regionens egen miljö.
- Det spelar ingen roll vilken plattform regionen har.
- Kravet ligger i ett gemensamt kontrakt.
- Talarstöd: Hävstången ligger i kontraktet, inte i leverantören.

## Slide 11 — Vad som redan finns
- Verktyg som importerar scheman och föreslår mappningar.
- En sökbar katalog över scheman.
- Validering och export av mappningsartefakter.
- Talarstöd: En första byggsten mot motorn finns redan.

## Slide 12 — Vägen dit (fyra spår)
- A: Stäng pilotens kvarvarande luckor.
- B: Lägg grunden (maskinläsbar export, terminologi).
- C: Bygg motorn stegvis.
- D: Beslut om namn, juridik och förankring.
- Talarstöd: Planen bockas av löpande.

## Slide 13 — Avslut
- Pocken bevisade metoden.
- Målbilden visar var vi ska.
- Vi bygger dit steg för steg.
- Talarstöd: Knyt ihop med presentation 1.
