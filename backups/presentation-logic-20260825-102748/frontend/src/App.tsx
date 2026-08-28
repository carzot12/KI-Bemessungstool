import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import type { BridgeEnvelope, FormOptions, UISnapshot, Variant } from "./types";
import SideView from "./visualization/SideView";
import SectionView from "./visualization/SectionView";
import IsometricView from "./visualization/IsometricView";
import logoUrl from "../../assets/logo.png";

type View = "Seitenansicht" | "Querschnitt" | "3D";
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
}: {
  snapshot: UISnapshot;
  theme: Theme;
  onTheme: (theme: Theme) => void;
  mode: string;
  onMode: (mode: string) => void;
}) {
  return (
    <header className="header">
      <div className="brand">
        <img src={logoUrl} alt="holz.bau forschungs gmbh" />
      </div>
      <div className="product">
        <h1>KI-Bemessungstool</h1>
        <p>KI-gestützte Bemessung von Holzbauverbindungen</p>
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
}: {
  snapshot: UISnapshot;
  onSnapshot: (s: UISnapshot) => void;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
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
    if (!value || busy) return;
    setText("");
    setBusy(true);
    setFollow(true);
    try {
      if (window.pywebview) {
        const response = await window.pywebview.api.send_message({
          text: value,
        });
        onSnapshot(response.data);
      } else
        onSnapshot({
          ...snapshot,
          conversation: [
            ...snapshot.conversation,
            { role: "user", content: value },
            {
              role: "assistant",
              content:
                "Browser-Vorschau: Der echte Agent ist nur in der pywebview-Desktop-Shell verbunden.",
            },
          ],
        });
    } finally {
      setBusy(false);
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
  return (
    <section className="chat card">
      <div className="card-head">
        <h2>
          <span className="spark">✦</span> KI-Assistent
        </h2>
        <button onClick={copy}>Chat kopieren</button>
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
            <div className="avatar">{m.role === "user" ? "CZ" : "✦"}</div>
            <div>
              <small>{m.role === "user" ? "Sie" : "KI-Assistent"}</small>
              <p>{m.content}</p>
            </div>
          </article>
        ))}
        {busy && (
          <article className="message assistant">
            <div className="avatar">✦</div>
            <div className="thinking">
              <i />
              <i />
              <i /> Analysiere Anfrage …
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
        <button aria-label="Senden">➤</button>
        <small>Enter senden · Shift+Enter neue Zeile</small>
      </form>
    </section>
  );
}

function Visualizer({
  snapshot,
  modelOverride,
}: {
  snapshot: UISnapshot;
  modelOverride?: UISnapshot["visualizationModel"];
}) {
  const [view, setView] = useState<View>("Seitenansicht");
  const [dimensions, setDimensions] = useState(true);
  const model = modelOverride || snapshot.visualizationModel;
  return (
    <section className="visual card">
      <div className="card-head">
        <h2>
          Technische Live-Visualisierung{" "}
          {snapshot.demoMode && <em>DEMO-SNAPSHOT</em>}
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
        {(["3D", "Seitenansicht", "Querschnitt"] as View[]).map((v) => (
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
          ) : view === "Querschnitt" ? (
            <SectionView model={model} dimensions={dimensions} />
          ) : (
            <IsometricView model={model} />
          )
        ) : (
          <p>Kein berechneter Entwurf vorhanden.</p>
        )}
      </div>
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
  const r = snapshot.currentResult,
    m = snapshot.visualizationModel;
  if (!r || !m) return null;
  const input = r.input;
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
  const fulfilled = r.passed && r.normAdmissible;
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
          <Ring value={r.utilization} />
          <p>
            Maßgebend:
            <br />
            <b>{r.governingCheck}</b>
          </p>
        </div>
      </div>
    </section>
  );
}

function Variants({
  snapshot,
  selected,
  onPreview,
}: {
  snapshot: UISnapshot;
  selected: Variant | null;
  onPreview: (variant: Variant) => void;
}) {
  return (
    <section className="variants card">
      <div className="card-head">
        <h2>WEITERE VARIANTEN</h2>
        <button>Alle Varianten</button>
      </div>
      <div className="variant-list">
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
              <b>{i === 0 ? "Beste Lösung" : v.label}</b>
              <p>
                Ø{v.diameterMm} · {v.rowsParallel} × {v.rowsPerpendicular}
              </p>
              <small>
                {v.fastenerCount} Stabdübel{" "}
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
          disabled
          title="Eine technische Übernahme benötigt eine freigegebene Python-Bridge-Mutation."
        >
          Übernehmen
        </button>
      </div>
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
  const input =
    snapshot.currentResult?.input ||
    snapshot.technicalState ||
    options.manualDefaults;
  const [form, setForm] = useState<Record<string, string>>(() => ({
    force_ed_kn: String(input.force_ed_kn ?? 140),
    timber_grade: String(input.timber_grade ?? "GL24h"),
    width_b_mm: String(input.width_b_mm ?? 200),
    height_h_mm: String(input.height_h_mm ?? 240),
    service_class: String(input.service_class ?? 1),
    load_duration_class: String(input.load_duration_class ?? "mittel"),
    objective: "BALANCED_DESIGN",
  }));
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setForm((current) => ({
      ...current,
      force_ed_kn: String(input.force_ed_kn ?? current.force_ed_kn),
      timber_grade: String(input.timber_grade ?? current.timber_grade),
      width_b_mm: String(input.width_b_mm ?? current.width_b_mm),
      height_h_mm: String(input.height_h_mm ?? current.height_h_mm),
      service_class: String(input.service_class ?? current.service_class),
      load_duration_class: String(
        input.load_duration_class ?? current.load_duration_class,
      ),
    }));
  }, [input.force_ed_kn, input.timber_grade, input.width_b_mm,
      input.height_h_mm, input.service_class, input.load_duration_class]);
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!window.pywebview) return;
    setBusy(true);
    try {
      const r = await window.pywebview.api.compact_calculate(form);
      onSnapshot(r.data);
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
          Bemessungslast Ft,d [kN]
          <input
            type="number"
            value={form.force_ed_kn}
            onChange={(e) => set("force_ed_kn", e.target.value)}
          />
        </label>
        <label>
          Holzklasse
          <select
            value={form.timber_grade}
            onChange={(e) => set("timber_grade", e.target.value)}
          >
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
              value={form.width_b_mm}
              onChange={(e) => set("width_b_mm", e.target.value)}
            />
          </label>
          <label>
            Höhe h [mm]
            <input
              type="number"
              value={form.height_h_mm}
              onChange={(e) => set("height_h_mm", e.target.value)}
            />
          </label>
        </div>
        <label>
          Nutzungsklasse
          <select
            value={form.service_class}
            onChange={(e) => set("service_class", e.target.value)}
          >
            {["1", "2", "3"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Lasteinwirkungsdauer
          <select
            value={form.load_duration_class}
            onChange={(e) => set("load_duration_class", e.target.value)}
          >
            {options.loadDurations.map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label>
          Entwurfsziel
          <select
            value={form.objective}
            onChange={(e) => set("objective", e.target.value)}
          >
            <option value="BALANCED_DESIGN">Empfehlung / wirtschaftlich</option>
            <option value="MIN_FASTENER_COUNT">wenig Stabdübel</option>
            <option value="LOWER_UTILIZATION">mehr Reserve</option>
            <option value="COMPACT_GEOMETRY">kompakte Geometrie</option>
            <option value="MAXIMIZE_UTILIZATION">maximal ausnutzen</option>
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
}: {
  snapshot: UISnapshot;
  options: FormOptions;
  onSnapshot: (s: UISnapshot) => void;
}) {
  const source = {
    ...options.manualDefaults,
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
      ...options.manualDefaults,
      ...snapshot.technicalState,
      ...(snapshot.currentResult?.input || {}),
    };
    setForm(
      Object.fromEntries(Object.entries(next).map(([k, v]) => [k, String(v)])),
    );
  }, [snapshot.currentResult, snapshot.technicalState, options.manualDefaults]);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!window.pywebview) return;
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
      onSnapshot(r.data);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="form-workspace manual-view">
      <form className="entry-card card manual-form" onSubmit={submit}>
        <h1>Eingabedaten</h1>
        <div className="manual-grid">
          <label>
            Holzfestigkeitsklasse
            <select
              value={form.timber_grade}
              onChange={(e) => set("timber_grade", e.target.value)}
            >
              {options.timberGrades.map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Nutzungsklasse
            <select
              value={form.service_class}
              onChange={(e) => set("service_class", e.target.value)}
            >
              {["1", "2", "3"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </label>
          <label>
            Lasteinwirkungsdauer
            <select
              value={form.load_duration_class}
              onChange={(e) => set("load_duration_class", e.target.value)}
            >
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
                value={form[key] ?? ""}
                onChange={(e) => set(key, e.target.value)}
              />
            </label>
          ))}
        </div>
        <button className="primary-action" disabled={busy}>
          {busy ? "BERECHNUNG LÄUFT …" : "NACHWEIS BERECHNEN"}
        </button>
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
  const [options, setOptions] = useState<FormOptions | null>(null);
  const [theme, setTheme] = useState<Theme>(() => {
    const initialTheme =
      localStorage.getItem("ki-tool-theme") === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = initialTheme;
    return initialTheme;
  });
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
          setSnapshot(result.data);
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
      />
      <Sidebar active={active} setActive={setActive} />
      {mode === "KI Workspace" && (
        <>
          <Chat
            snapshot={snapshot}
            onSnapshot={(s) => {
              setSnapshot(s);
              setSelected(null);
            }}
          />
          <main className="workspace">
            <Visualizer
              snapshot={snapshot}
              modelOverride={selected?.visualizationModel}
            />
            <div className="results-grid">
              <BestSolution snapshot={snapshot} />
              <Variants
                snapshot={snapshot}
                selected={selected}
                onPreview={setSelected}
              />
              <section className="why card">
                <h2>WARUM DIESE VARIANTE?</h2>
                <p>
                  Die Bewertung wird ausschließlich aus dem aktuellen
                  Python-Ergebnis und den tatsächlich untersuchten Varianten
                  aufgebaut.
                </p>
                <button>Details anzeigen</button>
              </section>
              <section className="sources card">
                <h2>QUELLEN</h2>
                <p>ÖNORM EN 1995-1-1</p>
                <p>ÖNORM B 1995-1-1</p>
                <p>IHBV Holzbau-Kompakt</p>
              </section>
            </div>
          </main>
        </>
      )}
      {mode === "Kompakt" && options && (
        <CompactView
          snapshot={snapshot}
          options={options}
          onSnapshot={(s) => {
            setSnapshot(s);
            setSelected(null);
          }}
        />
      )}
      {mode === "Manuell" && options && (
        <ManualView
          snapshot={snapshot}
          options={options}
          onSnapshot={(s) => {
            setSnapshot(s);
            setSelected(null);
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
        <button disabled>PDF-Bericht erstellen</button>
      </div>
    </div>
  );
}

export default App;
