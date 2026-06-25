// ── Mappning till FHIR #7: Målbilden — en motor, fyra pass, fyra kunskapslager ──
// Beskriver VISIONEN (den regiongemensamma utvecklingsmiljön), inte vad som är byggt i v1.
(function () {
  const { useState } = React;

  const C = {
    bg: "#FAFAF7", ink: "#1A1A17", teal: "#377D7A", tealDark: "#2A5F5C",
    tealTint: "#EAF2F1", tealLine: "#CADFDD", slate: "#44546A", slateTint: "#EDEFF3",
    ochre: "#B5772E", ochreTint: "#F6ECDD", ochreLine: "#E4CDA6", paper: "#FFFFFF", hair: "#E8E6DF",
    green: "#2F8F5B",
  };
  const display = "'Libre Franklin', sans-serif";
  const body = "'IBM Plex Sans', sans-serif";
  const mono = "'IBM Plex Mono', monospace";

  // Pipelinens steg = det fullständiga sex-stegsflödet. Fyra steg är pass genom motorn.
  const STEG = [
    { id: "kalla",  namn: "Källsystem",      under: "regionalt — Cosmic m.fl." },
    { id: "pass1",  namn: "Pass 1",          under: "källa → openEHR + admin" },
    { id: "pass2",  namn: "Pass 2",          under: "standard → utgående" },
    { id: "nod",    namn: "Centrala noden",  under: "Pass 3: FHIR → openEHR" },
    { id: "pass4",  namn: "Pass 4",          under: "→ OMOP CDM" },
    { id: "sekundar", namn: "Sekundärbruk",  under: "kataloger, forskning, EU" },
  ];

  // Källorna = de fyra kunskapslagren. Motorn frågar alla fyra under en transformation.
  const KALLOR = [
    { id: "organik", namn: "Organik", under: "vad mottagaren vill ha",
      forklaring: "Ägaren av specifikationen: registerfrågor, grunddata med koder (ICD-10, SNOMED, NPU, ATC), härledningsregler och informationsspecifikationer. Organik gör redan det svåraste — att förstå vad en mottagare behöver och hur det motsvaras i journalen. Idag produceras det som ett Word-dokument; steget därifrån till körbar kod är det motorn ska fylla.",
      urls: [], note: "Kunskapslager (målschemanivå). Behöver maskinläsbart format — Spår B1." },
    { id: "terminologi", namn: "Terminologitjänsten", under: "vad något heter i standard",
      forklaring: "Svarar på vad ett värde heter i standardformat: ConceptMaps (översättningar) och ValueSets (tillåtna värden), förvaltade av Inera. Motorn anropar $translate och $validate-code, och regiongemensamma ConceptMaps laddas upp en gång och når alla regioner. Ger även tillgång till de regionala koder Organik saknar idag.",
      urls: [ { label: "hl7.org/fhir/R4 (ConceptMap/ValueSet)", href: "https://hl7.org/fhir/R4/" } ], note: "Referenskälla. Integration är Spår B5." },
    { id: "datakatalog", namn: "Datakatalogen", under: "var data finns",
      forklaring: "En sökbar uppslagsbok: tabellnamn, kolumnnamn, datatyper, lokala kodnamn och kvalitetsmetrik per region. Den beskriver administrativa variabler som openEHR saknar metadata för, hanterar synonymer, spårar lineage källa → OMOP, och exponerar variabelbeskrivningar i GSIM och dataset i HealthDCAT-AP. Tjänar både motorn maskinellt och dataanvändaren mänskligt.",
      urls: [], note: "Referenskälla + förvaltningsverktyg för den administrativa modellen." },
    { id: "ai", namn: "AI-assistenten", under: "vad mappningen borde bli",
      forklaring: "Föreslår mappningar och lär av varje mänsklig validering. Informatikern öppnar ett grunddata, assistenten läser namn, beskrivning, kodverk och datatyp och föreslår — direkt när den är säker, en rankad lista när den är osäker. Varje godkänt beslut sparas som referens för nästa likartade fält. Människan i loopen: maskinen gör grovarbetet, människan kvalitetssäkrar, varje kvalitetssäkring förbättrar maskinen.",
      urls: [], note: "Kunskapslager. Pilotens fem korrigeringar är de första träningsexemplen." },
  ];

  // konsult = motorn frågar lagret (teal) · loop = beslut återförs/lär (ochre)
  const VARIABLER = [
    {
      id: "ny_mottagare", kod: "Ny mottagare pluggas in", scenario: "Ett nytt målschema läggs till — motorn och referenskällorna är oförändrade",
      steg: {
        kalla:    { state: "pass", txt: "Källsystemen är desamma." },
        pass1:    { state: "pass", txt: "Pass 1 omvandlar källan till openEHR + administrativ modell precis som förut — oberoende av vem mottagaren är." },
        pass2:    { state: "fix",  txt: "Här pluggas det NYA målschemat in. Pass 2 producerar nu även det utgående formatet (t.ex. ett nytt kvalitetsregisters schema). Motorn ändras inte — bara mallen för utdata." },
        nod:      { state: "pass", txt: "Inget nytt centralt; den nya mottagaren kan ta emot regionalt eller via noden som proxy." },
        pass4:    { state: "pass", txt: "OMOP-passet påverkas inte." },
        sekundar: { state: "pass", txt: "Den nya mottagaren syns i Datakatalogen som ännu en beskriven datamängd." },
      },
      lankar: [
        { from: "pass2", to: "organik", kind: "konsult" },
        { from: "pass2", to: "terminologi", kind: "konsult" },
      ],
      resultat: { falt: "Pluggbart målschema", varde: "samma motor, ny mottagare", extra: "Kärnlöftet: en ny mottagare läggs till genom att ett nytt målschema pluggas in, utan att motorn eller referenskällorna ändras." },
    },
    {
      id: "fyra_pass", kod: "En variabel hela vägen", scenario: "Från regional källa till OMOP genom alla fyra pass — alla kunskapslager frågas",
      steg: {
        kalla:    { state: "pass", txt: "Variabeln hämtas ur källsystemet regionalt." },
        pass1:    { state: "pass", txt: "Pass 1: rådata → openEHR-komposition + administrativ modell. Motorn frågar alla fyra kunskapslagren om vad, var, hur och vad-det-borde-bli." },
        pass2:    { state: "pass", txt: "Pass 2: standardmodellen → utgående format (PAR-SV, JoL, FHIR-bundles). Ursprungskoderna bevaras så ICD-10/KVÅ kan levereras till Socialstyrelsen." },
        nod:      { state: "pass", txt: "Pass 3 centralt: inkommande FHIR → openEHR + admin. Noden tar emot bundles och kan agera proxy mot nationella mottagare." },
        pass4:    { state: "pass", txt: "Pass 4 centralt: standardmodellen → OMOP CDM. Här gäller principen att varje variabel förekommer en gång." },
        sekundar: { state: "pass", txt: "Variabeln blir tillgänglig för populationsanalys och forskning, exponerad i Datakatalogen." },
      },
      lankar: [
        { from: "pass1", to: "organik", kind: "konsult" },
        { from: "pass1", to: "terminologi", kind: "konsult" },
        { from: "pass1", to: "datakatalog", kind: "konsult" },
        { from: "pass1", to: "ai", kind: "konsult" },
      ],
      resultat: { falt: "Källa → openEHR/admin → FHIR → OMOP", varde: "fyra pass, en motor", extra: "Motorn äger exekveringen; kunskapen ligger i de fyra lagren. Under varje transformation frågar motorn alla fyra." },
    },
    {
      id: "federerad", kod: "Federerad körning", scenario: "Regionen kör koden i sin egen miljö; noden sammanställer — substratoberoende",
      steg: {
        kalla:    { state: "pass", txt: "Datan stannar i regionen. Det spelar ingen roll om regionen kör Denodo/SSIS (som i piloten) eller en kommersiell CDR." },
        pass1:    { state: "pass", txt: "Pass 1 körs i regionens egen miljö. Koden flyttas dit datan finns." },
        pass2:    { state: "pass", txt: "Pass 2 körs också regionalt och producerar standardiserade FHIR-bundles." },
        nod:      { state: "fix",  txt: "Bara det standardiserade RESULTATET skickas till den centrala noden — aldrig rådata. Noden sammanställer och kan agera proxy vidare." },
        pass4:    { state: "pass", txt: "Pass 4 körs centralt på det noden tagit emot." },
        sekundar: { state: "pass", txt: "Sammanställd data tillgängliggörs centralt. Hävstången ligger i kontraktet, inte i leverantörsvalet." },
      },
      lankar: [
        { from: "pass1", to: "datakatalog", kind: "konsult" },
        { from: "pass2", to: "terminologi", kind: "konsult" },
      ],
      resultat: { falt: "Kod körs regionalt, resultat sammanställs centralt", varde: "federerad princip", extra: "Samma princip som kataraktpiloten prövade. En region som uppfyller kontraktet är fullvärdig deltagare oavsett plattform." },
    },
    {
      id: "larande", kod: "Lärande mappning", scenario: "AI föreslår, människan validerar, beslutet sparas — och förbättrar maskinen",
      steg: {
        kalla:    { state: "pass", txt: "En informatiker öppnar ett nytt grunddata som ska mappas." },
        pass1:    { state: "fix",  txt: "AI-assistenten läser namn, beskrivning, kodverk och datatyp och föreslår en mappning — direkt om den är säker, annars en rankad lista. Människan i loopen granskar och godkänner eller korrigerar." },
        pass2:    { state: "pass", txt: "Det godkända beslutet används när standardmodellen omvandlas till utgående format." },
        nod:      { state: "pass", txt: "Inget särskilt centralt i det här scenariot." },
        pass4:    { state: "pass", txt: "Beslutet bär hela vägen till OMOP utan att mappas om." },
        sekundar: { state: "pass", txt: "Resultatet blir tillgängligt — och varje likartat fält i ett annat register eller en annan region har nu det godkända beslutet som referens." },
      },
      lankar: [
        { from: "pass1", to: "organik", kind: "konsult" },
        { from: "pass1", to: "terminologi", kind: "konsult" },
        { from: "pass1", to: "ai", kind: "konsult" },
        { from: "pass1", to: "ai", kind: "loop" },
      ],
      resultat: { falt: "Människans validering → AI-assistentens minne", varde: "lärloopen sluts", extra: "Manuell mappning tar månader per register. Varje kvalitetssäkring förbättrar maskinen — det här är lärloopen som v1-verktyget ännu inte har." },
    },
  ];

  const H = 124;
  const stepX = (id) => ((STEG.findIndex((s) => s.id === id) + 0.5) / STEG.length) * 100;
  const kallaX = (id) => ((KALLOR.findIndex((k) => k.id === id) + 0.5) / KALLOR.length) * 100;

  // Tre-lagers-lagring — en miljöegenskap i målbilden, visas som egen liten rad
  const LAGER = [
    { namn: "Rålogg", txt: "Inkommande data landar rått, bundet till sin proveniens, innan den normaliseras." },
    { namn: "Operativt openEHR-lager", txt: "Bär den longitudinella journalen. Harmoniserade arketyper är interoperabilitetsmekanismen; AQL förenar vid frågetillfället." },
    { namn: "Analyslager (OMOP)", txt: "Bär populationsanalys och forskning. Här gäller att varje variabel förekommer en gång." },
  ];

  function Vision() {
    const [vid, setVid] = useState("fyra_pass");
    const v = VARIABLER.find((x) => x.id === vid);
    const aktivaKallor = new Set(v.lankar.map((l) => l.to));
    const stateColor = (st) => (st === "fix" ? C.ochre : C.green);

    const Cell = ({ children }) => (
      <div style={{ flex: "1 1 0", minWidth: 0, padding: "0 6px", boxSizing: "border-box" }}>{children}</div>
    );

    const StegBox = (s) => {
      const st = v.steg[s.id].state;
      const isFix = st === "fix";
      return (
        <div style={{
          background: isFix ? C.ochreTint : C.tealTint,
          border: `1.5px solid ${isFix ? C.ochreLine : C.tealLine}`,
          borderRadius: 11, padding: "12px 10px", textAlign: "center", height: "100%", boxSizing: "border-box",
        }}>
          <div style={{ fontFamily: display, fontWeight: 800, fontSize: 15, color: isFix ? C.ochre : C.tealDark }}>{s.namn}</div>
          <div style={{ fontSize: 11.5, color: C.slate, marginTop: 2 }}>{s.under}</div>
        </div>
      );
    };

    const KallaBox = (k) => {
      const on = aktivaKallor.has(k.id);
      return (
        <div style={{
          background: on ? C.paper : "#F4F3EE",
          border: `1.5px solid ${on ? C.teal : C.hair}`,
          borderRadius: 11, padding: "11px 9px", textAlign: "center", height: "100%", boxSizing: "border-box",
          opacity: on ? 1 : 0.45, transition: "opacity .35s ease, border-color .35s ease",
        }}>
          <div style={{ fontFamily: display, fontWeight: 700, fontSize: 13.5, color: on ? C.ink : C.slate }}>{k.namn}</div>
          <div style={{ fontSize: 11, color: C.slate, marginTop: 2 }}>{k.under}</div>
        </div>
      );
    };

    const lineStyle = (kind) => {
      if (kind === "loop") return { stroke: C.ochre, dash: "5 4", marker: "url(#vhOchre)" };
      return { stroke: C.teal, dash: "5 4", marker: "url(#vhTeal)" };
    };

    const stegLista = STEG.map((s) => ({ s, d: v.steg[s.id] }));

    return (
      <div style={{ background: C.bg, minHeight: "100vh", color: C.ink, fontFamily: body, padding: "44px 24px 72px" }}>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />

        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          <div style={{ height: 3, width: 64, background: C.teal, marginBottom: 22, borderRadius: 2 }} />
          <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".14em", color: C.teal, marginBottom: 10 }}>MÅLBILDEN — DEN REGIONGEMENSAMMA UTVECKLINGSMILJÖN</div>
          <h1 style={{ fontFamily: display, fontWeight: 800, fontSize: 36, lineHeight: 1.08, margin: "0 0 14px", letterSpacing: "-0.02em", maxWidth: 860 }}>
            En mappningsmotor, fyra pass, fyra kunskapslager
          </h1>
          <p style={{ fontSize: 16, lineHeight: 1.7, color: C.slate, margin: "0 0 18px", maxWidth: 800 }}>
            Det här är <strong>visionen</strong>, inte vad som är byggt i v1. Data tar sig från regionernas källsystem, genom standardisering, till de format olika mottagare behöver: kvalitetsregister, Socialstyrelsen, forskning och europeisk sekundäranvändning. Allt vilar på en <strong>enda motor som körs i flera pass</strong> och på fyra kunskapslager som motorn konsulterar under varje transformation.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: C.slate, margin: "0 0 18px", maxWidth: 800 }}>
            Principen är <strong>federerad</strong>: regionerna behåller kontrollen över sin data och kör koden i sin egen miljö. Den centrala noden tar emot standardiserade resultat och sammanställer dem — samma princip som prövades i kataraktpiloten. Hävstången ligger i kontraktet, inte i leverantörsvalet.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: C.slate, margin: "0 0 26px", maxWidth: 800 }}>
            Välj en rörelse nedan. Pilarna visar vilka kunskapslager motorn frågar och var en lärloop sluts. De fyra lagren förklaras längre ner, följt av lagringen i tre lager.
          </p>

          {/* Scenarioväljare */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 28 }}>
            {VARIABLER.map((x) => {
              const on = x.id === vid;
              return (
                <button key={x.id} onClick={() => setVid(x.id)} style={{
                  cursor: "pointer", border: `1.5px solid ${on ? C.teal : C.hair}`,
                  background: on ? C.tealDark : C.paper, color: on ? "#fff" : C.ink,
                  borderRadius: 10, padding: "10px 16px", textAlign: "left", fontFamily: body, maxWidth: 260,
                }}>
                  <div style={{ fontFamily: display, fontSize: 14, fontWeight: 700 }}>{x.kod}</div>
                  <div style={{ fontSize: 11.5, color: on ? "#D7E7E5" : C.slate, marginTop: 2 }}>{x.scenario}</div>
                </button>
              );
            })}
          </div>

          {/* Diagram: pass-pipeline → kopplingsband → kunskapslager */}
          <div style={{ background: C.paper, border: `1px solid ${C.hair}`, borderRadius: 16, padding: "26px 22px 22px" }}>
            <div style={{ display: "flex", alignItems: "stretch" }}>
              {STEG.map((s, i) => (
                <Cell key={s.id}>
                  <div style={{ display: "flex", alignItems: "center", height: "100%" }}>
                    <div style={{ flex: 1 }}>{StegBox(s)}</div>
                    {i < STEG.length - 1 && <div style={{ color: C.tealLine, fontSize: 18, fontWeight: 800, padding: "0 1px" }}>→</div>}
                  </div>
                </Cell>
              ))}
            </div>

            <svg width="100%" height={H} style={{ display: "block", overflow: "visible", margin: "2px 0" }}>
              <defs>
                <marker id="vhTeal" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.teal} />
                </marker>
                <marker id="vhOchre" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.ochre} />
                </marker>
              </defs>
              {v.lankar.map((l, i) => {
                const ls = lineStyle(l.kind);
                const sx = `${stepX(l.from)}%`;
                const kx = `${kallaX(l.to)}%`;
                // konsult: pass (topp) → lager (botten). loop: lager (botten) → pass (topp).
                const up = l.kind === "loop";
                const x1 = up ? kx : sx, y1 = up ? H - 6 : 6;
                const x2 = up ? sx : kx, y2 = up ? 6 : H - 6;
                return (
                  <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                    stroke={ls.stroke} strokeWidth="2" strokeDasharray={ls.dash}
                    markerEnd={ls.marker} />
                );
              })}
            </svg>

            <div style={{ display: "flex", alignItems: "stretch" }}>
              {KALLOR.map((k) => (
                <Cell key={k.id}>{KallaBox(k)}</Cell>
              ))}
            </div>

            <div style={{ display: "flex", gap: 22, flexWrap: "wrap", marginTop: 18, paddingTop: 14, borderTop: `1px solid ${C.hair}`, fontSize: 12.5, color: C.slate }}>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.teal}`, verticalAlign: "middle", marginRight: 7 }} />motorn frågar lagret</span>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.ochre}`, verticalAlign: "middle", marginRight: 7 }} />beslut återförs (lärloop)</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.green, verticalAlign: "middle", marginRight: 7 }} />passet löper på</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.ochre, verticalAlign: "middle", marginRight: 7 }} />här händer det centrala</span>
            </div>
          </div>

          {/* Vad kunskapslagren är — i klartext */}
          <div style={{ marginTop: 34 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 22, margin: "0 0 4px", letterSpacing: "-0.01em" }}>De fyra kunskapslagren — i klartext</h2>
            <p style={{ fontSize: 14, color: C.slate, margin: "0 0 18px", maxWidth: 740 }}>Motorn äger exekveringen, men kunskapen om vad som ska transformeras ligger i fyra lager som var och en svarar på en egen fråga. Lager som motorn frågar i den valda rörelsen är markerade.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12 }}>
              {KALLOR.map((k) => {
                const on = aktivaKallor.has(k.id);
                return (
                  <div key={k.id} style={{ background: C.paper, border: `1.5px solid ${on ? C.teal : C.hair}`, borderRadius: 12, padding: "16px 18px", boxShadow: on ? `0 0 0 3px ${C.tealTint}` : "none" }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                      <span style={{ fontFamily: display, fontWeight: 800, fontSize: 16, color: C.tealDark }}>{k.namn}</span>
                      <span style={{ fontSize: 12, color: C.slate }}>· {k.under}</span>
                      {on && <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", color: C.teal, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 20, padding: "2px 9px" }}>FRÅGAS HÄR</span>}
                    </div>
                    <div style={{ fontSize: 14, color: C.slate, lineHeight: 1.6 }}>{k.forklaring}</div>
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.hair}` }}>
                      <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".08em", color: C.slate, marginBottom: 6 }}>STATUS I MÅLBILDEN</div>
                      {k.urls.length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          {k.urls.map((u) => (
                            <a key={u.href} href={u.href} target="_blank" rel="noopener noreferrer" style={{ fontFamily: mono, fontSize: 12.5, color: C.teal, textDecoration: "none", wordBreak: "break-all" }}>↗ {u.label}</a>
                          ))}
                          <div style={{ fontSize: 12.5, color: C.slate, fontStyle: "italic", marginTop: 2 }}>{k.note}</div>
                        </div>
                      ) : (
                        <div style={{ fontSize: 12.5, color: C.slate, fontStyle: "italic" }}>{k.note}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Tre-lagers-lagring */}
          <div style={{ marginTop: 30 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 20, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Lagring i tre lager</h2>
            <p style={{ fontSize: 14, color: C.slate, margin: "0 0 14px", maxWidth: 740 }}>En miljöegenskap i målbilden: rått skiljs från förädlat, det operativa lagret bär journalen, analyslagret bär forskningen.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
              {LAGER.map((l, i) => (
                <div key={l.namn} style={{ background: C.slateTint, border: `1px solid ${C.hair}`, borderRadius: 12, padding: "14px 16px" }}>
                  <div style={{ fontFamily: display, fontWeight: 800, fontSize: 14.5, color: C.slate, marginBottom: 4 }}>{i + 1}. {l.namn}</div>
                  <div style={{ fontSize: 13.5, color: C.slate, lineHeight: 1.55 }}>{l.txt}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Stegberättelse för vald rörelse */}
          <div style={{ marginTop: 34 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 22, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Så ser rörelsen ut: <span style={{ fontWeight: 800, color: C.tealDark }}>{v.kod}</span></h2>
            <p style={{ fontSize: 14, color: C.slate, margin: "0 0 18px" }}>Scenario: {v.scenario}</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 10 }}>
              {stegLista.map(({ s, d }, i) => (
                <div key={s.id} style={{ display: "flex", gap: 14, background: C.paper, border: `1px solid ${C.hair}`, borderRadius: 12, padding: "14px 16px" }}>
                  <div style={{ flex: "0 0 30px", height: 30, borderRadius: 15, background: stateColor(d.state), color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: display, fontWeight: 800, fontSize: 14 }}>{i + 1}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: display, fontWeight: 700, fontSize: 15, color: C.ink }}>{s.namn} <span style={{ fontWeight: 500, color: C.slate, fontSize: 13 }}>· {s.under}</span></div>
                    <div style={{ fontSize: 14.5, color: C.slate, lineHeight: 1.6, marginTop: 3 }}>{d.txt}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Resultat: vad målbilden ger */}
          <div style={{ marginTop: 26, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 14, padding: "20px 22px" }}>
            <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".12em", color: C.tealDark, marginBottom: 10 }}>VAD MÅLBILDEN GER</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 28px", alignItems: "baseline" }}>
              <div style={{ fontFamily: display, fontSize: 17, fontWeight: 800, color: C.tealDark }}>{v.resultat.falt}</div>
              <div style={{ fontFamily: mono, fontSize: 15, color: C.ink }}>→ {v.resultat.varde}</div>
            </div>
            {v.resultat.extra && <div style={{ fontSize: 13.5, color: C.slate, marginTop: 8 }}>{v.resultat.extra}</div>}
          </div>
        </div>
      </div>
    );
  }

  window.kuComponents['MappningVisionHelhet'] = Vision;
})();
