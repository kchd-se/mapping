# Presentation 1: Så gjorde vi i pocken

*Talarmanus + slides. Skrivet för att läsas högt. En idé per slide.*

---

## Läs det här först (60 sekunder)

Vi tog ett vanligt tal ur Västra Götalandsregionens system — hur många patienter som väntat
länge på en starroperation. Sedan översatte vi det talet till ett gemensamt språk som andra
kan läsa: FHIR. Vi gjorde det på ett kontrollerat sätt, ett fält i taget, och vi skrev ner
varför varje koppling var rätt. Det viktiga: regionens data lämnade aldrig regionen. Vi körde
koden hemma hos dem och skickade bara svaret vidare. Det blev körbar kod som en dator kunde
godkänna. Och vi var ärliga med vad vi bevisade och inte bevisade. Det är hela poängen med
pocken: vi visade att metoden håller.

## Miniordlista (säg det så här)

- **Mappning** = översättning. Att säga samma sak på ett annat språk.
- **FHIR** = ett gemensamt språk för vårddata, som andra system och länder förstår.
- **Fält** = en enskild ruta med data, t.ex. "antal som väntat över 90 dagar".
- **Federerat** = data stannar hemma. Vi skickar receptet, inte råvarorna.
- **Validera** = en dator kontrollerar att resultatet är rätt byggt.

---

## Slide 1 — Så gjorde vi i pocken

**På skärmen:** Titeln. En bild på ett öga eller en kö.

**Du säger:**
"Det här är berättelsen om hur vi tog ett tal ur ett av regionens system och översatte det så
att resten av Sverige och Europa kan läsa det. Vi gjorde det med starroperationer i Västra
Götaland. Och det fungerade."

---

## Slide 2 — Problemet vi ville lösa

**På skärmen:** Två system som inte förstår varandra. En frågande min emellan.

**Du säger:**
"Varje region har sin data i sina egna system, på sitt eget sätt. När någon utanför vill ha den —
Socialstyrelsen, ett kvalitetsregister, en forskare — passar den inte. Idag översätts det för hand,
om och om igen. Vi ville visa att det går att göra prydligt och pålitligt."

---

## Slide 3 — Vad vi konkret gjorde

**På skärmen:** Ett tal till vänster, FHIR-logotyp till höger, en pil emellan.

**Exempel:** Antalet patienter som väntat på en starroperation → ett fält i en FHIR-rapport.

**Du säger:**
"Vi tog väntetiderna för starroperationer i Västra Götaland. Alltså färdiga siffror — hur många
som väntat, hur länge. Inga enskilda patienter, bara statistik. Och vi översatte de siffrorna
till FHIR, det gemensamma språket."

---

## Slide 4 — Datan lämnade aldrig regionen

**På skärmen:** Ett hus (regionen) med data kvar inuti. Bara en liten kuvert-pil går ut.

**Exempel:** Koden kördes inne i VGR:s miljö. Bara det färdiga svaret skickades vidare.

**Du säger:**
"Det här är viktigt. Vi flyttade inte regionens data någonstans. Vi skickade vårt recept till
deras kök, de lagade rätten hemma, och bara den färdiga rätten skickades ut. Regionen behöll
hela tiden kontrollen. Det kallas federerat."

---

## Slide 5 — Hur vi översatte ett enda fält

**På skärmen:** Två rutor sida vid sida. Vänster: "kolumn i VGR:s system". Höger: "fält i FHIR".
En förstoringsglas-ikon över dem.

**Exempel:** Vi läste vad FHIR säger att fältet betyder. Vi läste vad kolumnen faktiskt innehåller.
Vi kopplade ihop dem bara om de betyder samma sak.

**Du säger:**
"Vi tog ett fält i taget. För varje fält ställde vi en enkel fråga: betyder den här kolumnen
verkligen samma sak som det här FHIR-fältet? Vi gissade inte. Vi jämförde definition mot
definition, och kopplade bara ihop dem när de matchade på riktigt."

---

## Slide 6 — Varför vi litade på varje koppling

**På skärmen:** Fyra enkla ikoner i rad: bok, flagga, klocka, glödlampa.

**Exempel:** Varje koppling vilade på en av fyra grunder:
1. Det står svart på vitt i FHIR-specifikationen.
2. Det finns en svensk officiell källa.
3. Vi använde en tillfällig adress tills den rätta är spikad.
4. Vi tog ett eget beslut — och skrev ner varför.

**Du säger:**
"För varje koppling kunde vi svara på frågan 'hur vet ni att det är rätt?'. Antingen stod det i
specifikationen, eller fanns en svensk källa, eller så satte vi en tillfällig lösning vi kan byta
senare, eller så tog vi ett eget beslut och motiverade det. Inget var en tyst gissning."

---

## Slide 7 — När det såg rätt ut men var fel

**På skärmen:** En bock som blir ett kryss. Texten "5 gånger".

**Exempel:** Fem kopplingar var korrekt byggd FHIR — men siffran hamnade i fel fält. Ett separat
granskningssteg läste varje fälts definition mot vad siffran faktiskt betydde och fångade dem. I
pocken kördes det steget med AI — samma AI som gjort utkastet.

**Du säger:**
"Här är det mest lärorika. Fem gånger var översättningen tekniskt felfri men ändå fel — siffran
låg i fel ruta. En formell kontroll hade sagt 'giltig FHIR'. Det som såg felet var ett separat
granskningssteg som jämförde betydelse mot betydelse — i pocken körde vi det med AI, inte en
människa. Lärdomen är dubbel: kontrollera betydelsen och inte bara formen, och lita inte på första
utkastet — kör alltid det granskande steget. Människan är kvar som den som slutligt godkänner, och
den granskningen är obligatorisk. Hos oss innebar den ingen ändring — vi accepterade AI:ns förslag
till fullo, just för att granskningssteget redan fångat felen."

---

## Slide 8 — Det blev körbar kod

**På skärmen:** En liten kodsnutt som blir en grön bock ("validerad").

**Exempel:** Vi byggde en referens i Python. Den producerade en färdig FHIR-rapport. En dator
kontrollerade den och godkände den mot standarden.

**Du säger:**
"Det här var inte bara ett dokument. Vi skrev kod som faktiskt körde, spottade ut en färdig
FHIR-rapport, och en dator godkände att den var rätt byggd. Alltså: från idé till något som
fungerar på riktigt."

---

## Slide 9 — Vad vi bevisade, och var gränsen går

**På skärmen:** Två kolumner. "Vi visade" och "Vi visade inte ännu".

**Exempel:**
- Vi visade: en översättning kan byggas, dokumenteras och granskas; samma kod kan köras i regionen
  och samlas centralt; en ny mottagare kan kopplas in utan att byta metod.
- Vi visade inte ännu: hela patientresan, bara aggregerad statistik.

**Du säger:**
"Vi bevisade att metoden håller, att den går att köra hemma hos regionen, och att den går att
återanvända. Vi bevisade inte hela patientresan — vi körde statistik, inte enskilda patienter.
Och en sak till: en formell validering räcker inte för att garantera att en översättning är rätt —
det krävs ett granskande steg som jämför betydelse, och en människa som slutligt godkänner och kan
både källan och målet. Det leder oss till nästa presentation — hur hela maskinen ser ut när den är
färdig."
