// ── Mappning till FHIR #6: Verktyget i v1 — från källschema till mappningsartefakt ──
// Källtroget mot koden i repot. Beskriver bara det som faktiskt är byggt (RL-01/02/03).
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

  // Pipelinens steg (vänster → höger) — användarens end-to-end-flöde i v1
  const STEG = [
    { id: "projekt",    namn: "Projekt",        under: "skapas, RBAC sätts" },
    { id: "kallschema", namn: "Källschema",     under: "importeras & parsas" },
    { id: "malschema",  namn: "Målschema",      under: "väljs (FHIR/OMOP)" },
    { id: "forslag",    namn: "Förslag",        under: "motorn rankar fält" },
    { id: "version",    namn: "Granska",        under: "människan skapar version" },
    { id: "validering", namn: "Validering",     under: "regler + policy" },
    { id: "export",     namn: "Export",         under: "artefakt + SQL" },
  ];

  // Källorna (under pipelinen) = de format-oberoende paketen motorn använder.
  // url-fält saknas medvetet: detta är intern kod i repot, inte publika tjänster.
  const KALLOR = [
    { id: "core", namn: "Det kanoniska navet", under: "packages/core",
      forklaring: "CanonicalSchema/CanonicalField är navet. Varje källschema parsas in hit, och varje målschema beskrivs här. Det är en neutral mittpunkt som källor mappas TILL och mål mappas FRÅN — samma nav-och-eker-princip som målbilden vilar på. Här bor även fält, datatyper, kardinalitet och constraints på ett ställe (målbildens administrativa modell, B4).",
      note: "I repot: packages/core/models/canonical_schema.py" },
    { id: "adapters", namn: "Inläsningsadaptrar", under: "packages/adapters",
      forklaring: "Input-parsers som översätter ett källformat till det kanoniska navet. FUNGERAR idag: JSON Schema och CSV. STUBBAR (inte färdiga): FHIR-profil, OMOP, openEHR, SQL DDL, Parquet. Ett adapterregister gör formaten öppna/konfigurerbara i stället för hårdkodade (RL-03) — en ny källa läggs till utan att motorn ändras.",
      note: "I repot: packages/adapters/input/ + registry.py" },
    { id: "standards", namn: "Förinlästa målscheman", under: "apps/api/standards",
      forklaring: "Två målscheman laddas vid uppstart: FHIR R4 (9 resurser) och OMOP CDM 5.4 (11 tabeller). De är pluggbara mål — samma motor mappar mot vilket som. Att byta eller lägga till ett mål ändrar inte förslags- eller valideringslogiken.",
      note: "I repot: apps/api/standards/ (laddas i create_app)" },
    { id: "suggestions", namn: "Förslagsmotorn", under: "packages/suggestions",
      forklaring: "SuggestionEngine ger rankade fält-mappningsförslag via viktade strategier (namn, typ, kardinalitet, constraints) plus en valfri semantisk provider. Defaulten är lexikal; finns en Azure OpenAI-nyckel används den i stället. Poängen är förklarbara — det är inte en svart låda. Beslutet överlåts alltid till människan.",
      note: "I repot: packages/suggestions/engine.py + semantic/" },
    { id: "validation", namn: "Valideringsregler", under: "packages/validation",
      forklaring: "Regler som kontrollerar mappningen strukturellt och semantiskt. Allvarlighetsgraden sätts av en policy PER ANROP — den är inte hårdkodad. Samma kontroll-tänk som kataraktpilotens metod, där en koppling kan vara giltig men ändå betyda fel sak.",
      note: "I repot: packages/validation/" },
    { id: "script_gen", namn: "SQL-generator", under: "packages/script_gen",
      forklaring: "SqlInsertSelectGenerator producerar deterministisk INSERT … SELECT-SQL ur en mappning. SQL:en GENERERAS men KÖRS ALDRIG (RL-01) — den är en artefakt att granska och ta vidare, inte en transformation som verktyget exekverar. Ingen patient-/individdata läses någonsin in (RL-02).",
      note: "I repot: packages/script_gen/generators/sql_insert_select.py" },
  ];

  // pass = säkert/validerat (grön) · low = osäkert/flaggat för granskning (amber)
  const VARIABLER = [
    {
      id: "kon", kod: "kon → Patient.gender", scenario: "Rakt igenom — högt rankat förslag, validering ok",
      steg: {
        projekt:    { state: "pass", txt: "En analytiker skapar ett projekt. RBAC är simulerad via X-User-Id/X-User-Role — rollen avgör vad som får göras (viewer/analyst/approver/admin)." },
        kallschema: { state: "pass", txt: "Källschemat importeras som JSON Schema. Adaptern parsar in fältet 'kon' till det kanoniska navet med datatyp och kardinalitet." },
        malschema:  { state: "pass", txt: "Målschemat FHIR R4 väljs ur de förinlästa standarderna. Fältet Patient.gender finns där." },
        forslag:    { state: "pass", txt: "SuggestionEngine matchar 'kon' mot Patient.gender. Namn- och typstrategierna ger hög, förklarbar poäng — förslaget visas överst." },
        version:    { state: "pass", txt: "Människan granskar förslaget och skapar en mappningsversion. Beslutet loggas som ett AuditEvent." },
        validering: { state: "pass", txt: "Valideringen körs med vald policy. Inga regelbrott — mappningen är strukturellt giltig." },
        export:     { state: "pass", txt: "En MappingArtifact serialiseras. SQL-generatorn producerar motsvarande INSERT … SELECT — som artefakt, körs aldrig." },
      },
      lankar: [
        { from: "kallschema", to: "adapters", kind: "use" },
        { from: "malschema", to: "standards", kind: "use" },
        { from: "forslag", to: "suggestions", kind: "use" },
        { from: "export", to: "script_gen", kind: "genskip" },
      ],
      resultat: { falt: "MappingRule: kon → Patient.gender", varde: "exporterad artefakt", extra: "SQL genererades och ligger i artefakten — men kördes aldrig (RL-01)." },
    },
    {
      id: "diagnos", kod: "diagnos_kod → Condition.code", scenario: "CSV-källa, kodverk hålls öppet (RL-03)",
      steg: {
        projekt:    { state: "pass", txt: "Projektet finns redan; en ny källa läggs till." },
        kallschema: { state: "pass", txt: "Källan är en CSV-fil. CSV-adaptern (en av de två som fungerar idag) läser in kolumnen 'diagnos_kod' till navet." },
        malschema:  { state: "pass", txt: "FHIR R4 är målet; Condition.code är facket för diagnoskod." },
        forslag:    { state: "pass", txt: "Motorn föreslår Condition.code. Kodverket (ICD-10 etc.) hålls som en öppen TerminologyReference, inte hårdkodat — verktyget binder inte in ett specifikt system." },
        version:    { state: "pass", txt: "Människan godkänner och skapar versionen." },
        validering: { state: "pass", txt: "Policyn körs; constraints på fältet kontrolleras. Giltigt." },
        export:     { state: "pass", txt: "Artefakten exporteras med kodverket som referens, inte som hårdkodat värde." },
      },
      lankar: [
        { from: "kallschema", to: "adapters", kind: "use" },
        { from: "forslag", to: "suggestions", kind: "use" },
        { from: "validering", to: "validation", kind: "use" },
      ],
      resultat: { falt: "MappingRule: diagnos_kod → Condition.code", varde: "exporterad artefakt", extra: "TerminologyReference håller kodverket öppet (RL-03) — ingen tjänst anropas i v1, det är en passiv referens." },
    },
    {
      id: "operation", kod: "operation → OMOP procedure_occurrence", scenario: "Pluggbart mål — samma motor, annat målschema",
      steg: {
        projekt:    { state: "pass", txt: "Samma projekt, men nu mot ett annat mål." },
        kallschema: { state: "pass", txt: "Källfältet 'operation' finns redan i navet." },
        malschema:  { state: "pass", txt: "Här väljs OMOP CDM 5.4 i stället för FHIR. Tabellen procedure_occurrence är ett av de 11 förinlästa OMOP-objekten. Motorn, förslagslogiken och valideringen är oförändrade — bara målschemat är ett annat." },
        forslag:    { state: "pass", txt: "SuggestionEngine kör exakt samma viktade strategier mot OMOP-fälten." },
        version:    { state: "pass", txt: "Människan skapar versionen." },
        validering: { state: "pass", txt: "Samma policymotor validerar mot OMOP-tabellens fält." },
        export:     { state: "pass", txt: "Artefakt + genererad SQL för OMOP-målet. SQL:en körs inte." },
      },
      lankar: [
        { from: "malschema", to: "standards", kind: "use" },
        { from: "forslag", to: "suggestions", kind: "use" },
        { from: "export", to: "script_gen", kind: "genskip" },
      ],
      resultat: { falt: "MappingRule: operation → procedure_occurrence", varde: "exporterad artefakt", extra: "Ett nytt mål pluggades in utan att motorn ändrades — målbildens kärnlöfte, realiserat i v1." },
    },
    {
      id: "fritext", kod: "fritext_anteckning → ?", scenario: "Osäkert — motorn rankar, människan avgör",
      steg: {
        projekt:    { state: "pass", txt: "Projektet finns." },
        kallschema: { state: "pass", txt: "Fältet 'fritext_anteckning' parsas in — en ostrukturerad textkolumn utan självklart mål." },
        malschema:  { state: "pass", txt: "FHIR R4 är valt, men inget fält matchar uppenbart." },
        forslag:    { state: "low",  txt: "Ingen strategi ger hög poäng. Motorn visar en RANKAD LISTA av svaga kandidater i stället för ett säkert förslag — och säger uttryckligen att den är osäker." },
        version:    { state: "low",  txt: "Människan i loopen avgör: väljer en kandidat, skapar ett eget fält, eller lämnar fältet omappat. Verktyget beslutar aldrig självt. Valet loggas som AuditEvent." },
        validering: { state: "low",  txt: "Valideringen flaggar att fältet är svagt/omappat — med en allvarlighetsgrad som policyn för anropet bestämmer." },
        export:     { state: "pass", txt: "Artefakten exporteras med människans beslut inbakat. (Ingen SQL för ett omappat fält.)" },
      },
      lankar: [
        { from: "forslag", to: "suggestions", kind: "use" },
        { from: "version", to: "core", kind: "use" },
        { from: "validering", to: "validation", kind: "use" },
      ],
      resultat: { falt: "MappingRule: fritext_anteckning → (människans beslut)", varde: "granskad artefakt", extra: "Maskinen gör grovarbetet, människan kvalitetssäkrar. Lärloopen tillbaka till motorn är ännu inte byggd (se vision-flödet)." },
    },
  ];

  const H = 124; // höjd på kopplingsbandet
  const stepX = (id) => ((STEG.findIndex((s) => s.id === id) + 0.5) / STEG.length) * 100;
  const kallaX = (id) => ((KALLOR.findIndex((k) => k.id === id) + 0.5) / KALLOR.length) * 100;

  function Byggt() {
    const [vid, setVid] = useState("kon");
    const v = VARIABLER.find((x) => x.id === vid);
    const aktivaKallor = new Set(v.lankar.map((l) => l.to));
    const stateColor = (st) => (st === "low" ? C.ochre : C.green);

    const Cell = ({ children }) => (
      <div style={{ flex: "1 1 0", minWidth: 0, padding: "0 6px", boxSizing: "border-box" }}>{children}</div>
    );

    const StegBox = (s) => {
      const st = v.steg[s.id].state;
      const isLow = st === "low";
      return (
        <div style={{
          background: isLow ? C.ochreTint : C.tealTint,
          border: `1.5px solid ${isLow ? C.ochreLine : C.tealLine}`,
          borderRadius: 11, padding: "12px 10px", textAlign: "center", height: "100%", boxSizing: "border-box",
        }}>
          <div style={{ fontFamily: display, fontWeight: 800, fontSize: 15, color: isLow ? C.ochre : C.tealDark }}>{s.namn}</div>
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
      // genskip = artefakt/SQL produceras men körs aldrig (RL-01)
      if (kind === "genskip") return { stroke: C.ochre, dash: "5 4", marker: "url(#bvOchre)" };
      return { stroke: C.teal, dash: "5 4", marker: "url(#bvTeal)" };
    };

    const stegLista = STEG.map((s) => ({ s, d: v.steg[s.id] }));

    return (
      <div style={{ background: C.bg, minHeight: "100vh", color: C.ink, fontFamily: body, padding: "44px 24px 72px" }}>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />

        <div style={{ maxWidth: 1180, margin: "0 auto" }}>
          <div style={{ height: 3, width: 64, background: C.teal, marginBottom: 22, borderRadius: 2 }} />
          <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".14em", color: C.teal, marginBottom: 10 }}>VERKTYGET I V1 — BYGGT, INTE MÅLBILD</div>
          <h1 style={{ fontFamily: display, fontWeight: 800, fontSize: 36, lineHeight: 1.08, margin: "0 0 14px", letterSpacing: "-0.02em", maxWidth: 820 }}>
            Från källschema till exporterad mappningsartefakt
          </h1>
          <p style={{ fontSize: 16, lineHeight: 1.7, color: C.slate, margin: "0 0 18px", maxWidth: 780 }}>
            Det här är det som <strong>faktiskt finns i koden</strong> idag — ett schema-till-schema-verktyg. En analytiker skapar ett projekt, importerar ett källschema, väljer ett målschema (FHIR R4 eller OMOP), får rankade mappningsförslag, granskar och skapar en mappningsversion, validerar, och exporterar en artefakt med genererad SQL. Allt sker på schema-/metadatanivå.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: C.slate, margin: "0 0 18px", maxWidth: 780 }}>
            Tre röda linjer gäller hela vägen: <strong>ingen transformation exekveras</strong> (SQL genereras men körs aldrig, RL-01), <strong>ingen patient-/individdata läses in</strong> (RL-02), och <strong>standarderna är öppna/konfigurerbara</strong>, inte hårdkodade (RL-03). UI:t är kontraktsdrivet mot OpenAPI.
          </p>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: C.slate, margin: "0 0 26px", maxWidth: 780 }}>
            Välj en uppgift nedan. Pilarna visar vilka av repots paket som används i varje steg, och var verktyget flaggar osäkerhet. Vad varje paket innehåller står längre ner.
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

          {/* Diagram: pipeline → kopplingsband → paket */}
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
                <marker id="bvTeal" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.teal} />
                </marker>
                <marker id="bvOchre" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M0,0 L7,3 L0,6 Z" fill={C.ochre} />
                </marker>
              </defs>
              {v.lankar.map((l, i) => {
                const ls = lineStyle(l.kind);
                const sx = `${stepX(l.from)}%`;
                const kx = `${kallaX(l.to)}%`;
                return (
                  <line key={i} x1={sx} y1={6} x2={kx} y2={H - 6}
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
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.teal}`, verticalAlign: "middle", marginRight: 7 }} />paketet används i steget</span>
              <span><span style={{ display: "inline-block", width: 22, borderTop: `2px dashed ${C.ochre}`, verticalAlign: "middle", marginRight: 7 }} />SQL/artefakt genereras — körs aldrig (RL-01)</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.green, verticalAlign: "middle", marginRight: 7 }} />säkert / validerat</span>
              <span><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: C.ochre, verticalAlign: "middle", marginRight: 7 }} />osäkert / flaggat för granskning</span>
            </div>
          </div>

          {/* Vad paketen är — i klartext */}
          <div style={{ marginTop: 34 }}>
            <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 22, margin: "0 0 4px", letterSpacing: "-0.01em" }}>Vad paketen är — i klartext</h2>
            <p style={{ fontSize: 14, color: C.slate, margin: "0 0 18px", maxWidth: 720 }}>De sex rutorna i flödet ovan är repots format-oberoende paket. Här står vad var och en faktiskt innehåller. Paket som används för den valda uppgiften är markerade.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12 }}>
              {KALLOR.map((k) => {
                const on = aktivaKallor.has(k.id);
                return (
                  <div key={k.id} style={{ background: C.paper, border: `1.5px solid ${on ? C.teal : C.hair}`, borderRadius: 12, padding: "16px 18px", boxShadow: on ? `0 0 0 3px ${C.tealTint}` : "none" }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                      <span style={{ fontFamily: display, fontWeight: 800, fontSize: 16, color: C.tealDark }}>{k.namn}</span>
                      <span style={{ fontFamily: mono, fontSize: 12, color: C.slate }}>· {k.under}</span>
                      {on && <span style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".06em", color: C.teal, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 20, padding: "2px 9px" }}>ANVÄNDS HÄR</span>}
                    </div>
                    <div style={{ fontSize: 14, color: C.slate, lineHeight: 1.6 }}>{k.forklaring}</div>
                    <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${C.hair}` }}>
                      <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: ".08em", color: C.slate, marginBottom: 6 }}>VAR I REPOT</div>
                      <div style={{ fontFamily: mono, fontSize: 12.5, color: C.slate, fontStyle: "italic" }}>{k.note}</div>
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

          {/* Resultat: vad verktyget producerar */}
          <div style={{ marginTop: 26, background: C.tealTint, border: `1px solid ${C.tealLine}`, borderRadius: 14, padding: "20px 22px" }}>
            <div style={{ fontFamily: body, fontSize: 11, fontWeight: 600, letterSpacing: ".12em", color: C.tealDark, marginBottom: 10 }}>RESULTAT — REGEL I DEN EXPORTERADE ARTEFAKTEN</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 28px", alignItems: "baseline" }}>
              <div style={{ fontFamily: mono, fontSize: 17, fontWeight: 600, color: C.tealDark }}>{v.resultat.falt}</div>
              <div style={{ fontFamily: mono, fontSize: 15, color: C.ink }}>→ {v.resultat.varde}</div>
            </div>
            {v.resultat.extra && <div style={{ fontSize: 13.5, color: C.slate, marginTop: 8 }}>{v.resultat.extra}</div>}
          </div>
        </div>
      </div>
    );
  }

  window.kuComponents['MappningByggtVerktyg'] = Byggt;
})();
