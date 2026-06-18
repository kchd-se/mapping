# Plan — mappning i den regiongemensamma utvecklingsmiljön

Löpande checklista. Ersätter plan_mappningsmotor.md. Hör ihop med kunskapskällan kchd_mappning_kunskapskalla.md.

Status: ✅ klar · ◻ öppen · ⏳ beror på extern leverans

---

## Spår A — Stäng den bevisade grundens luckor

Detta är pilotens egna gap, kända och avgränsade. De ändrar varken metoden eller målbilden.

- ◻ **A1 — KVÅ-OID.** Tre kandidatvärden i omlopp: underlagets 1.2.752.116.1.3.2.1.4 och 1.2.752.116.1.3.2.3.6, samt 1.2.752.116.1.3.2.3.4 ur Socialstyrelsens egen FHIR-resurs (se.socialstyrelsen.nim). Stängs genom att jämföra de tre mot raderna för KVÅ, KKÅ och KMÅ i Socialstyrelsens OID-serie 2025-10-17. ⏳ Kräver att OID-serie-filen laddas upp eller att raderna klistras in. Hålls provisorisk i ref_fhir_system tills dess.
- ◻ **A2 — Övriga URI:er.** Stäm av HSA-id, SOSNYK och HSA verksamhetskod mot samma OID-serie-fil. Lägre prioritet, redan källbelagda.
- ◻ **A3 — Saknade filer.** ⏳ Hämta prompt_fhir_mappning.md, fhir_serializer.py och fhir_paket.vql från repo, så att metoddokumentets sista påståenden kan verifieras. Repona är privata; filerna behöver delas.
- ✅ **A4 — Dokumenterade avvikelser.** D-kodkollision, radantal, bundle-storlek, odefinierad U6 och D9–D16-glappet är hanterade i det konsoliderade metoddokumentet.

## Spår B — Realisera målbildens förutsättningar

Detta är vad som krävs för att kedjan från specifikation till körbar kod ska slutas. Källa: målbildens del 11 och bilaga B.

- ◻ **B1 — Organik maskinläsbart.** Definiera ett exportformat utöver Word, exempelvis ett API som exponerar grunddata, mappningar och härledningsregler i JSON eller som FHIR Implementation Guide.
- ◻ **B2 — Strukturerat härledningsformat.** Välj ett regelformat i stället för fritext för härledningsreglerna, exempelvis CQL, FHIRPath eller ett eget JSON-schema, så att motorn kan läsa in och köra dem.
- ◻ **B3 — Organiks scope.** Bredda Organik från kvalitetsregister till att även täcka PAR-SV, väntetider och OMOP, eller bygg en parallell instans av samma koncept för andra mottagare.
- ◻ **B4 — Definiera den administrativa modellen.** Lägg modellens fält, datatyper och regler på ett ställe (JSON Schema, FHIR StructureDefinition eller openEHR-template), eftersom Terminologitjänsten kan hålla mappningsbeslut men inte datatyp, kardinalitet eller valideringsregler.
- ◻ **B5 — Terminologitjänst-integration.** Fastställ hur motorn anropar Terminologitjänsten för $translate och $validate-code, och hur regiongemensamma ConceptMaps laddas upp och förvaltas.

## Spår C — Bygg motorn stegvis

Detta är vägen från pilotens för-hand-körda metod till en körbar motor. Källa: motorunderlaget, nu del II i kunskapskällan.

- ◻ **C1 — Maskinläsbara mappningsartefakter.** Uttryck mappningen som StructureDefinition för struktur, ConceptMap för värdeöversättning och StructureMap för omvandling, så att en validerare kan köra dem.
- ◻ **C2 — Registret som tjänst.** Flytta mappningsregistret från markdown till en sökbar tjänst där en URI slås upp en gång och ett byte av en provisorisk URI når alla regioner. Detta är fortsättningen på ref_fhir_system in i Terminologitjänsten.
- ◻ **C3 — AI-lager med människan i loopen.** Bygg det lager som föreslår mappningar och lär av varje validering. Pilotens fem korrigeringar är de första träningsexemplen.
- ◻ **C4 — Bredare täckning.** Väx från aggregerad FHIR till patientnivåresurser och till fler målscheman och pass, med samma metod.

## Spår D — Förankring och beslut

- ◻ **D1 — Namn och terminologi.** Besluta namnet på utvecklingsmiljön och den centrala noden, så att "hubb" kan utgå ur all text.
- ◻ **D2 — Juridisk form.** Avgör om data som landar centralt faller under regional rådighet eller registerägarens, och förankra mappningens juridiska grund.
- ◻ **D3 — Förankring i NSG hälsodata.** Förankra kunskapskällan och planen i styrgruppen och arkitekturråden.

---

## Närmast att göra

1. A1 och A2 — ladda upp OID-serie-filen, så stängs KVÅ-OID:en och övriga URI:er.
2. A3 — dela de tre saknade filerna, så verifieras metoddokumentet helt.
3. B4 — börja definiera den administrativa modellen, eftersom flera senare steg beror på den.
