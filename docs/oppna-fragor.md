# Öppna frågor under verifiering

**Roll:** Logg för sakfrågor som ännu inte är bekräftade men som påverkar hur vi formulerar oss i
presentationer och kunskapsbas. En fråga lämnar den här loggen först när någon med källkännedom har
bekräftat svaret — då uppdateras de berörda filerna och raden flyttas till "Avgjorda".

> Princip: vi ändrar **inte** ett påstående i kunskapsbasen eller presentationerna förrän frågan är
> avgjord. Tills dess står ursprungstexten kvar, med en synlig flagga som pekar hit.

---

## ÖF-01 · Vem/vad upptäckte de fem semantiska felen i kataraktpiloten?

**Status:** ✅ Avgjord (2026-06-18) — bekräftat mot pilotens källfiler (se "Avgörande" nedan).

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

### Avgörande (2026-06-18)
Bekräftat mot pilotens egna källfiler, som uppgiftslämnaren tillhandahöll:

- `fhir_mappning_metod.md` §5: "Där hittade och korrigerade AI (Claude) fem mappningar … samma AI hade
  genererat den ursprungliga mappningen, och det var i ett separat verifieringssteg — inte genom
  mänsklig granskning — som felen upptäcktes."
- `fhir_mappning_analys.md`, avsnittet "Verifiering av radnivå-mappningar (fas 4)": "Felen … upptäcktes
  också av AI, i ett separat verifieringssteg … Ingen mänsklig granskare var inblandad i att hitta dem."

**Svar:** Det var en **AI** (samma AI som genererade utkastet) som i ett **separat verifieringssteg**
fångade alla fem felen, genom att läsa R4-specens definition mot kolumnens faktiska innebörd.

**Underfrågan:** AI:n fångade felen **helt själv** — inte som kandidater en människa sedan bekräftade.
Felen låg på **patientnivå (radnivå, fas 4)**. Människan i loopen kvarstår som den som slutligt
**godkänner** mappningen, men var inte den som **fångade** felen.

**Den mänskliga granskningen är obligatorisk** och ska alltid ske. I kataraktpiloten innebar den dock
**ingen ändring** — människan accepterade AI:ns mappningsförslag **till fullo**, just därför att
AI-verifieringssteget redan hade fångat och rättat de fem felen.

### Vad som uppdaterades till följd
- `docs/ppt-1-poc-fhir-mappning.md` slide 7 (och slide 9): granskningssteget (AI) får sin roll; behåller
  att en *formell* validering ensam inte räcker; människan godkänner slutligt.
- `docs/kchd_mappning_kunskapskalla.md` §11 (flaggan ersatt med avgjort-not), §12 (patientnivå-gränsen
  nyanserad) och §13 ("den mänskliga bedömningen" nyanserad till AI-QA + mänskligt godkännande).
- `docs/kchd-vision-vs-build.md` §5 punkt 4 (lärloopen — korrigeringarna kom ur ett AI-verifieringssteg).
- Kunskapsutvecklings-sajtens FHIR-vyer (`web/index.html`): `MappningFhirForklarat` och `MappningKpi16`.

---

## Avgjorda frågor

- **ÖF-01 — Vem/vad upptäckte de fem semantiska felen?** ✅ Avgjord 2026-06-18. Svar: ett separat
  **AI-verifieringssteg** (inte en människa) fångade alla fem. Fullständig logg ovan.
