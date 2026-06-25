// ── Mappning till FHIR #5: Hela flödet — variabel till FHIR, steg för steg ──
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

  // Pipelinens steg (vänster → höger)
  const STEG = [
    { id: "denodo",   namn: "Databasen",            under: "vi hämtar uppgiften" },
    { id: "ai",       namn: "AI:n",                 under: "gör mappningen" },
    { id: "forslag",  namn: "Förslag",              under: "AI:ns utkast" },
    { id: "qa",       namn: "AI-granskning",        under: "en andra AI kollar" },
    { id: "manniska", namn: "Människa",             under: "kvalitetssäkrar" },
    { id: "fhir",     namn: "FHIR-tabellen",        under: "uppgiften landar" },
  ];

  // Källane (under pipelinen) — med klarspråksförklaring och URL:er
  const KALLOR = [
    { id: "regelbok",   namn: "FHIR-regelboken",   under: "den internationella regelboken",
      forklaring: "FHIR är ett internationellt språk för vårddata. Regelboken talar om vilka 'fack' som finns att lägga varje uppgift i, och vilka regler facket har — till exempel att ett datum måste skrivas på ett bestämt sätt. Hit går AI:n för att veta vilket fack en uppgift hör hemma i.",
      urls: [ { label: "hl7.org/fhir/R4", href: "https://hl7.org/fhir/R4/" } ] },
    { id: "sos",        namn: "Socialstyrelsen",   under: "Sveriges officiella kodlistor",
      forklaring: "Socialstyrelsen äger de officiella listorna över vad som gjordes i vården (åtgärdskoder, kallade KVÅ) och diagnoser (ICD-10). Varje kod har en bestämd svensk text. Hit går AI:n för att kontrollera att en kod verkligen finns och vad den officiellt heter.",
      urls: [ { label: "klassifikationer.socialstyrelsen.se (sök kod)", href: "https://klassifikationer.socialstyrelsen.se/" }, { label: "KVÅ-sidan", href: "https://www.socialstyrelsen.se/statistik-och-data/klassifikationer-och-koder/kva/" } ] },
    { id: "conceptmap", namn: "Kodöversättning",   under: "en översättningstabell",
      forklaring: "Våra egna system kan lagra en uppgift som en siffra (t.ex. 2 för kvinna) medan standarden vill ha ett annat ord (female). Översättningstabellen säger exakt hur vår kod ska översättas till standardens. Hit går AI:n när ett värde behöver översättas.",
      urls: [ { label: "ConceptMap (FHIR R4)", href: "https://hl7.org/fhir/R4/conceptmap.html" }, { label: "administrative-gender (värdelista)", href: "https://hl7.org/fhir/R4/valueset-administrative-gender.html" } ] },
    { id: "mallar",     namn: "Svenska FHIR-mallar", under: "färdiga svenska mallar",
      forklaring: "Sverige (HL7 Sweden och Inera) har redan tagit fram mallar för hur viss vårddata ska beskrivas. Hit går AI:n för att se om någon redan löst hur en uppgift ska beskrivas — då gör vi likadant istället för att hitta på eget. För väntetidsmåtten fanns ingen mall ännu, så vi fick göra en egen.",
      urls: [ { label: "hl7.se/fhir/ig/base (basprofiler)", href: "http://hl7.se/fhir/ig/base/" }, { label: "hl7.se", href: "https://hl7.se/" } ] },
    { id: "minne",      namn: "Lärande databasen", under: "minnet av tidigare rättelser",
      forklaring: "Varje gång en människa rättar något sparas det som en regel: 'den här uppgiften ska hanteras så här'. Hit går AI:n allra först nästa gång — hittar den en regel följer den den direkt, så att samma fel inte görs om.",
      urls: [], note: "Internt — vår egen databas, ingen publik URL." },
  ];

  // pass = klart/oförändrat (grön) · fix = rättelse skedde här (amber)
  const VARIABLER = [
    {
      id: "start_datum", kod: "start_datum", scenario: "Rakt igenom — inget behöver ändras",
      steg: {
        denodo:   { state: "pass", txt: "Vi hämtar uppgiften ur databasen: operationsdatumet 2026-02-18." },
        ai:       { state: "pass", txt: "AI:n slår upp i FHIR-regelboken vilket fack ett operationsdatum hör hemma i, och hittar fältet för 'när åtgärden gjordes'. Datumet passar precis som det är." },
        forslag:  { state: "pass", txt: "AI:ns förslag: lägg 2026-02-18 i fältet för utförandedatum." },
        qa:       { state: "pass", txt: "En andra AI granskar att datumet är skrivet på rätt sätt. Allt stämmer." },
        manniska: { state: "pass", txt: "Människan tittar igenom och godkänner. Inget behöver ändras." },
        fhir:     { state: "pass", txt: "Datumet hamnar på sin plats i FHIR-tabellen." },
      },
      lankar: [ { from: "ai", to: "regelbok", kind: "read" } ],
      resultat: { falt: "Procedure.performedDateTime", varde: "2026-02-18", extra: "Datumet behövde inte ändras alls." },
    },
    {
      id: "kon", kod: "kon", scenario: "Värdet måste översättas",
      steg: {
        denodo:   { state: "pass", txt: "Vi hämtar uppgiften: kön lagrat som siffran 2 (hos oss betyder 2 kvinna)." },
        ai:       { state: "pass", txt: "AI:n hittar rätt fack i FHIR-regelboken (fältet för kön), men siffran 2 betyder inget för andra system. AI:n använder en översättningstabell som säger att 2 ska bli ordet 'female'." },
        forslag:  { state: "pass", txt: "AI:ns förslag: lägg 'female' i könsfältet." },
        qa:       { state: "pass", txt: "En andra AI kontrollerar att 'female' är ett av de tillåtna orden. Det stämmer." },
        manniska: { state: "pass", txt: "Människan godkänner." },
        fhir:     { state: "pass", txt: "Könet hamnar på sin plats, nu på ett språk alla system förstår." },
      },
      lankar: [ { from: "ai", to: "regelbok", kind: "read" }, { from: "ai", to: "conceptmap", kind: "read" } ],
      resultat: { falt: "Patient.gender", varde: "female", extra: "Vår siffra 2 översattes till 'female' via översättningstabellen." },
    },
    {
      id: "atgard_kod", kod: "atgard_kod", scenario: "Koden måste slås upp och få rätt etikett",
      steg: {
        denodo:   { state: "pass", txt: "Vi hämtar uppgiften: åtgärdskoden CJE05 (en svensk KVÅ-kod för en starroperation)." },
        ai:       { state: "pass", txt: "AI:n hittar facket för 'vad som gjordes' i FHIR-regelboken. Sedan slår den upp CJE05 hos Socialstyrelsen för att bekräfta att koden finns och vad den officiellt heter, och hämtar i de svenska mallarna den 'adress' som talar om att det är just en KVÅ-kod." },
        forslag:  { state: "pass", txt: "AI:ns förslag: koden CJE05, märkt som en KVÅ-kod, med den officiella texten 'Kataraktextraktion, fakoemulsifikation'." },
        qa:       { state: "pass", txt: "En andra AI kontrollerar att koden finns hos Socialstyrelsen och att etiketten stämmer. Allt rätt." },
        manniska: { state: "pass", txt: "Människan godkänner." },
        fhir:     { state: "pass", txt: "Åtgärden hamnar på sin plats med rätt kod och rätt text." },
      },
      lankar: [ { from: "ai", to: "regelbok", kind: "read" }, { from: "ai", to: "sos", kind: "read" }, { from: "ai", to: "mallar", kind: "read" } ],
      resultat: { falt: "Procedure.code", varde: "CJE05", extra: "Märkt som KVÅ-kod, officiell text: Kataraktextraktion, fakoemulsifikation." },
    },
    {
      id: "vardgaranti", kod: "vardgaranti", scenario: "Inget färdigt fack finns — AI:n granskar, människan rättar, regeln sparas",
      steg: {
        denodo:   { state: "pass", txt: "Vi hämtar uppgiften: omfattades patienten av vårdgarantin? Här: JA." },
        ai:       { state: "pass", txt: "Det finns inget färdigt FHIR-fack för 'vårdgaranti'. AI:n gör en första gissning och lägger uppgiften i ett fält som handlar om hur brådskande vården är, eftersom det verkade ligga närmast." },
        forslag:  { state: "fix",  txt: "AI:ns förslag är tekniskt tillåtet, men betyder fel sak: 'brådskande'-fältet handlar om hur akut något är, inte om patienten hade vårdgaranti." },
        qa:       { state: "fix",  txt: "En andra AI läser vad fältet egentligen får innehålla och ser att ett ja/nej om vårdgaranti inte hör hemma där. Den flaggar felet och föreslår att vi skapar ett eget fält." },
        manniska: { state: "fix",  txt: "Människan håller med och bestämmer: vårdgaranti ska vara ett eget ja/nej-fält med ett bestämt namn. Det är rättelsen. Den sparas i den lärande databasen som en regel — ungefär 'vårdgaranti ska alltid hanteras så här' — så att AI:n kan följa den i framtiden." },
        fhir:     { state: "pass", txt: "Uppgiften hamnar i sitt nya, egna ja/nej-fält: vårdgaranti = ja." },
      },
      lankar: [
        { from: "ai", to: "regelbok", kind: "read" },
        { from: "qa", to: "regelbok", kind: "read" },
        { from: "qa", to: "mallar", kind: "read" },
        { from: "manniska", to: "minne", kind: "write" },
      ],
      resultat: { falt: "Extension[vardgaranti]", varde: "ja", extra: "Eget fält skapat. Rättelsen sparades som en regel i den lärande databasen." },
    },
    {
      id: "vardgaranti_igen", kod: "vardgaranti — nästa gång", scenario: "AI:n läser minnet först och slipper göra om felet",
      steg: {
        denodo:   { state: "pass", txt: "Ett nytt sjukhus skickar in samma sorts uppgift: vårdgaranti, den här gången NEJ." },
        ai:       { state: "pass", txt: "Innan AI:n gissar något slår den upp i den lärande databasen — och hittar regeln som människan sparade förra gången. AI:n följer den direkt och lägger uppgiften i rätt eget fält på en gång. Den gör alltså inte om gårdagens fel." },
        forslag:  { state: "pass", txt: "AI:ns förslag är rätt från början: vårdgaranti = nej i sitt egna ja/nej-fält." },
        qa:       { state: "pass", txt: "En andra AI hittar inget att anmärka på — felet är redan borta tack vare minnet." },
        manniska: { state: "pass", txt: "Människan godkänner. Ingen ny rättelse behövs." },
        fhir:     { state: "pass", txt: "Uppgiften hamnar rätt direkt: vårdgaranti = nej." },
      },
      lankar: [
        { from: "ai", to: "minne", kind: "loop" },
        { from: "ai", to: "regelbok", kind: "read" },
      ],
      resultat: { falt: "Extension[vardgaranti]", varde: "nej", extra: "AI:n följde en sparad regel ur den lärande databasen — rätt från första försöket." },
    },
  ];

  const H = 124; // höjd på kopplingsbandet
  const stepX = (id) => ((STEG.findIndex((s) => s.id === id) + 0.5) / STEG.length) * 100;
  const kallaX = (id) => ((KALLOR.findIndex((k) => k.id === id) + 0.5) / KALLOR.length) * 100;

  function Flode() {
    const [vid, setVid] = useState("start_datum");
    const v = VARIABLER.find((x) => x.id === vid);
    const aktivaKallor = new Set(v.lankar.map((l) => l.to));
    const stateColor = (st) => (st === "fix" ? C.ochre : C.green);

    const Cell = ({ children, count }) => (
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
      if (kind === "write") return { stroke: C.ochre, dash: "0", marker: "url(#mfOchre)" };
      if (kind === "loop") return { stroke: C.ochre, dash: "5 4", marker: "url(#mfOchre)" };
      return { stroke: C.teal, dash: "5 4", marker: "url(#mfTeal)" };
    };

    const stegLista = STEG.map((s) => ({ s, d: v.steg[s.id] }));

    return (
      <div style={{ background: C.bg, minHeight: "100vh", color: C.ink, fontFamily: body, padding: "44px 24px 72px" }}>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />

        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          <div style={{ height: 3, width: 64, background: C.teal, marginBottom: 22, borderRadius: 2 }} />
          <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".14em", color: C.teal, marginBottom: 10 }}>HELA FLÖDET, STEG FÖR STEG</div>
          <h1 style={{ fontFamily: display, fontWeight: 800, fontSize: 36, lineHeight: 1.08, margin: "0 0 14px", letterSpacing: "-0.02em", maxWidth: 820 }}>
            Från väntetidsvariabel till FHIR-profilens tabell
          </h1>
          <p style={{ fontSize: 16, lineHeight: 1.7, color: C.slate, margin: "0 0 18px", maxWidth: 780 }}>
            Vårddata måste översättas till ett gemensamt språk som alla system förstår, kallat FHIR. Här ser du hur en enskild uppgift tar sig hela vägen dit. Vi hämtar uppgiften ur databasen, en AI gör ett första förslag och slår upp det som behövs i ett par kunskapskällor, en andra AI granskar att förslaget faktiskt betyder rätt sak, och en människa kvalitetssäkrar till sist. När människan rättar något sparas rättelsen i ett minne — en lärande databas — som AI:n läser nästa gång, så att samma fel inte görs om.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: C.slate, margin: "0 0 26px", maxWidth: 780 }}>
            Välj en uppgift nedan. Pilarna visar vilka källor AI:n gick till och varför, och var en rättelse skedde. Vad varje källa egentligen är förklaras längre ner.
          </p>

          {/* Variabelväljare */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 28 }}>
            {VARIABLER.map((x) => {
              const on = x.id === vid;
              return (
                <button key={x.id} onClick={() => setVid(x.id)} style={{
                  cursor: "pointer", border: `1.5px solid ${on ? C.teal : C.hair}`,
                  background: on ? C.tealDark : C.paper, color: on ? "#fff" : C.ink,
                  borderRadius: 10, padding: "10px 16px", textAlign: "left", fontFamily: body,
                }}>
                  <div style={{ fontFamily: mono, fontSize: 14, fontWeight: 600 }}>{x.kod}</div>
                  <div style={{ fontSize: 11.5, color: on ? "#D7E7E5" : C.slate, marginTop: 2 }}>{x.scenario}</div>
                </button>
              );
            })}
          </div>

          {/* Diagram: pipeline → kopplingsband → källane */}
          <div style={{ background: C.paper, border: `1px solid ${C.hair}`, borderRadius: 16, padding: "26px 22px 22px" }}>
            {/* Pipeline */}
            <div style={{ display: "flex", alignItems: "stretch" }}>
              {STEG.map((s, i) => (
                <Cell key={s.id} count={STEG.length}>
                  <div style={{ display: "flex", alignItems: "center", height: "100%" }}>
                    <div style={{ flex: 1 }}>{StegBox(s)}</div>
                    {i < STEG.length - 1 && <div style={{ color: C.tealLine, fontSize: 18, fontWeight: 800, padding: "0 1px" }}>→</div>}
                  </div>
                </Cell>
              ))}
            </div>

            {/* Kopplingsband (SVG) */}
            <svg width="100%" height={H} style={{ display: "block", overflow: "visible", margin: "2px 0" }}>
              <defs>
                <marker id="mfTeal" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.teal} />
                </marker>
                <marker id="mfOchre" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.ochre} />
                </marker>
              </defs>
              {v.lankar.map((l, i) => {
                const ls = lineStyle(l.kind);
                const sx = `${stepX(l.from)}%`;
                const kx = `${kallaX(l.to)}%`;
                // read/write: steg (topp) → källa (botten). loop: källa (botten) → steg (topp).
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

            {/* Källane */}
            <div style={{ display: "flex", alignItems: "stretch" }}>
              {KALLOR.map((k) => (
                <Cell key={k.id} count={KALLOR.length}>{KallaBox(k)}</Cell>
              ))}
            </div>

            {/* Legend */}
            <div style={{ display: "flex", gap: 22, flexWrap: "wrap", marginTop: 18, paddingTop: 14, borderTop: `1px solid ${C.hair}`, fontSize: 12.5, color: C.slate }}>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.teal}`, verticalAlign: "middle", marginRight: 7 }} />slår upp i källa</span>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px solid ${C.ochre}`, verticalAlign: "middle", marginRight: 7 }} />rättelse skrivs till minnet</span>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.ochre}`, verticalAlign: "middle", marginRight: 7 }} />AI:n läser minnet (lärande-loop)</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.green, verticalAlign: "middle", marginRight: 7 }} />klart / oförändrat</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.ochre, verticalAlign: "middle", marginRight: 7 }} />rättat här</span>
            </div>
          </div>

          {/* Vad källorna är — i klartext */}
          <div style={{ marginTop: 34 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 22, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Vad källorna är — i klartext</h2>
            <p style={{ fontSize: 14, color: C.slate, margin: "0 0 18px", maxWidth: 720 }}>De fem rutorna i flödet ovan. Här står vad var och en faktiskt innehåller och varför AI:n går dit. Källor som används för den valda uppgiften är markerade.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12 }}>
              {KALLOR.map((k) => {
                const on = aktivaKallor.has(k.id);
                return (
                  <div key={k.id} style={{ background: C.paper, border: `1.5px solid ${on ? C.teal : C.hair}`, borderRadius: 12, padding: "16px 18px", boxShadow: on ? `0 0 0 3px ${C.tealTint}` : "none" }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                      <span style={{ fontFamily: display, fontWeight: 800, fontSize: 16, color: C.tealDark }}>{k.namn}</span>
                      <span style={{ fontSize: 12, color: C.slate }}>· {k.under}</span>
                      {on && <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", color: C.teal, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 20, padding: "2px 9px" }}>ANVÄNDS HÄR</span>}
                    </div>
                    <div style={{ fontSize: 14, color: C.slate, lineHeight: 1.6 }}>{k.forklaring}</div>
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.hair}` }}>
                      <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".08em", color: C.slate, marginBottom: 6 }}>AI:N TITTAR HÄR</div>
                      {k.urls.length > 0 ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          {k.urls.map((u) => (
                            <a key={u.href} href={u.href} target="_blank" rel="noopener noreferrer" style={{ fontFamily: mono, fontSize: 12.5, color: C.teal, textDecoration: "none", wordBreak: "break-all" }}>↗ {u.label}</a>
                          ))}
                        </div>
                      ) : (
                        <div style={{ fontFamily: mono, fontSize: 12.5, color: C.slate, fontStyle: "italic" }}>{k.note}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stegberättelse för vald variabel */}
          <div style={{ marginTop: 34 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 22, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Så går det till för <span style={{ fontFamily: mono, fontWeight: 600 }}>{v.kod}</span></h2>
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

          {/* Resultat: var datan landar */}
          <div style={{ marginTop: 26, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 14, padding: "20px 22px" }}>
            <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".12em", color: C.tealDark, marginBottom: 10 }}>RESULTAT — RAD I FHIR-PROFILENS TABELL</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 28px", alignItems: "baseline" }}>
              <div style={{ fontFamily: mono, fontSize: 18, fontWeight: 600, color: C.tealDark }}>{v.resultat.falt}</div>
              <div style={{ fontFamily: mono, fontSize: 16, color: C.ink }}>= {v.resultat.varde}</div>
            </div>
            {v.resultat.extra && <div style={{ fontSize: 13.5, color: C.slate, marginTop: 8 }}>{v.resultat.extra}</div>}
          </div>
        </div>
      </div>
    );
  }

  window.kuComponents['MappningFlode'] = Flode;
})();
