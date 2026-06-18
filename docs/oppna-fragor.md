# Öppna frågor under verifiering

**Roll:** Logg för sakfrågor som ännu inte är bekräftade men som påverkar hur vi formulerar oss i
presentationer och kunskapsbas. En fråga lämnar den här loggen först när någon med källkännedom har
bekräftat svaret — då uppdateras de berörda filerna och raden flyttas till "Avgjorda".

> Princip: vi ändrar **inte** ett påstående i kunskapsbasen eller presentationerna förrän frågan är
> avgjord. Tills dess står ursprungstexten kvar, med en synlig flagga som pekar hit.

---

## ÖF-01 · Vem/vad upptäckte de fem semantiska felen i kataraktpiloten?

**Status:** 🔎 Under verifiering (2026-06-18) — uppgiftslämnaren letar efter källa.

### Vad dokumenten säger idag
Nuvarande text tillskriver upptäckten en **människa**, och använder kontrasten "maskin godkänner,
människa ser felet" som själva beviset för människan-i-loopen:

- `docs/ppt-1-poc-fhir-mappning.md`, slide 7: "Granskningen fångade dem…" och "En dator hade sagt
  'godkänt'. En människa såg att det var fel ändå."
- `docs/kchd_mappning_kunskapskalla.md` §11: "Den semantiska kontrollen är prövad: fem mappningar var
  giltig FHIR och ändå fel element och korrigerades."
- `docs/kchd_mappning_kunskapskalla.md` §13: "ingen motor bevisar att en semantisk mappning är
  korrekt … en granskning av någon som kan både källmodellen och målformatet … den ersätter inte den
  mänskliga bedömningen."

### Funderingen som ska prövas
Att det **i praktiken var en AI** som upptäckte de fem problemen — fast i ett
**kvalitetssäkringssteg** — och inte (enbart) en människa vid manuell granskning.

### Varför det spelar roll (inte en detalj)
Det här är ett **bärande argument**. Om en AI flaggade felen försvagas påståendet "en maskin hade
sagt godkänt" på *ett* ställe, men *stärker* AI-lagrets story (C3) på ett annat. Det får alltså inte
smygas in — det måste formuleras om medvetet och konsekvent på alla tre ställena ovan.

### Två saker som inte får blandas ihop
1. **Vem genererade mappningsförslaget** — här kan en AI/LLM mycket väl ha varit med.
2. **Vad som fångade de fem felen** — dokumenten säger människa; funderingen säger AI i ett QA-steg.
   Det är punkt 2 som ska verifieras.

### Underfråga om det bekräftas
Flaggade AI:n bara **kandidater** som en människa sedan bekräftade (AI föreslår, människa avgör), eller
fångade AI:n felen **helt själv**? Formuleringen måste spegla exakt vilket.

### Om det bekräftas — så här uppdateras texten
- POC slide 7: skriv om så att QA-steget (AI) får sin roll, men behåll att *strukturell* validering
  ensam inte räcker. Undvik att överdriva åt något håll.
- Kunskapskällan §11 och §13: nyansera "den mänskliga bedömningen" till att beskriva samspelet
  maskin-QA + mänsklig bekräftelse, i linje med underfrågans svar.
- Speglas i `docs/flode-byggt-vs-malbild.md` (raden om "Lärande" / människan i loopen) och i
  `docs/kchd-vision-vs-build.md` §5 punkt 4 (lärloopen audit→förslag).

---

## Avgjorda frågor

_(inga ännu)_
