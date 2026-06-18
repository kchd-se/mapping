# Mappning i den regiongemensamma utvecklingsmiljön — kunskapskälla

**Status:** Konsoliderad v1.0 · 2026-06-16
**Roll:** Detta är den samlade kunskapskällan för mappning och tänket kring det. Den integrerar fyra tidigare artefakter — målbilden för den federerade mappningsmodellen, det konsoliderade metoddokumentet från kataraktpiloten, underlaget för en mappningsmotor, och planen — och ersätter dem som självständiga sanningskällor. Målbildens två utarbetade exempel följer med som bilagor (se del V).
**Plan:** Färdvägen ligger i ett eget dokument, kchd_mappning_plan.md, så att den kan bockas av löpande. Del IV här ger översikten.

> **Terminologi.** Dokumentet använder "den regiongemensamma utvecklingsmiljön" för helheten och "den centrala noden" för den komponent som tar emot, lagrar och vidaretransformerar data centralt. Namnet på miljön är inte beslutat. Begreppen är funktionella och kan bytas när beslut finns. Orden "hubb" och "vårddatahubb" undviks i formell text.

---

## Del I — Målbilden: vart vi ska

Denna del sammanfattar den auktoritativa beskrivningen av mappningsmodellen i sin målbild. Den fullständiga framställningen med kodexempel finns i bilaga A och B.

### 1. Modellen i korthet

Mappningsmodellen beskriver hur data tar sig från regionernas källsystem, genom standardisering, till de format olika mottagare behöver: kvalitetsregister, Socialstyrelsen, forskning och europeisk sekundäranvändning. Modellen vilar på en enda mappningsmotor som körs i flera pass, och på en uppsättning kunskapskällor som motorn konsulterar under varje transformation. Regionerna behåller kontrollen över sin data och kör koden i sin egen miljö. Den centrala noden tar emot standardiserade resultat och sammanställer dem. Det är samma federerade princip som prövades i kataraktpiloten.

### 2. Referenskällor och målscheman

Modellen vilar på en åtskillnad som återkommer genom hela flödet. Referenskällor är de kunskapsbaser motorn konsulterar under en transformation, och de svarar på vad något betyder och var det hamnar. Hit hör Terminologitjänsten, openEHR-arketyperna och Datakatalogen. Målscheman är de mallar som bestämmer hur resultatet ska se ut, och de svarar på hur en viss mottagare vill ha sin data. Hit hör PAR-SV och PAR-OV, kvalitetsregistrens scheman, FHIR R4-profiler och OMOP CDM. En ny mottagare läggs till genom att ett nytt målschema pluggas in, utan att motorn eller referenskällorna ändras. Organik hör hemma på målschemanivån, eftersom det är verktyget där kvalitetsregistrens scheman definieras.

### 3. Det fullständiga flödet

Flödet löper i sex steg från regional källa till europeisk sekundäranvändning. Fyra av stegen är pass genom mappningsmotorn.

| Steg | Var | Vad som händer |
|------|-----|----------------|
| 1 | Regionalt | Källdata hämtas från kliniska och administrativa system |
| 2 | Regionalt | Pass 1: Källa → openEHR + administrativ modell |
| 3 | Regionalt | Pass 2: Standardmodell → utgående format (PAR-SV, JoL, FHIR-bundles) |
| 4 | Centralt | Noden tar emot FHIR-bundles · Pass 3: FHIR → openEHR + admin |
| 5 | Centralt | Pass 4: openEHR + admin → OMOP CDM |
| 6 | Centralt | Data tillgängliggörs för sekundäranvändning och exponeras i kataloger |

Källdatan kommer från kliniska system (Cosmic, Millennium, TakeCare) med diagnoser, åtgärder, labb och läkemedel, och från administrativa system med väntetider, remisser, bemanning, beläggning, ekonomi och logistik. I steg 6 exponeras data genom Datakatalogen, exporteras i GSIM-format till Vetenskapsrådets RUT, och beskrivs i HealthDCAT-AP för HDAB och HealthData@EU.

### 4. Mappningsmotorn pass för pass

