# Målbild vs. byggt verktyg — gap- och konvergensanalys

**Status:** v1.0 · 2026-06-16
**Roll:** Detta dokument binder ihop den strategiska kunskapskällan
([`kchd_mappning_kunskapskalla.md`](./kchd_mappning_kunskapskalla.md)) och dess plan
([`kchd_mappning_plan.md`](./kchd_mappning_plan.md)) med koden som faktiskt finns i det här
repot. Syftet är att slå ihop tänket: visa var det byggda verktyget redan realiserar målbilden,
var det skiljer sig, och vilka konkreta hävstänger som tar oss närmare en state-of-the-art-tjänst.

> Terminologin följer kunskapskällan: **den regiongemensamma utvecklingsmiljön** för helheten och
> **den centrala noden** för den centralt mottagande komponenten. "Hubb" undviks. Repots egen term
> "central/on-prem" läses som den centrala noden respektive regionens egen miljö.

---

## 1. Syfte och nivåskillnad

De två källdokumenten och repot beskriver samma domän på **olika abstraktionsnivåer**, och det är
nyckeln till att läsa resten:

- **Kunskapskällan + planen** beskriver *hela den regiongemensamma utvecklingsmiljön* — en federerad
  mappningsmotor i fyra pass, fyra kunskapslager, tre-lagers-lagring och den bevisade grunden från
  kataraktpiloten. Det är en organisationsövergripande målbild med juridik, förvaltning och
  nationell förankring.
- **Repot** (se [`README.md`](../README.md) och [`opus-input/`](../opus-input/)) bygger *verktyget i
  v1*: ett schema-till-schema-mappningsverktyg med schemaimport, katalogbläddring,
  fält-mappningsförslag, validering och artefaktexport. Uttalat utanför scope i v1
  ([`README.md`](../README.md), [`COPILOT_RED_LINES.md`](../COPILOT_RED_LINES.md)): exekvering av
  transformationsskript och inläsning av patientnivådata.

Repot är alltså i praktiken en **körbar realisering av en avgränsad del av målbilden — främst Spår C**
(bygg motorn stegvis): maskinläsbara mappningsartefakter, registret som tjänst och AI-lagret med
människan i loopen. Spår A (pilotens luckor), Spår B (organisatoriska förutsättningar) och Spår D
(förankring) ligger till största delen *utanför* repots kod.

---

## 2. Komponentmappning: repo ↔ målbild ↔ plan-spår

| Repo-komponent | Fil | Målbildens motsvarighet | Plan-spår |
|---|---|---|---|
| `CanonicalSchema` / `CanonicalField` | [`packages/core/models/canonical_schema.py`](../packages/core/models/canonical_schema.py) | Standardmodellen / den administrativa modellen som nav | B4 |
| Input-adaptrar (FHIR-profil, OMOP CDM, openEHR, JSON Schema, SQL DDL, CSV, Parquet) | [`packages/adapters/input/`](../packages/adapters/input/) | "Målscheman pluggas in utan att motorn ändras"; referenskällor/målscheman | C4, B3 |
| Adapterregister | [`packages/adapters/registry.py`](../packages/adapters/registry.py) | Standarder är öppna/konfigurerbara, inte hårdkodade (RL-03) | C4 |
| `SuggestionEngine` + strategier + semantisk provider | [`packages/suggestions/engine.py`](../packages/suggestions/engine.py), [`semantic/`](../packages/suggestions/semantic/) | AI-assistenten — "vad mappningen borde bli", människan i loopen | C3 |
| `CatalogService` | [`packages/catalog/catalog_service.py`](../packages/catalog/catalog_service.py) | Registret som sökbar tjänst; del av Datakatalogens roll | C2 |
| `TerminologyReference` | [`packages/core/models/canonical_schema.py`](../packages/core/models/canonical_schema.py) (rad ~124) | Terminologitjänsten (ConceptMaps/ValueSets) — idag bara en referens, inte en tjänst | B5 |
| `AuditEvent` / `AuditAction` | [`packages/core/models/audit_event.py`](../packages/core/models/audit_event.py) | Lärsubstrat för människan-i-loopen; spårbarhet/proveniens | C3 |
| `MappingArtifact` + serialisering | [`packages/core/serialization/artifact.py`](../packages/core/serialization/artifact.py) | "Maskinläsbara mappningsartefakter" | C1 |
| SQL-generator (`INSERT … SELECT`) | [`packages/script_gen/generators/sql_insert_select.py`](../packages/script_gen/generators/sql_insert_select.py) | Utgående transformationsformat (men *genererat, inte exekverat* — RL-01) | C1 |
| Validering | [`packages/validation/`](../packages/validation/) | Den semantiska/strukturella kontrollen från pilotens metod | C1 |
| Versionshantering (`mapping_version.py`) | [`packages/core/models/mapping_version.py`](../packages/core/models/mapping_version.py) | Organiks versions- och granskningsflöde | B1 |

