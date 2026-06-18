# Presentation 2: Så ser hela maskinen ut

*Talarmanus + slides. Skrivet för att läsas högt. En idé per slide.*

---

## Läs det här först (60 sekunder)

Tänk dig en patient, Astrid, som ska opereras för grå starr. Hennes uppgifter skrivs in i
journalen på sjukhuset. Idag måste en person sedan översätta de uppgifterna för hand, varje gång,
för varje mottagare som vill ha dem — det tar månader. Vår vision är en maskin som gör
översättningen, med en ordbok vid sin sida, medan en människa godkänner. Astrids data stannar
på sjukhuset; bara svaret skickas ut. Och samma maskin kan skicka till flera mottagare samtidigt:
Socialstyrelsen, kvalitetsregistren och europeisk forskning. Pocken bevisade att en bit av det
här fungerar. Nu bygger vi resten, steg för steg.

## Miniordlista (säg det så här)

- **Mappning** = översättning mellan två sätt att säga samma sak.
- **Motorn** = översättaren. En maskin som följer en ordbok.
- **Ordboken (Terminologitjänsten)** = en enda sanning för vad en kod heter.
- **Innehållsförteckningen (Datakatalogen)** = var saken ligger och vad den betyder.
- **Federerat** = data stannar hemma. Vi skickar receptet, inte råvarorna.
- **Människan i loopen** = maskinen föreslår, en expert godkänner.

---

## Slide 1 — Så ser hela maskinen ut

**På skärmen:** Titeln. En enkel skiss: sjukhus → maskin → flera mottagare.

**Du säger:**
"Förra presentationen handlade om vad vi redan bevisat. Den här handlar om vart vi är på väg —
hela maskinen, när den är färdig. Jag tar er igenom den med en patient som heter Astrid."

---

## Slide 2 — Så jobbigt är det idag

**På skärmen:** En person framför en hög med papper. Texten "månader".

**Exempel:** Idag skriver en informatiker en specifikation i Word. Sedan sitter en utvecklare och
knappar in koden för hand. Per register tar det månader.

**Du säger:**
"Idag gör vi det här mest för hand. En person beskriver vad mottagaren behöver i ett
Word-dokument. Sedan får en utvecklare skriva koden för hand utifrån dokumentet. Det tar månader,
för varje register, om och om igen. Det är det vi vill ändra på."

---

## Slide 3 — Idén: en maskin, en ordbok, data stannar hemma

**På skärmen:** Tre ikoner: en maskin, en ordbok, ett hus med lås.

**Du säger:**
"Tre enkla idéer. Ett: en maskin gör översättningen i stället för en människa. Två: maskinen har
en ordbok bredvid sig som vet vad varje kod heter. Tre: precis som i pocken stannar datan hemma
hos regionen — bara svaret skickas ut. Resten av presentationen visar hur de tre hänger ihop."

---

## Slide 4 — Astrid kommer in i maskinen

**På skärmen:** Tre olika system-loggor (Cosmic, Millennium, TakeCare) som möts i en gemensam form.

**Exempel:** Astrids diagnos kan stå på tre olika sätt i tre olika journalsystem — Cosmic,
Millennium, TakeCare. Maskinen lägger dem i en gemensam form så att de betyder samma sak.

**Du säger:**
"Astrids uppgifter kan se helt olika ut beroende på vilket journalsystem sjukhuset har. Cosmic,
Millennium och TakeCare säger samma sak på olika sätt. Det första maskinen gör är att lägga allt
i en gemensam form, så att 'grå starr' betyder grå starr oavsett varifrån det kom."

---

## Slide 5 — Ordboken reder ut koderna

**På skärmen:** Tre nästan identiska sifferrader, med en ringad som "rätt".

**Exempel:** En verklig knäckfråga: koden för operationstypen (KVÅ) hade *tre* nästan identiska
officiella adresser i omlopp. En människa fick reda ut vilken som gäller. Ordboken ska lösa det
en gång — för alla.