Motorn är en kodbas med utbytbara moduler. Varje pass aktiverar en parser-modul som läser in, ett antal anrop mot kunskapskällor, och en serializer-modul som producerar utdata. Pass 1 omvandlar rådata från journal- och administrativa system till openEHR-kompositioner och en administrativ modell. Pass 2 omvandlar standardmodellen till PAR-SV, JoL-meddelanden och FHIR-bundles, och bevarar ursprungskoderna så att ICD-10 och KVÅ kan levereras till Socialstyrelsen. Pass 3 är den omvända transformationen centralt, från inkommande FHIR till openEHR och administrativ modell. Pass 4 omvandlar standardmodellen centralt till OMOP CDM. Den centrala noden fungerar även som proxy och kan vidarebefordra transformerad data till Socialstyrelsen och andra nationella mottagare å regionernas vägnar.

### 5. De fyra kunskapslagren

Motorn äger exekveringen, men kunskapen om vad som ska transformeras ligger i fyra lager som var och en svarar på en egen fråga. Organik svarar på vad mottagaren vill ha, alltså registerfrågor, grunddata, härledningsregler och informationsspecifikationer. Terminologitjänsten svarar på vad något heter i standardformat, i form av ConceptMaps och ValueSets, och hanteras av Inera. Datakatalogen svarar på var data finns i källsystemet, med tabellnamn, kolumnnamn, datatyper, lokala kodnamn och kvalitetsmetrik per region. AI-assistenten svarar på vad mappningen borde bli och förbättras över tid genom mänsklig validering. Under en transformation frågar motorn alla fyra.

### 6. Organik som ägare av specifikationen

Organik löser redan det svåraste och dyraste i kedjan, det intellektuella arbetet att förstå vad en mottagare behöver och hur det motsvaras av det som finns dokumenterat i journalen. Det arbetet kräver informatiker som förstår både den kliniska verkligheten och den tekniska strukturen. Verktyget har byggstenarna: grunddata med koder från ICD-10, SNOMED, NPU och ATC, härledningsregler, en förstudiedel, en anslutningsbedömning per region, och versionshantering med granskningsflöde. Det Organik gör idag är att producera en informationsspecifikation som ett Word-dokument, varefter en utvecklare manuellt skriver kod som implementerar det. Steget från specifikation till körbar kod är manuellt, och det är det steget mappningsmotorn ska fylla.

### 7. Lärande mappning med AI

Manuell mappning tar månader per register. En AI-assistent som föreslår mappningar och lär sig av varje korrigering ändrar skalan på arbetet. En informatiker öppnar ett nytt grunddata, assistenten läser namn, beskrivning, kodverk och datatyp och föreslår en mappning, och visar förslaget direkt när den är säker eller en rankad lista när den är osäker. Varje val sparas, så att nästa likartade grunddata i ett annat register eller en annan region har det godkända beslutet som referens. Mönstret är människan i loopen: maskinen gör grovarbetet, människan kvalitetssäkrar, och varje kvalitetssäkring förbättrar maskinen. Terminologitjänsten ger dessutom assistenten och informatikern tillgång till de regionala koder som Organik saknar idag.

### 8. Lagringsarkitektur i tre lager

Lagringen har tre lager med olika uppgifter. Det operativa openEHR-lagret bär den longitudinella journalen, och den verkliga interoperabilitetsmekanismen mellan källsystem är harmoniserade arketyper som AQL förenar vid frågetillfället. AQL-åtkomst räcker för måttliga analysbehov, där ett dataelement nås via sin arketypväg oberoende av komposition och persistensschema. Analyslagret i OMOP-form bär populationsanalys och forskning, och där hör principen att varje variabel förekommer en gång hemma. En viktig princip för det operativa lagret är att skilja på rått och förädlat: varje komposition är bunden till sin proveniens, och inkommande data kan landa i en rålogg och först därefter normaliseras till det styrda formatet.

### 9. Datakatalogens roll

Datakatalogen är en sökbar uppslagsbok som beskriver vilken data som finns, vad den betyder, hur den ser ut tekniskt och var den lagras, och den tjänar både motorn maskinellt och dataanvändare mänskligt. Den beskriver administrativa variabler som openEHR saknar metadata för, hanterar synonymer, anger var data finns, förklarar för forskare vad som finns tillgängligt, exponerar variabelbeskrivningar i GSIM och dataset-beskrivningar i HealthDCAT-AP, och spårar lineage från källsystem till OMOP. Den refererar till Terminologitjänstens ConceptMaps för koder och är förvaltningsverktyget för den administrativa modellen.

### 10. Substratoberoende och hävstången i kontraktet