---

## 3. Likheter — där det byggda redan bär målbildens tänk

1. **Standardmodell som nav.** `CanonicalSchema` spelar exakt den roll målbilden ger standardmodellen
   / den administrativa modellen: en neutral mittpunkt som källor mappas *till* och mål mappas *från*.
   Det är samma "nav-och-eker"-princip som passen vilar på.
2. **Pluggbara mål, oförändrad motor.** Adapterregistret realiserar målbildens kärnlöfte att "en ny
   mottagare läggs till genom att ett nytt målschema pluggas in, utan att motorn ändras". Att FHIR,
   OMOP och openEHR redan finns som adaptrar visar att samma mekanism bär flera av målbildens format.
3. **Människan i loopen.** `SuggestionEngine` ger rankade förslag och överlåter beslutet till
   informatikern — precis målbildens mönster där maskinen gör grovarbetet och människan kvalitetssäkrar.
4. **Determinism och granskbarhet.** De viktade strategierna producerar förklarbara poäng, och
   `AuditEvent` loggar varje beslut. Det svarar mot pilotens krav på en *dokumenterad, validerbar*
   beslutsgång snarare än en svart låda.
5. **Substratoberoende.** Repots åtskillnad mellan central och on-prem speglar målbildens
   substratoberoende: koden kan köras där datan finns, kontraktet (det kanoniska schemat + artefakten)
   är hävstången, inte plattformsvalet.
6. **Terminologi som signal, inte hårdkodning.** `TerminologyReference` håller kodverk öppet (RL-03)
   i stället för att baka in specifika system — samma princip som målbilden lägger i Terminologitjänsten.

---

## 4. Skillnader — där nivå och scope går isär

1. **Ett pass vs. fyra pass.** Repot kör en generisk källa→mål-mappning. Målbilden orkestrerar fyra
   namngivna pass (källa→openEHR/admin, standard→utgående, FHIR→openEHR/admin centralt, →OMOP). Repot
   har byggstenarna men ingen pass-orkestrering.
2. **Generisk fält-till-fält vs. FHIR-native conformance.** Repots `MappingArtifact` är ett eget
   JSON-format. Målbilden (Spår C1) vill uttrycka mappningen som **StructureDefinition** (struktur),
   **ConceptMap** (värdeöversättning) och **StructureMap** (omvandling), så att en standardvaliderare
   kan köra dem. Detta är det enskilt största gapet.
3. **En referens vs. en levande Terminologitjänst.** `TerminologyReference` är en passiv referens i
   schemat. Målbilden förutsätter aktiva anrop mot Terminologitjänsten ($translate, $validate-code)
   och regiongemensamt förvaltade ConceptMaps (Spår B5). Repot anropar ingen sådan tjänst idag.
4. **Schema-only vs. patientnivå.** Repot är medvetet schema/metadata-nivå (RL-02, ingen
   patientdata). Målbildens fullständiga flöde transformerar patientnivåresurser (Condition,
   Procedure). Piloten bevisade endast aggregerad nivå (MeasureReport) — så här är repot och den
   bevisade grunden faktiskt *samstämmiga*, medan målbilden sträcker sig längre.
5. **In-memory artefakt vs. tre-lagers-lagring.** Repot producerar och versionshanterar artefakter men
   har ingen openEHR-operativ / OMOP-analys-lagring. Tre-lagers-lagringen är en miljöegenskap utanför
   verktygets v1-scope.
6. **Genererad kod vs. federerad exekvering.** SQL-generatorn *producerar* skript men kör dem aldrig
   (RL-01). Målbildens federerade princip — koden körs i regionens miljö, resultatet sammanställs
   centralt — är inte implementerad i repot; det är en deploy-/runtime-egenskap.

---

## 5. Insikter och konvergens-hävstänger (prioriterat)

Det här är de konkreta stegen som flyttar verktyget mot målbilden, ordnade efter hävstång:

1. **Gör kanonisk modell + artefakt uttryckbar som FHIR conformance-resurser (Spår C1 — störst).**
   Lägg till en *output-serialisering* från `CanonicalSchema`/`MappingArtifact` till
   StructureDefinition + ConceptMap + StructureMap. Detta är additivt — det egna JSON-formatet kan
   finnas kvar — men det gör artefakterna körbara i en standardvaliderare och låser i målbildens
   maskinläsbarhet. Naturlig plats: en ny generator under
   [`packages/script_gen/generators/`](../packages/script_gen/generators/) bredvid SQL-generatorn, plus
   en serialiserare i [`packages/core/serialization/`](../packages/core/serialization/).

2. **Koppla katalogen till en riktig Terminologitjänst (Spår B5 + C2).** Låt `CatalogService` /
   `TerminologyReference` lösa upp koder via ett $translate/$validate-code-gränssnitt i stället för att
   bara hålla en statisk referens. Det realiserar målbildens "registret som tjänst där en URI slås upp
   en gång och ett byte når alla regioner" — fortsättningen på pilotens `ref_fhir_system`.

3. **Inför pass-orkestrering ovanpå enkel-pass-motorn (Spår C4).** Bygg ett tunt orkestreringslager
   som kedjar flera mappningar (källa→kanonisk→mål) till namngivna pass. Adaptrarna och motorn finns
   redan; det som saknas är sekvenseringen och konventionen för mellanliggande kanoniska modeller.

4. **Slut lärloopen mellan audit och förslag (Spår C3).** `AuditEvent` fångar redan godkännanden och
   korrigeringar. Mata tillbaka dem som signal till `SuggestionEngine` (t.ex. en strategi som väger upp
   tidigare godkända mappningar av likartade fält). Pilotens fem korrigeringar — som fångades av ett
   separat AI-verifieringssteg, inte av en mänsklig granskare — är de första träningsexemplen och
   själva belägget för målbildens "varje kvalitetssäkring förbättrar maskinen".

5. **Förtydliga Datakatalogens bredare roll vs. repots katalog.** Repots `CatalogService` täcker
   schema-/registeruppslag, men målbildens Datakatalog gör mer: lineage källa→OMOP, GSIM-export och
   HealthDCAT-AP-beskrivningar. Detta bör dokumenteras som en *medveten* avgränsning, inte ett glömt
   krav, och läggas på en framtida väg snarare än v1.

---

## 6. Plan-spår × repo-status

| Spår | Innehåll | Repo-status |
|---|---|---|
| **A** — Stäng pilotens luckor | KVÅ-OID, övriga URI:er, saknade filer | Utanför repots scope (datakällor/verifiering, inte kod). |
| **B** — Realisera förutsättningar | Organik maskinläsbart, härledningsformat, **B4: administrativa modellen**, B5: terminologi | Delvis: **B4** realiseras av `CanonicalSchema` (fält, datatyper, kardinalitet, constraints på ett ställe). B5 saknas (ingen tjänst-integration). B1–B3 är organisatoriska. |
| **C** — Bygg motorn stegvis | C1 artefakter, C2 register-tjänst, C3 AI-lager, C4 bredd | **Repots tyngdpunkt.** C1 finns som eget format (gap: FHIR-resurser). C2 finns som `CatalogService` (gap: terminologi-uppslag). C3 finns som `SuggestionEngine` (gap: lärloop). C4 delvis via adaptrar (gap: pass + patientnivå). |
| **D** — Förankring och beslut | Namn, juridik, NSG-förankring | Utanför repots scope. |

**Slutsats:** Repot är en trovärdig, körbar grund för Spår C och uppfyller redan B4. De största
konvergensstegen är att (a) uttrycka artefakterna som FHIR conformance-resurser och (b) göra
terminologin till en levande tjänst. Båda är additiva ovanpå den befintliga arkitekturen och bryter
inte mot v1:s röda linjer (ingen exekvering, ingen patientdata).

---

## 7. Terminologinot

| Repots term | Målbildens term |
|---|---|
| "central" / centrala noden | den centrala noden |
| "on-prem" / regionens miljö | regionens egen miljö (federerad körning) |
| "tool" / verktyget v1 | en realisering av Spår C i den regiongemensamma utvecklingsmiljön |
| "canonical schema" | standardmodellen / den administrativa modellen |
| "terminology reference" | Terminologitjänsten (när den blir en aktiv tjänst) |

Undvik "hubb" och "vårddatahubb" i formell text, i linje med kunskapskällans del 16.