**Du säger:**
"Här är ett exempel ur verkligheten. Det fanns tre nästan identiska officiella nummer för samma
sorts kod. Tre! Någon fick sitta och lista ut vilket som var det rätta. Med en gemensam ordbok
löser vi det en gång, och alla regioner får samma svar. Ingen behöver gissa igen."

---

## Slide 6 — En översättning, många mottagare

**På skärmen:** En gaffel: från maskinen går tre pilar ut till tre olika mottagare. En
"resekontakt"-symbol.

**Exempel:** Från Astrids standardiserade uppgifter går det ut till Socialstyrelsen (PAR),
kvalitetsregistret (t.ex. RiksSvikt) och FHIR — samtidigt. Ny mottagare = byt bara "kontakten".

**Du säger:**
"När Astrids uppgifter väl är i den gemensamma formen kan maskinen skicka dem till många mottagare
samtidigt — Socialstyrelsen, kvalitetsregistren, forskningen. Tänk på det som eluttag i olika
länder: strömmen är densamma, du byter bara kontakten. En ny mottagare betyder bara en ny kontakt,
inte en ny maskin."

---

## Slide 7 — Maskinen föreslår, människan godkänner

**På skärmen:** En lärling och en mästare. En pil som går runt i en loop.

**Exempel:** Informatikern öppnar ett nytt fält. Assistenten föreslår en översättning. Människan
godkänner eller rättar. Nästa liknande register ärver det godkända beslutet. Pocken-rättningarna
är de första lärdomarna.

**Du säger:**
"Vi låter inte maskinen bestämma själv. Tänk lärling och mästare. Maskinen föreslår en
översättning, experten godkänner eller rättar. Och varje rättning gör maskinen lite bättre, så
att nästa register går snabbare. De fem felen vi hittade i pocken är de första lärdomarna."

---

## Slide 8 — Forskaren som vill räkna

**På skärmen:** En forskare framför en prydlig hylla där varje sak har sin plats.

**Exempel:** En forskare vill räkna starroperationer per region. I analyslagret (OMOP) finns varje
variabel på exakt ett ställe — en välstädad hylla — så frågan går snabbt och rätt.

**Du säger:**
"Längst ut sitter forskaren. Hen vill kanske räkna hur många starroperationer som gjorts per
region. För det har vi ett särskilt analyslager där varje uppgift finns på exakt ett ställe — som
en välstädad hylla. Då blir det enkelt att ställa frågor och få pålitliga svar."

---

## Slide 9 — Det spelar ingen roll vilken plattform regionen har

**På skärmen:** Två olika maskiner under samma "kontrakt"-paraply.

**Exempel:** I pocken körde Västra Götaland på en viss teknik (Denodo och SSIS). En annan region
kan köra något helt annat. Båda duger — så länge de uppfyller det gemensamma kontraktet.

**Du säger:**
"En sista viktig poäng. Vi tvingar ingen region att byta system. I pocken körde Västra Götaland på
sin teknik; en annan region kan köra något helt annat. Det vi enas om är ett kontrakt för vad som
ska levereras — inte vilken leverantör man måste välja. Det är där styrkan ligger."

---

## Slide 10 — Var vi står, och vägen dit

**På skärmen:** En enkel tidslinje: "Bevisat" → "Bygger nu" → "Målet".

**Exempel:** Pocken bevisade metoden. Ett första verktyg finns redan — det importerar scheman,
föreslår översättningar och kontrollerar dem. Härifrån bygger vi motorn och ordboken steg för steg.

**Du säger:**
"Så var står vi? Pocken bevisade att metoden håller. Vi har redan ett första verktyg som kan läsa
in scheman, föreslå översättningar och kontrollera dem. Härifrån bygger vi vidare, steg för steg,
tills hela maskinen står där. Astrids resa, från journalen ut till alla som behöver hennes
uppgifter — utan att hennes data någonsin lämnar sjukhuset i onödan."