Modellen är substratoberoende genom design. Koden körs i regionens egen miljö och resultatet skickas till den centrala noden. Det spelar ingen roll om en region kör Denodo och SSIS, som i kataraktpiloten, eller en kommersiell CDR, så länge miljön uppfyller det kontrakt som specificerar vad en region måste leverera. Hävstången ligger i kontraktet, inte i leverantörsvalet. Så länge specifikationen ägs gemensamt genom KCHD och NSG är en region som uppfyller kontraktet en fullvärdig deltagare oavsett underliggande plattform.

---

## Del II — Den bevisade grunden: vad kataraktpiloten visade

### 11. Vad piloten gjorde

Kataraktpiloten med Västra Götalandsregionen byggde en mappning från regionens väntetidsmodell till HL7 FHIR R4 på aggregerad nivå, och körde den federerat. Metoden är dokumenterad i sju operativa steg som ligger nedskrivna som en återanvändbar prompt: inventera nyckeltalen, slå mot R4-specen, slå mot svenska profiler och OID-register, fatta designbesluten, skapa VQL-vyn, testa mot testdata, och logga osäkerheterna. Inuti stegen sitter beslutsgången per variabel, där varje koppling kontrolleras genom att specens definition av ett element jämförs mot kolumnens innebörd. Den fullständiga metoden finns i det konsoliderade metoddokumentet.

Varje koppling vilar på en av fyra evidensgrunder: bekräftad mot R4-specen, bekräftad svensk system-URI med källa, provisorisk fallback-URI samlad i ref_fhir_system, eller eget designbeslut med motivering. Den semantiska kontrollen är prövad: fem mappningar var giltig FHIR och ändå fel element och korrigerades, vilket visar att metoden prövar betydelse och inte bara form. En körbar Python-referens producerade en FHIR Bundle som validerades mot R4.

> 🔎 **Under verifiering (ÖF-01):** Texten ovan tillskriver upptäckten av de fem felen den mänskliga granskningen. Det utreds om det i praktiken var en AI som fångade dem i ett kvalitetssäkringssteg. Påståendet står kvar oförändrat tills frågan är avgjord — se [`oppna-fragor.md`](./oppna-fragor.md).

### 12. Hur piloten placerar sig i målbilden

Detta avsnitt skiljer design från bevis, och det är avgörande att det står rätt.

Piloten omvandlade redan beräknade nyckeltal direkt till FHIR MeasureReport. Den gick inte genom openEHR och arbetade på administrativ statistik på aggregerad nivå. I målbildens termer är piloten ett instans av den administrativa vägen till ett målschema, alltså en del av det pass 2 gör när det producerar ett utgående format. Den administrativa vägen går enligt målbilden inte genom openEHR-arketyperna utan genom den administrativa modellen och Datakatalogen, vilket är förenligt med vad piloten faktiskt gjorde.

Piloten bevisade tre saker som målbilden bygger på. Den bevisade att en mappning till ett målschema kan byggas, dokumenteras och verifieras med en metod som tål granskning. Den bevisade att samma kodpaket kan köras i regionens miljö och att resultatet kan sammanställas centralt. Den bevisade att ett målschema kan pluggas in utan att metoden byts ut.

Piloten bevisade inte openEHR-kärnan, återanvändningen över fyra pass, eller transformationen på patientnivå. Den prövade en aggregerad rapporteringsresurs, MeasureReport, och inte de patientnivåresurser som Condition och Procedure som målbildens fullständiga flöde förutsätter. Den bevisade alltså metodiken, verifierbarheten och federationen, men inte den gemensamma modellen eller passens fulla bredd. Att skriva ut den gränsen är det som gör grunden trovärdig.

### 13. Evidensliggaren och den ärliga gränsen

Nio konkreta förhållanden gör piloten till en försvarbar grund. Metoden är dokumenterad och stegvis. Varje koppling har en uttalad evidensgrund. Källsökningen är fullständig och daterad. Den semantiska kontrollen är prövad genom fem korrigeringar. Det finns en körbar referens med validerad utdata. Beräkningen under mappningen är byggd i fyra implementationer med samma resultat mot syntetisk data. De provisoriska URI:erna byts på ett ställe. Registret är byggt för att skala. Arbetet dokumenterar var Sverige har en standard och var en saknas, vilket är relevant för EHDS.

Den ärliga gränsen kvarstår: ingen motor bevisar att en semantisk mappning är korrekt. Korrektheten etableras genom en dokumenterad definitionsmatchning, en auktoritativ källa där en sådan finns, och en granskning av någon som kan både källmodellen och målformatet. En motor sänker arbetsinsatsen, höjer konsekvensen och gör besluten validerbara, men den ersätter inte den mänskliga bedömningen.

