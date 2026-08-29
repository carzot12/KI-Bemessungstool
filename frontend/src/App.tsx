import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import type { BridgeEnvelope, FormOptions, UISnapshot, Variant } from "./types";
import SideView from "./visualization/SideView";
import SectionView from "./visualization/SectionView";
import IsometricView from "./visualization/IsometricView";
import TopView from "./visualization/TopView";
import logoUrl from "../../assets/logo.png";

window.addEventListener("error", (event) => {
  console.error("Uncaught frontend error", event.error || event.message);
});
window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled frontend rejection", event.reason);
});

type View = "Seitenansicht" | "Draufsicht" | "Schnitt A-A" | "3D";
type Theme = "light" | "dark";

function Ring({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const dash = 2 * Math.PI * 42;
  return (
    <div className="ring">
      <svg viewBox="0 0 100 100">
        <circle className="ring-bg" cx="50" cy="50" r="42" />
        <circle
          className="ring-value"
          cx="50"
          cy="50"
          r="42"
          style={{
            strokeDasharray: dash,
            strokeDashoffset: dash * (1 - pct / 100),
          }}
        />
      </svg>
      <strong>η = {pct.toFixed(0)}%</strong>
    </div>
  );
}

function Header({
  snapshot,
  theme,
  onTheme,
  mode,
  onMode,
  onProjectName,
}: {
  snapshot: UISnapshot;
  theme: Theme;
  onTheme: (theme: Theme) => void;
  mode: string;
  onMode: (mode: string) => void;
  onProjectName: (name: string) => void;
}) {
  return (
    <header className="header">
      <div className="brand">
        <img src={logoUrl} alt="holz.bau forschungs gmbh" />
      </div>
      <div className="product">
        <h1>KI-Bemessungstool</h1>
        <p>KI-gestützte Bemessung von Holzbauverbindungen</p>
        <input aria-label="Projektname" value={snapshot.projectName || ""} placeholder="Projektname"
          onChange={(e) => onProjectName(e.target.value)}
          onBlur={(e) => void window.pywebview?.api.set_project_name({ project_name: e.target.value })} />
      </div>
      <nav className="mode-tabs">
        {["KI Workspace", "Kompakt", "Manuell"].map((label) => (
          <button
            key={label}
            className={mode === label ? "active" : ""}
            onClick={() => onMode(label)}
          >
            {label}
          </button>
        ))}
      </nav>
      <div className="header-meta">
        <span className="norm">
          NORMMODUS <b>ÖNORM</b>
        </span>
        <span className={`online ${snapshot.agentStatus.mode}`}>
          <i /> {snapshot.agentStatus.label}
        </span>
        <button
          className="theme-switch"
          onClick={() => onTheme(theme === "light" ? "dark" : "light")}
          aria-label="Farbschema wechseln"
        >
          <span className={theme === "light" ? "active" : ""}>☀</span>
          <span className={theme === "dark" ? "active" : ""}>☾</span>
        </button>
      </div>
    </header>
  );
}

function Sidebar({
  active,
  setActive,
}: {
  active: string;
  setActive: (v: string) => void;
}) {
  const items = ["Entwurf", "Varianten", "Nachweise", "Quellen", "Bericht"];
  return (
    <aside className="sidebar">
      <small className="sidebar-title">PROJEKT</small>
      <div className="side-nav">
        {items.map((label) => (
          <button
            key={label}
            className={active === label ? "active" : ""}
            onClick={() => setActive(label)}
          >
            <span>{active === label ? "●" : "○"}</span>
            {label}
          </button>
        ))}
      </div>
      <footer>
        Zuglaschenstoß
        <br />
        Stabdübel · Zug
      </footer>
    </aside>
  );
}

function Chat({
  snapshot,
  onSnapshot,
  onError,
}: {
  snapshot: UISnapshot;
  onSnapshot: (s: UISnapshot) => void;
  onError: (message: string) => void;
}) {
  const [text, setText] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [follow, setFollow] = useState(true);
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (follow)
      scroll.current?.scrollTo({
        top: scroll.current.scrollHeight,
        behavior: "smooth",
      });
  }, [snapshot.conversation, follow]);
  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    const value = text.trim();
    if (!value || isThinking) return;
    setText("");
    const optimisticSnapshot: UISnapshot = {
      ...snapshot,
      conversation: [
        ...snapshot.conversation,
        { role: "user", content: value },
      ],
    };
    onSnapshot(optimisticSnapshot);
    setIsThinking(true);
    setFollow(true);
    try {
      if (window.pywebview) {
        const response = await window.pywebview.api.send_message({
          text: value,
        });
        if (!response.ok || !response.data) {
          const message = response.error || "Die Anfrage konnte nicht verarbeitet werden.";
          onError(message);
          onSnapshot({
            ...optimisticSnapshot,
            conversation: [
              ...optimisticSnapshot.conversation,
              { role: "assistant", content: message },
            ],
          });
        } else onSnapshot(response.data);
      } else
        onSnapshot({
          ...optimisticSnapshot,
          conversation: [
            ...optimisticSnapshot.conversation,
            {
              role: "assistant",
              content:
                "Browser-Vorschau: Der echte Agent ist nur in der pywebview-Desktop-Shell verbunden.",
            },
          ],
        });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Python-Backend nicht verbunden.";
      onError(message);
      onSnapshot({
        ...optimisticSnapshot,
        conversation: [
          ...optimisticSnapshot.conversation,
          { role: "assistant", content: message },
        ],
      });
    } finally {
      setIsThinking(false);
    }
  };
  const key = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };
  const copy = async () => {
    const content = window.pywebview
      ? await window.pywebview.api.copy_chat_text()
      : snapshot.conversation
          .map(
            (m) => `${m.role === "user" ? "Sie" : "Assistent"}:\n${m.content}`,
          )
          .join("\n\n");
    await navigator.clipboard.writeText(content);
  };
  const selectProvider = async (provider: "local" | "openai") => {
    if (!window.pywebview || provider === snapshot.agentStatus.provider) return;
    const result = await window.pywebview.api.set_llm_provider({ provider });
    if (!result.ok || !result.data) onError(result.error || "KI-Modell konnte nicht gewechselt werden.");
    else onSnapshot(result.data);
  };
  return (
    <section className="chat card">
      <div className="card-head">
        <h2>
          <span className="spark">✦</span> KI-Assistent
        </h2>
        <div className="chat-head-actions">
          <div className="model-control" aria-label="KI-Modell auswählen">
            <span>KI-Modell</span>
            <div className="model-toggle">
              <button className={snapshot.agentStatus.provider === "local" ? "active" : ""} onClick={() => void selectProvider("local")}>Lokal</button>
              <button className={snapshot.agentStatus.provider === "openai" ? "active" : ""} onClick={() => void selectProvider("openai")}>OpenAI</button>
            </div>
            <small className={snapshot.agentStatus.available ? "available" : "unavailable"}>
              {snapshot.agentStatus.available ? "●" : "○"} {snapshot.agentStatus.detail}
              {snapshot.agentStatus.provider === "local" ? " · Daten bleiben auf diesem Gerät" : ""}
            </small>
          </div>
          <button onClick={copy}>Chat kopieren</button>
        </div>
      </div>
      <div
        className="messages"
        ref={scroll}
        onScroll={(e) => {
          const el = e.currentTarget;
          setFollow(el.scrollHeight - el.scrollTop - el.clientHeight < 70);
        }}
      >
        {snapshot.conversation.map((m, i) => (
          <article key={i} className={`message ${m.role}`}>
            <div className="avatar" aria-hidden="true">
              {m.role === "user" ? (
                <svg className="user-avatar-icon" viewBox="0 0 24 24">
                  <circle cx="12" cy="8" r="3.5" />
                  <path d="M5.5 19c.7-4 3-6 6.5-6s5.8 2 6.5 6" />
                </svg>
              ) : "✦"}
            </div>
            <div className="message-content">
              <small>{m.role === "user" ? "Sie" : "KI-Assistent"}</small>
              <p>{m.content}</p>
            </div>
          </article>
        ))}
        {isThinking && (
          <article className="message assistant">
            <div className="avatar">✦</div>
            <div className="message-content">
              <small>KI-Assistent</small>
              <div className="thinking" aria-label="KI-Assistent verarbeitet die Anfrage">
                <i />
                <i />
                <i />
              </div>
            </div>
          </article>
        )}
      </div>
      {!follow && (
        <button
          className="new-message"
          onClick={() => {
            setFollow(true);
            scroll.current?.scrollTo({
              top: scroll.current.scrollHeight,
              behavior: "smooth",
            });
          }}
        >
          ↓ Neue Nachricht
        </button>
      )}
      <form className="composer" onSubmit={send}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={key}
          placeholder="Frag den KI-Assistenten …"
        />
        <button aria-label="Senden" disabled={isThinking || !text.trim()}>➤</button>
        <small>Enter senden · Shift+Enter neue Zeile</small>
      </form>
    </section>
  );
}

function Visualizer({
  snapshot,
  modelOverride,
  previewActive = false,
}: {
  snapshot: UISnapshot;
  modelOverride?: UISnapshot["visualizationModel"];
  previewActive?: boolean;
}) {
  const [view, setView] = useState<View>("Seitenansicht");
  const [dimensions, setDimensions] = useState(true);
  const model = modelOverride || snapshot.connectionGeometry;
  return (
    <section className="visual card">
      <div className="card-head">
        <h2>
          Technische Darstellung{" "}
          {snapshot.demoMode && <em>DEMO-SNAPSHOT</em>}
          {previewActive && <em>VARIANTENVORSCHAU</em>}
        </h2>
        <label className="toggle">
          Maße{" "}
          <input
            type="checkbox"
            checked={dimensions}
            onChange={(e) => setDimensions(e.target.checked)}
          />
          <span />
        </label>
      </div>
      <div className="view-tabs">
        {(["Seitenansicht", "Draufsicht", "Schnitt A-A", "3D"] as View[]).map((v) => (
          <button
            className={view === v ? "active" : ""}
            onClick={() => setView(v)}
            key={v}
          >
            {v}
          </button>
        ))}
      </div>
      <div className="view-stage" key={view}>
        {model ? (
          view === "Seitenansicht" ? (
            <SideView model={model} dimensions={dimensions} />
          ) :           view === "Draufsicht" ? (
            <TopView model={model} dimensions={dimensions} />
          ) : view === "Schnitt A-A" ? (
            <SectionView model={model} dimensions={dimensions} />
          ) : (
            <IsometricView model={model} dimensions={dimensions} />
          )
        ) : (
          <p>Kein berechneter Entwurf vorhanden.</p>
        )}
      </div>
      {model && (
        <div className="visual-specs">
          <b>{previewActive ? "Vorschau Variante" : "Gewählte Variante / Favorit"}</b>
          <span>Holzquerschnitt {model.sectionWidthMm} × {model.sectionHeightMm} mm</span>
          <span>{model.plateCount} Stahlblech{model.plateCount === 1 ? "" : "e"} · ts {model.plateThicknessMm} mm · t1 {model.sideThicknessMm} mm{model.plateCount === 2 ? ` · t2 ${model.middleThicknessMm} mm` : ""}</span>
          <span>Stabdübel Ø{model.dowelDiameterMm} mm · {model.rowsParallel} × {model.rowsPerpendicular} · {model.rowsParallel * model.rowsPerpendicular} je Stoßseite</span>
          <span>a1 {model.a1Mm} · a2 {model.a2Mm} · a3,t {model.a3tMm} · a4,c {model.a4cMm} · e1 {model.e1Mm} · e2 {model.e2Mm} mm</span>
        </div>
      )}
    </section>
  );
}