### 14. Kontinuiteten från pilot till målbild

Piloten är en tidig, för hand körd version av målbildens motor, och flera av dess delar har en naturlig fortsättning. De provisoriska URI:erna i ref_fhir_system motsvarar det målbilden lägger i Terminologitjänsten som ConceptMaps och CodeSystems. De fyra evidensgrunderna är samma slags beslut som Terminologitjänsten och Datakatalogen ska hålla i målbilden. Den manuella beslutsgången per variabel är det AI-lagret med människan i loopen ska skala upp, och pilotens fem korrigeringar är träningsexempel för ett sådant lager. KVÅ-OID-frågan, där tre kandidatvärden står mot varandra, är just det Terminologitjänsten ska lösa en gång för alla genom att hålla rätt CodeSystem med rätt OID.

---

## Del III — Konsistens och terminologi

### 15. Två olika "fyra" som inte får blandas ihop

Dokumentationen innehåller två fyrtal på olika nivåer. De fyra evidensgrunderna är ett metoddetalj från piloten och beskriver vad en enskild mappning vilar på: R4-bekräftelse, svensk URI, provisorisk fallback, eller designbeslut. De fyra kunskapslagren är målbildens arkitektur och beskriver var kunskapen ligger: Organik, Terminologitjänsten, Datakatalogen och AI-assistenten. De svarar på olika frågor och hör till olika nivåer. När båda nämns i samma text ska det framgå vilket fyrtal som avses.

### 16. Terminologi och namn

Helheten benämns den regiongemensamma utvecklingsmiljön och den centrala komponenten den centrala noden. Namnet på miljön är inte beslutat. I formella texter och i POC-rapporten undviks "hubb" och "vårddatahubb". Målbildens bilagor använder "vårddatahubben" löst i de utarbetade exemplen, och de orden ska läsas som den centrala noden tills namnet är beslutat.

### 17. Öppna designbeslut

Fyra designbeslut behöver vara på plats innan motorn implementeras, och de följer av målbildens del 11 och bilaga B. Organik behöver ett maskinläsbart exportformat utöver Word, exempelvis ett API i JSON eller som FHIR Implementation Guide. Härledningsreglerna behöver ett strukturerat regelformat i stället för fritext, exempelvis CQL eller FHIRPath. Organiks scope behöver breddas från kvalitetsregister till att även täcka PAR-SV, väntetider och OMOP, eller också byggs en parallell instans för andra mottagare. Den administrativa modellen behöver definieras på ett ställe, eftersom Terminologitjänsten kan hålla mappningsbeslut som ConceptMaps men inte datatyp, kardinalitet eller valideringsregler, och där fyller Datakatalogen rollen.

---

## Del IV — Planen i översikt

Färdvägen ligger i kchd_mappning_plan.md och bockas av där. Den löper i fyra spår. Spår A stänger den bevisade grundens luckor, främst KVÅ-OID:en och de saknade filerna. Spår B realiserar målbildens förutsättningar, främst Organiks maskinläsbara export, det strukturerade härledningsformatet och definitionen av den administrativa modellen. Spår C bygger motorn stegvis, från maskinläsbara mappningsartefakter och ett register som blir en sökbar tjänst, till AI-lagret med människan i loopen och bredare täckning över fler pass och format. Spår D hanterar förankring och beslut, främst namn, juridisk form och förankring i NSG hälsodata.

---

## Del V — Bilagor

Målbildens två utarbetade exempel hör till denna kunskapskälla och utgör dess bilagor. Bilaga A följer en patient från Cosmic genom mappningsmotorn och Terminologitjänsten till openEHR, och vidare i gaffeln till Socialstyrelsens PAR-SV, kvalitetsregistret RiksSvikt via NKRR, och FHIR R4. Bilaga B beskriver vad Terminologitjänsten kan och inte kan lagra, och hur ansvaret därför fördelas mellan Terminologitjänsten, Datakatalogen och datamodellerna. De ligger i målbildsdokumentet och är oförändrade.

### Källor till den bevisade grunden

Den bevisade grunden vilar på fyra filer från kataraktpiloten — fhir_mappning_analys.md, fhir_mappningsregister.md, fhir_serializer_spec.md och fhir_mappning_metod.md — samt det konsoliderade metoddokumentet som sammanställer dem. Tre filer som metoddokumentet hänvisar till är ännu inte verifierade mot original: prompt_fhir_mappning.md, fhir_serializer.py och fhir_paket.vql.