const value = (input: Record<string, unknown>, ...keys: string[]) => {
  for (const key of keys)
    if (input[key] !== undefined && input[key] !== null)
      return String(input[key]);
  return "—";
};

function BestSolution({ snapshot }: { snapshot: UISnapshot }) {
  const recommendation = snapshot.recommendedVariant;
  if (!recommendation)
    return (
      <section className="solution card empty-result">
        <h2>BESTE LÖSUNG</h2>
        <p>Noch keine Berechnung vorhanden.</p>
      </section>
    );
  const input = recommendation.input;
  const m = recommendation.connectionGeometry;
  const rows = [
    ["Anschlussaufbau", `${m.plateCount} innenliegende Stahlbleche`],
    ["Blechdicke", `${m.plateThicknessMm} mm`],
    [
      "Holzaufteilung",
      `t1 = ${m.sideThicknessMm} mm · t2 = ${m.middleThicknessMm} mm`,
    ],
    ["Stabdübeldurchmesser", `Ø${m.dowelDiameterMm} mm`],
    [
      "Dübelanordnung",
      `${m.rowsParallel} × ${m.rowsPerpendicular} = ${m.rowsParallel * m.rowsPerpendicular}`,
    ],
    ["Holzklasse", value(input, "timber_grade")],
    ["Nutzungsklasse", value(input, "service_class")],
    ["Lasteinwirkungsdauer", value(input, "load_duration_class")],
    ["kmod", value(input, "k_mod")],
  ];
  const fulfilled = recommendation.passed && recommendation.normAdmissible;
  const stats = snapshot.lastOptimization;
  return (
    <section className="solution card result-flash">
      <div className="solution-title">
        <span>🏅</span>
        <b>BESTE LÖSUNG</b>
        <em>(berechneter Snapshot)</em>
      </div>
      <div className={`proof ${fulfilled ? "pass" : "fail"}`}>
        {fulfilled ? "✓ NACHWEIS ERFÜLLT" : "✕ NACHWEIS NICHT ERFÜLLT"}
      </div>
      <div className="solution-body">
        <dl>
          {rows.map(([label, v]) => (
            <div key={label}>
              <dt>✓ {label}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <div className="eta">
          <Ring value={recommendation.utilization} />
          <p>
            Maßgebend:
            <br />
            <b>{recommendation.governingCheck}</b>
          </p>
        </div>
      </div>
      {stats && (
        <div className="optimization-stats">
          <span>Varianten untersucht: <b>{stats.evaluatedCount.toLocaleString("de-DE")}</b></span>
          <span>davon geeignet: <b>{stats.feasibleCount.toLocaleString("de-DE")}</b></span>
          <span>Entwurfsziel: <b>{stats.objective || "ausgewogene Empfehlung"}</b></span>
        </div>
      )}
    </section>
  );
}

function Variants({
  snapshot,
  selected,
  onPreview,
  onAdopt,
}: {
  snapshot: UISnapshot;
  selected: Variant | null;
  onPreview: (variant: Variant) => void;
  onAdopt: (variant: Variant) => void;
}) {
  return (
    <section className="variants card">
      <div className="card-head">
        <h2>WEITERE VARIANTEN</h2>
        <button onClick={() => document.querySelector<HTMLElement>(".sidebar button:nth-child(2)")?.click()}>Alle Varianten</button>
      </div>
      <div className="variant-list">
        {!snapshot.variants.length && <p>Noch keine Varianten berechnet.</p>}
        {snapshot.variants.slice(0, 3).map((v, i) => (
          <article
            key={v.id}
            className={`${selected?.id === v.id ? "selected" : ""} ${!v.passed || !v.normAdmissible ? "inadmissible" : ""}`}
            tabIndex={0}
            onClick={() => onPreview(v)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onPreview(v);
            }}
            style={{ animationDelay: `${i * 70}ms` }}
          >
            <div className="variant-id">{String.fromCharCode(65 + i)}</div>
            <div>
              <b>{i === 0 ? "KI-EMPFEHLUNG" : v.label}</b>
              <p>
                {v.plateCount} Blech{v.plateCount === 1 ? "" : "e"} · ts {v.plateThicknessMm} mm · Ø{v.diameterMm} · {v.rowsParallel} × {v.rowsPerpendicular}
              </p>
              <small>
                {v.fastenerCount} Stabdübel je Stoßseite · maßgebend: {v.governingCheck}<br />
                {v.interestReason}{" "}
                {!v.normAdmissible && "· nicht zulässig"}
              </small>
            </div>
            <span>η = {(v.utilization * 100).toFixed(0)}%</span>
          </article>
        ))}
      </div>
      <div className="variant-actions">
        <span>
          {selected ? "Vorschau aktiv" : "Variante für Vorschau wählen"}
        </span>
        <button
          disabled={!selected}
          onClick={() => selected && onAdopt(selected)}
        >
          Als Favorit übernehmen
        </button>
      </div>
    </section>
  );
}

function VariantWorkspace({
  snapshot,
  preview,
  onPreview,
  onAskAi,
  onAdopt,
}: {
  snapshot: UISnapshot;
  preview: Variant | null;
  onPreview: (variant: Variant) => void;
  onAskAi: () => void;
  onAdopt: (variant: Variant) => void;
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [showComparison, setShowComparison] = useState(false);
  const [reportIds, setReportIds] = useState<string[]>(
    snapshot.reportVariantIds?.length
      ? snapshot.reportVariantIds
      : snapshot.variants.length ? [snapshot.variants[0].id] : [],
  );
  const selected = snapshot.variants.filter((v) => selectedIds.includes(v.id));
  const toggle = (id: string) => {
    const next = reportIds.includes(id)
      ? reportIds.filter((item) => item !== id)
      : [...reportIds, id];
    setReportIds(next);
    if (window.pywebview) {
      void window.pywebview.api.set_report_selection({ variant_ids: next });
    }
  };
  return (
    <section className="section-workspace variants-workspace">
      <div className="section-head">
        <div><h1>Varianten</h1><p>Kuratierte, tatsächlich berechnete Lösungen</p></div>
        <div className="section-actions">
          <button disabled={selected.length < 2} onClick={() => setShowComparison(true)}>VARIANTEN VERGLEICHEN</button>
          <button disabled={!selected.length} onClick={onAskAi}>KI BEWERTEN LASSEN</button>
        </div>
      </div>
      {!snapshot.variants.length ? (
        <div className="card section-empty">Noch keine Varianten berechnet.</div>
      ) : (
        <>
          <div className="variant-catalog">
            {snapshot.variants.map((v) => (
              <article className="card" key={v.id} onClick={() => onPreview(v)}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(v.id)}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => setSelectedIds((ids) =>
                    ids.includes(v.id) ? ids.filter((item) => item !== v.id) : [...ids, v.id],
                  )}
                  aria-label={`${v.label} auswählen`}
                />
                <label onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={reportIds.includes(v.id)} onChange={() => toggle(v.id)} /> Im Bericht aufnehmen</label>
                <div><h2>{v.label}{snapshot.currentVariant?.id === v.id ? " · FAVORIT" : ""}</h2><p>{v.plateCount} Blech(e) · ts {v.plateThicknessMm} mm · Ø{v.diameterMm} mm</p></div>
                <dl>
                  <div><dt>Anordnung</dt><dd>{v.rowsParallel} × {v.rowsPerpendicular} = {v.fastenerCount}</dd></div>
                  <div><dt>Ausnutzung</dt><dd>{(v.utilization * 100).toFixed(0)} %</dd></div>
                  <div><dt>Reserve</dt><dd>{(v.reserve * 100).toFixed(0)} %</dd></div>
                  <div><dt>Maßgebend</dt><dd>{v.governingCheck}</dd></div>
                  <div><dt>Einordnung</dt><dd>{v.interestReason}</dd></div>
                </dl>
                <strong className={v.passed && v.normAdmissible ? "status-ok" : "status-bad"}>
                  {v.passed && v.normAdmissible ? "✓ zulässig und erfüllt" : "✕ nicht zulässig/erfüllt"}
                </strong>
              </article>
            ))}
          </div>
          {preview && (
            <div className="card variant-detail">
              <h2>VARIANTENVORSCHAU · {preview.label}</h2>
              <p>
                {preview.plateCount} Blech(e) · ts {preview.plateThicknessMm} mm · Ø{preview.diameterMm} mm · {preview.rowsParallel} × {preview.rowsPerpendicular} = {preview.fastenerCount} Stabdübel
              </p>
              <p>η = {(preview.utilization * 100).toFixed(1)} % · Reserve {(preview.reserve * 100).toFixed(1)} % · maßgebend: {preview.governingCheck}</p>
              <button onClick={() => onAdopt(preview)}>Als Favorit übernehmen</button>
            </div>
          )}
          {showComparison && selected.length > 1 && (
            <div className="card comparison">
              <h2>VARIANTENVERGLEICH</h2>
              <div className="comparison-scroll"><table><thead><tr>
                <th>Variante</th><th>Bleche</th><th>ts</th><th>Ø</th><th>Anordnung</th><th>Anzahl</th><th>η</th><th>Reserve</th><th>Maßgebend</th><th>Status</th>
              </tr></thead><tbody>{selected.map((v) => <tr key={v.id}>
                <td>{v.label}</td><td>{v.plateCount}</td><td>{v.plateThicknessMm} mm</td><td>{v.diameterMm} mm</td><td>{v.rowsParallel} × {v.rowsPerpendicular}</td><td>{v.fastenerCount}</td><td>{(v.utilization * 100).toFixed(0)} %</td><td>{(v.reserve * 100).toFixed(0)} %</td><td>{v.governingCheck}</td><td>{v.passed && v.normAdmissible ? "erfüllt" : "nicht erfüllt"}</td>
              </tr>)}</tbody></table></div>
              <h2>KI-EINSCHÄTZUNG</h2><p>{snapshot.recommendation}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function SourcesWorkspace({ snapshot }: { snapshot: UISnapshot }) {
  return (
    <section className="section-workspace">
      <div className="section-head"><div><h1>Quellen</h1><p>Für den aktuellen Entwurf verwendete Referenzen</p></div></div>
      <div className="card source-list">
        {snapshot.sources.length ? snapshot.sources.map((source) => <p key={source}>{source}</p>) : <p>Noch keine berechnungsspezifischen Quellen vorhanden.</p>}
      </div>
    </section>
  );
}

function ChecksWorkspace({ snapshot }: { snapshot: UISnapshot }) {
  const result = snapshot.currentResult;
  const checks = (result?.checks || []) as Array<{ name: string; resistance_kn: number; utilization: number; passed: boolean }>;
  return <section className="section-workspace"><div className="section-head"><div><h1>Nachweise</h1><p>Deterministische Ergebnisse der aktuellen Variante</p></div></div>
    <div className="card"><table><thead><tr><th>Nachweis</th><th>Einwirkung</th><th>Widerstand</th><th>Ausnutzung</th><th>Status</th></tr></thead>
      <tbody>{checks.length ? checks.map((item) => {
        return <tr key={item.name} className={item.name === result?.governingCheck ? "governing" : ""}><td>{item.name}</td><td>Ft,d</td><td>{item.resistance_kn.toFixed(2)} kN</td><td>{(item.utilization * 100).toFixed(1)} %</td><td>{item.passed ? "erfüllt" : "nicht erfüllt"}</td></tr>;
      }) : <tr><td colSpan={5}>Noch keine Berechnung vorhanden.</td></tr>}</tbody></table></div>
  </section>;
}

function ReportWorkspace({
  snapshot,
  onReport,
}: {
  snapshot: UISnapshot;
  onReport: (type: "calculation" | "variants") => void;
}) {
  return (
    <section className="section-workspace">
      <div className="section-head"><div><h1>Bericht</h1><p>Nachvollziehbare Ausgabe der berechneten Ergebnisse</p></div></div>
      <div className="report-grid">
        <article className="card"><h2>Berechnungsbericht</h2><p>Gewählte Variante, Eingaben, Nachweise, Status und Quellen.</p><button disabled={!snapshot.currentResult} onClick={() => onReport("calculation")}>PDF ERSTELLEN</button></article>
        <article className="card"><h2>Variantenbericht</h2><p>Kuratierte Varianten, Vergleich und gekennzeichnete KI-Einschätzung.</p><button disabled={!snapshot.variants.length} onClick={() => onReport("variants")}>PDF ERSTELLEN</button></article>
      </div>
      {snapshot.currentResult && <div className="card report-assessment"><h2>KI-EINSCHÄTZUNG</h2><p>{snapshot.recommendation}</p></div>}
    </section>
  );
}

const manualFields = [
  ["project_name", "Projektname", "text"],
  ["force_ed_kn", "Bemessungslast Ft,d [kN]", "number"],
  ["width_b_mm", "Breite b [mm]", "number"],
  ["height_h_mm", "Höhe h [mm]", "number"],
  ["number_of_plates_ns", "Anzahl Stahlbleche", "number"],
  ["plate_thickness_ts_mm", "Blechdicke ts [mm]", "number"],
  ["side_thickness_t1_mm", "Seitenholz t1 [mm]", "number"],
  ["middle_thickness_t2_mm", "Mittelholz t2 [mm]", "number"],
  ["slot_air_per_cut_ts_l_mm", "Schlitz-/Luftwert ts,L [mm]", "number"],
  ["dowel_diameter_d_mm", "Stabdübel d [mm]", "number"],
  ["dowel_length_l_mm", "Stabdübellänge l [mm]", "number"],
  ["hole_diameter_d0_mm", "Lochdurchmesser d0 [mm]", "number"],
  ["rows_parallel_n", "Reihen parallel n", "number"],
  ["rows_perpendicular_m", "Reihen quer m", "number"],
  ["a1_mm", "Abstand a1 [mm]", "number"],
  ["a2_mm", "Abstand a2 [mm]", "number"],
  ["a3_t_mm", "Endabstand a3,t [mm]", "number"],
  ["a4_c_mm", "Randabstand a4,c [mm]", "number"],
  ["e1_mm", "Stahlrandabstand e1 [mm]", "number"],
  ["e2_mm", "Stahlrandabstand e2 [mm]", "number"],
  ["kt_e_side", "kt,e Seitenholz [-]", "number"],
] as const;

function ResultSummary({ snapshot }: { snapshot: UISnapshot }) {
  const result = snapshot.currentResult;
  if (!result)
    return (
      <section className="form-result card">
        <h2>Berechnungsergebnis</h2>
        <p>Noch kein Ergebnis.</p>
      </section>
    );
  return (
    <section
      className={`form-result card ${result.passed && result.normAdmissible ? "result-ok" : "result-bad"}`}
    >
      <h2>
        {result.passed && result.normAdmissible
          ? "✓ NACHWEIS ERFÜLLT"
          : "✕ NACHWEIS NICHT ERFÜLLT"}
      </h2>
      <strong>η = {(result.utilization * 100).toFixed(0)} %</strong>
      <p>Maßgebend: {result.governingCheck}</p>
    </section>
  );
}

function CompactView({
  snapshot,
  options,
  onSnapshot,
}: {
  snapshot: UISnapshot;
  options: FormOptions;
  onSnapshot: (s: UISnapshot) => void;
}) {
  const input = snapshot.currentResult?.input || snapshot.technicalState;
  const [form, setForm] = useState<Record<string, string>>(() => ({
    project_name: String(input.project_name ?? ""),
    force_ed_kn: String(input.force_ed_kn ?? ""),
    timber_grade: String(input.timber_grade ?? ""),
    width_b_mm: String(input.width_b_mm ?? ""),
    height_h_mm: String(input.height_h_mm ?? ""),
    service_class: String(input.service_class ?? ""),
    load_duration_class: String(input.load_duration_class ?? ""),
    objective: "",
  }));
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setForm((current) => ({
      ...current,
      force_ed_kn: String(input.force_ed_kn ?? ""),
      project_name: String(input.project_name ?? ""),
      timber_grade: String(input.timber_grade ?? ""),
      width_b_mm: String(input.width_b_mm ?? ""),
      height_h_mm: String(input.height_h_mm ?? ""),
      service_class: String(input.service_class ?? ""),
      load_duration_class: String(input.load_duration_class ?? ""),
      objective: Object.keys(input).length ? current.objective : "",
    }));
  }, [input.force_ed_kn, input.timber_grade, input.width_b_mm,
      input.height_h_mm, input.service_class, input.load_duration_class]);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!window.pywebview) { window.alert("Python-Backend nicht verbunden."); return; }
    setBusy(true);
    try {
      const r = await window.pywebview.api.compact_calculate(form);
      if (!r.ok || !r.data) window.alert(r.error || "Die Berechnung konnte nicht durchgeführt werden.");
      else onSnapshot(r.data);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="form-workspace compact-view">
      <form className="entry-card card" onSubmit={submit}>
        <h1>Zuglaschenstoß</h1>
        <p>Schnelle KI-gestützte Vorbemessung</p>
        <label>
          Projektname
          <input value={form.project_name} onChange={(e) => set("project_name", e.target.value)} />
        </label>
        <label>
          Bemessungslast Ft,d [kN]
          <input
            type="number"
            required
            value={form.force_ed_kn}
            onChange={(e) => set("force_ed_kn", e.target.value)}
          />
        </label>
        <label>
          Holzklasse
          <select
            required
            value={form.timber_grade}
            onChange={(e) => set("timber_grade", e.target.value)}
          >
            <option value="">Bitte auswählen</option>
            {options.timberGrades.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <div className="field-pair">
          <label>
            Breite b [mm]
            <input
              type="number"
              required
              value={form.width_b_mm}
              onChange={(e) => set("width_b_mm", e.target.value)}
            />
          </label>
          <label>
            Höhe h [mm]
            <input
              type="number"
              required
              value={form.height_h_mm}
              onChange={(e) => set("height_h_mm", e.target.value)}
            />
          </label>
        </div>
        <label>
          Nutzungsklasse
          <select
            required
            value={form.service_class}
            onChange={(e) => set("service_class", e.target.value)}
          >
            <option value="">Bitte auswählen</option>
            {["1", "2", "3"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Lasteinwirkungsdauer
          <select
            required
            value={form.load_duration_class}
            onChange={(e) => set("load_duration_class", e.target.value)}
          >
            <option value="">Bitte auswählen</option>
            {options.loadDurations.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Entwurfsziel
          <select
            required
            value={form.objective}
            onChange={(e) => set("objective", e.target.value)}
          >
            <option value="">Bitte auswählen</option>
            <option value="BALANCED_DESIGN">Empfehlung / wirtschaftlich</option>
            <option value="MIN_FASTENER_COUNT">wenig Stabdübel</option>
            <option value="LOWER_UTILIZATION">mehr Reserve</option>
            <option value="COMPACT_GEOMETRY">kompakte Geometrie</option>
            <option value="MAXIMIZE_UTILIZATION">maximal ausnutzen</option>
            <option value="CUSTOM">Benutzerdefiniert</option>
          </select>
        </label>
        <button className="primary-action" disabled={busy}>
          {busy ? "BEMESSUNG LÄUFT …" : "BEMESSUNG STARTEN"}
        </button>
      </form>
      <div className="form-output">
        <Visualizer snapshot={snapshot} />
        <ResultSummary snapshot={snapshot} />
      </div>
    </main>
  );
}

function ManualView({
  snapshot,
  options,
  onSnapshot,
  onOptimize,
}: {
  snapshot: UISnapshot;
  options: FormOptions;
  onSnapshot: (s: UISnapshot) => void;
  onOptimize: () => void;
}) {
  const source = {
    ...snapshot.technicalState,
    ...(snapshot.currentResult?.input || {}),
  };
  const [form, setForm] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(source).map(([k, v]) => [k, String(v)])),
  );
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  useEffect(() => {
    const next = {
      ...snapshot.technicalState,
      ...(snapshot.currentResult?.input || {}),
    };
    setForm(
      Object.fromEntries(Object.entries(next).map(([k, v]) => [k, String(v)])),
    );
  }, [snapshot.currentResult, snapshot.technicalState, options.manualDefaults]);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!window.pywebview) { window.alert("Python-Backend nicht verbunden."); return; }
    setBusy(true);
    try {
      const numeric = new Set<string>(
        manualFields.filter((x) => x[2] === "number").map((x) => x[0]),
      );
      const payload: Record<string, string | number> = {};
      for (const [key] of manualFields)
        payload[key] = numeric.has(key) ? Number(form[key]) : form[key];
      payload.timber_grade = form.timber_grade;
      payload.service_class = Number(form.service_class);
      payload.load_duration_class = form.load_duration_class;
      const r = await window.pywebview.api.manual_calculate(payload);
      if (!r.ok || !r.data) window.alert(r.error || "Der Nachweis konnte nicht berechnet werden.");
      else onSnapshot(r.data);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="form-workspace manual-view">
      <form className="entry-card card manual-form" onSubmit={submit}>
        <div className="form-title-row">
          <div><h1>Eingabedaten</h1><p>Vollständige manuelle Bemessung</p></div>
          <button
            type="button"
            onClick={async () => {
              if (!window.pywebview) { window.alert("Python-Backend nicht verbunden."); return; }
              try {
                const example = await window.pywebview.api.manual_example();
                if (!example.ok) window.alert(example.error || "Beispieldaten konnten nicht geladen werden.");
                else setForm(Object.fromEntries(Object.entries(example.data).map(([k, v]) => [k, String(v)])));
              } catch (error) {
                window.alert(error instanceof Error ? error.message : "Beispieldaten konnten nicht geladen werden.");
              }
            }}
          >
            BEISPIEL LADEN
          </button>
        </div>
        <div className="manual-grid">
          <label>
            Holzfestigkeitsklasse
            <select
              required
              value={form.timber_grade}
              onChange={(e) => set("timber_grade", e.target.value)}
            >
              <option value="">Bitte auswählen</option>
              {options.timberGrades.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Nutzungsklasse
            <select
              required
              value={form.service_class}
              onChange={(e) => set("service_class", e.target.value)}
            >
              <option value="">Bitte auswählen</option>
              {["1", "2", "3"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Lasteinwirkungsdauer
            <select
              required
              value={form.load_duration_class}
              onChange={(e) => set("load_duration_class", e.target.value)}
            >
              <option value="">Bitte auswählen</option>
              {options.loadDurations.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          {manualFields.map(([key, label, type]) => (
            <label key={key}>
              {label}
              <input
                type={type}
                step="any"
                required
                value={form[key] ?? ""}
                onChange={(e) => set(key, e.target.value)}
              />
            </label>
          ))}
        </div>
        <button className="primary-action" disabled={busy}>
          {busy ? "BERECHNUNG LÄUFT …" : "NACHWEIS BERECHNEN"}
        </button>
        {snapshot.currentResult && (
          <button type="button" onClick={onOptimize} disabled={busy}>
            KI OPTIMIEREN LASSEN
          </button>
        )}
      </form>
      <div className="form-output">
        <Visualizer snapshot={snapshot} />
        <ResultSummary snapshot={snapshot} />
      </div>
    </main>
  );
}

function App() {
  const [snapshot, setSnapshot] = useState<UISnapshot | null>(null);
  const [active, setActive] = useState("Entwurf");
  const [selected, setSelected] = useState<Variant | null>(null);
  const [mode, setMode] = useState("KI Workspace");
  const [error, setError] = useState<string | null>(null);
  const [lastPdf, setLastPdf] = useState<string | null>(null);
  const [options, setOptions] = useState<FormOptions | null>(null);
  const [theme, setTheme] = useState<Theme>(() => {
    const initialTheme =
      localStorage.getItem("ki-tool-theme") === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = initialTheme;
    return initialTheme;
  });
  const updateSnapshot = (next: UISnapshot) => {
    setSnapshot(next);
    setSelected(null);
  };
  const resetDesign = async () => {
    if (!window.pywebview) { setError("Python-Backend nicht verbunden."); return; }
    if (!window.confirm("Neuen Entwurf starten?")) return;
    const result = await window.pywebview.api.reset_design();
    if (!result.ok || !result.data) setError(result.error || "Neuer Entwurf konnte nicht gestartet werden.");
    else { updateSnapshot(result.data); setActive("Entwurf"); setLastPdf(null); }
  };
  const createReport = async (type: "calculation" | "variants") => {
    if (!window.pywebview) { setError("Python-Backend nicht verbunden."); return; }
    try {
      const result = await window.pywebview.api.create_pdf_report({ type });
      if (result.status === "cancelled") return;
      if (result.status === "error") setError(result.message || "Der Bericht konnte nicht erstellt werden.");
      else if (result.path) { setError(null); setLastPdf(result.path); }
    } catch (e) { setError(e instanceof Error ? e.message : "Der Bericht konnte nicht erstellt werden."); }
  };
  const adoptVariant = async (variant: Variant) => {
    if (!window.pywebview) { setError("Python-Backend nicht verbunden."); return; }
    const result = await window.pywebview.api.adopt_variant({ variant_id: variant.id });
    if (!result.ok || !result.data) setError(result.error || "Variante konnte nicht übernommen werden.");
    else updateSnapshot(result.data);
  };
  const askVariantAssessment = async () => {
    if (!window.pywebview) { setError("Python-Backend nicht verbunden."); return; }
    try {
      const result = await window.pywebview.api.send_message({
        text: "Bewerte die aktuell angezeigten berechneten Varianten und empfehle mir eine davon kurz.",
      });
      if (!result.ok || !result.data) setError(result.error || "Die Variantenbewertung ist fehlgeschlagen.");
      else updateSnapshot(result.data);
    } catch (error) { setError(error instanceof Error ? error.message : "Die Variantenbewertung ist fehlgeschlagen."); }
  };
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("ki-tool-theme", theme);
  }, [theme]);
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        let result: BridgeEnvelope;
        if (window.pywebview) result = await window.pywebview.api.bootstrap();
        else if (
          location.protocol === "http:" ||
          location.protocol === "https:"
        )
          result = await fetch("./demo-snapshot.json").then((r) => r.json());
        else return false;
        if (!cancelled) {
          const data = {
            ...result.data,
            projectName: result.data.projectName || String(result.data.currentResult?.input?.project_name || ""),
            reportVariantIds: result.data.reportVariantIds || [],
            variants: result.data.variants || [],
            sources: result.data.sources || [],
            conversation: result.data.conversation || [],
          };
          setSnapshot(data);
          if (window.pywebview)
            setOptions(await window.pywebview.api.form_options());
          else
            setOptions({
              timberGrades: ["GL24h"],
              loadDurations: ["ständig", "lang", "mittel", "kurz", "sehr kurz"],
              manualDefaults: (result.data.currentResult?.input || {}) as Record<string, string | number>,
            });
        }
        return true;
      } catch (error) {
        console.error("Workspace bootstrap failed", error);
        return false;
      }
    };
    void load();
    const ready = () => {
      void load();
    };
    window.addEventListener("pywebviewready", ready);
    const poll = window.setInterval(() => {
      if (window.pywebview) {
        window.clearInterval(poll);
        void load();
      }
    }, 50);
    const stop = window.setTimeout(() => window.clearInterval(poll), 10000);
    return () => {
      cancelled = true;
      window.clearInterval(poll);
      window.clearTimeout(stop);
      window.removeEventListener("pywebviewready", ready);
    };
  }, []);
  useEffect(() => {
    if (snapshot && options) {
      (window as Window & { __KI_APP_READY__?: boolean }).__KI_APP_READY__ = true;
    }
  }, [snapshot, options]);
  if (!snapshot)
    return (
      <main className="loading" aria-label="Anwendung wird initialisiert">
        <span>Initialisierung …</span>
      </main>
    );
  return (
    <div className="app">
      <Header
        snapshot={snapshot}
        theme={theme}
        onTheme={setTheme}
        mode={mode}
        onMode={setMode}
        onProjectName={(name) =>
          setSnapshot((current) => current ? { ...current, projectName: name } : current)
        }
      />
      <Sidebar active={active} setActive={setActive} />
      {mode === "KI Workspace" && (
        <>
          {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError(null)}>Schließen</button></div>}
          {lastPdf && <div className="success-banner">PDF erstellt: {lastPdf} <button onClick={() => window.pywebview?.api.open_report({ path: lastPdf })}>PDF ÖFFNEN</button><button onClick={() => window.pywebview?.api.reveal_report({ path: lastPdf })}>IM FINDER ZEIGEN</button></div>}
          <Chat
            snapshot={snapshot}
            onSnapshot={updateSnapshot}
            onError={setError}
          />
          {active === "Nachweise" && <ChecksWorkspace snapshot={snapshot} />}
          {active === "Entwurf" && <main className="workspace">
            <Visualizer
              snapshot={snapshot}
              modelOverride={selected?.connectionGeometry}
              previewActive={Boolean(selected)}
            />
            <div className="results-grid">
              <BestSolution snapshot={snapshot} />
              <Variants
                snapshot={snapshot}
                selected={selected}
                onPreview={setSelected}
                onAdopt={adoptVariant}
              />
              <section className="why card">
                <h2>KI-EINSCHÄTZUNG</h2>
                <p>{snapshot.recommendation}</p>
              </section>
              <section className="sources card">
                <h2>QUELLEN</h2>
                {snapshot.sources.length ? snapshot.sources.slice(0, 3).map((source) => <p key={source}>{source}</p>) : <p>Noch keine berechnungsspezifischen Quellen.</p>}
              </section>
            </div>
          </main>}
          {active === "Varianten" && <VariantWorkspace snapshot={snapshot} preview={selected} onPreview={setSelected} onAskAi={askVariantAssessment} onAdopt={adoptVariant} />}
          {active === "Quellen" && <SourcesWorkspace snapshot={snapshot} />}
          {active === "Bericht" && <ReportWorkspace snapshot={snapshot} onReport={createReport} />}
        </>
      )}
      {mode === "Kompakt" && options && (
        <CompactView
          snapshot={snapshot}
          options={options}
          onSnapshot={updateSnapshot}
        />
      )}
      {mode === "Manuell" && options && (
        <ManualView
          snapshot={snapshot}
          options={options}
          onSnapshot={updateSnapshot}
          onOptimize={async () => {
            if (!window.pywebview) { setError("Python-Backend nicht verbunden."); return; }
            const result = await window.pywebview.api.send_message({
              text: "Optimiere den aktuellen manuellen Entwurf.",
            });
            if (!result.ok || !result.data) setError(result.error || "Die Optimierung ist fehlgeschlagen.");
            else updateSnapshot(result.data);
          }}
        />
      )}
      <div className="bottom">
        <span>
          ● Speicherstatus <b>lokal</b>
        </span>
        <span>
          ◷ Letzter Snapshot <b>aktuell</b>
        </span>
        <span>
          ● Engineering-Kern <b>aktiv</b>
        </span>
        <button className="reset-action" onClick={resetDesign}>Neuer Entwurf</button>
        <button disabled={!snapshot.currentResult} onClick={() => createReport("calculation")}>PDF-Bericht erstellen</button>
      </div>
    </div>
  );
}

export default App;
