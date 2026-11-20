"use client";
// Allocation POC page. It only DISPLAYS results made by packages/allocation (Python).
// No simulation logic lives here. Same rule as the rest of V1: the frontend is display only.
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import {
  ARM_ORDER,
  lastEventTime,
  spotStatus,
  uavPosition,
  type ArmRun,
  type CaseRun,
  type DemoPayload,
  type Decision,
  type SpotStatus,
} from "@/lib/allocation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const WORLD = 2000; // metres, same 2 km square as V1

const ARM_LABEL: Record<string, { name: string; note: string }> = {
  gold: { name: "Answer key (gold)", note: "Perfect task table + same CBBA" },
  FP16: { name: "FP16", note: "Llama 3.2 1B, full precision" },
  Q4: { name: "Q4_K_M", note: "Llama 3.2 1B, 4-bit" },
};

// My reading of each case. These five cases are fixed, so the notes are fixed too.
const CASE_NOTE: Record<string, string> = {
  c0618:
    "Both models update the wrong incident, so the new child at North Bridge is missed. FP16 also changes Boat Jetty to THERMAL, which delays Railway Crossing. This shows model error more than a quantization effect.",
  c0119:
    "Q4 keeps a false alarm at Clinic Gate (one wasted visit). The real person at Hill Road Bend is verified about 6 s later.",
  c1189:
    "Both models give a wrong camera or priority. The allocator cannot fix this. Both arms are far slower than the answer key.",
  c0093:
    "FP16 ignores the report, so nobody checks Rice Field A and the person is missed. Q4 creates the task and verifies at 75 s. This is the biggest difference between the two models.",
  c0047:
    "Small effect. FP16 adds a task for cattle at Rice Field A (one wasted visit). North Bridge is verified about 10 s later.",
};

const STATUS_STYLE: Record<SpotStatus | "missed", { fill: string; stroke: string; text: string }> = {
  none: { fill: "#17232e", stroke: "#34424f", text: "no task" },
  waiting: { fill: "#17232e", stroke: "#e3edf3", text: "task waiting" },
  verified: { fill: "#2f8f5b", stroke: "#6fdc8c", text: "verified" },
  failed: { fill: "#8f3a3a", stroke: "#ff7b7b", text: "wrong camera" },
  empty: { fill: "#4a5560", stroke: "#8a9bab", text: "nobody there" },
  missed: { fill: "#17232e", stroke: "#ff7b7b", text: "missed" },
};

const css: Record<string, CSSProperties> = {
  page: { maxWidth: 1400, margin: "0 auto", padding: "16px 16px 48px" },
  card: { background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 8, padding: 12 },
  muted: { color: "var(--muted)" },
  row: { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" },
  th: { textAlign: "left", padding: "6px 8px", borderBottom: "1px solid var(--border)", color: "var(--muted)", fontWeight: 600 },
  td: { padding: "6px 8px", borderBottom: "1px solid #1b2733" },
};

function describe(d: Decision): string {
  switch (d.action) {
    case "CREATE_VERIFICATION":
      return `Create task: ${d.landmark}, ${d.sensor}, priority ${d.priority}`;
    case "UPDATE_INCIDENT":
      return `Update ${d.incident}: ${d.landmark}, ${d.sensor}, priority ${d.priority}`;
    case "CLOSE_INCIDENT":
      return `Close ${d.incident}`;
    case "NO_ACTION":
      return "No action";
    default:
      return d.action;
  }
}

const fmt = (x: number) => x.toFixed(1);

function ArmMap({ run, data, t, caseRun }: { run: ArmRun; data: DemoPayload; t: number; caseRun: CaseRun }) {
  const P = (p: [number, number]): [number, number] => [p[0], WORLD - p[1]]; // flip y for the screen
  const [bx, by] = P(data.base);
  return (
    <svg viewBox={`0 0 ${WORLD} ${WORLD}`} style={{ width: "100%", height: "auto", display: "block", background: "#0b1119", borderRadius: 6 }} role="img" aria-label="Map of one arm">
      {[500, 1000, 1500].map((g) => (
        <g key={g} stroke="#1b2733" strokeWidth={4}>
          <line x1={g} y1={0} x2={g} y2={WORLD} />
          <line x1={0} y1={g} x2={WORLD} y2={g} />
        </g>
      ))}
      <rect x={0} y={0} width={WORLD} height={WORLD} fill="none" stroke="#26323e" strokeWidth={8} />

      {/* planned routes: start -> each visited landmark, in order */}
      {data.uavs.map((u) => {
        const stops = run.result.visits
          .filter((v) => v.uav === u.id)
          .sort((a, b) => a.start - b.start)
          .map((v) => P(data.landmarks[v.landmark]));
        const pts = [P(u.start), ...stops];
        if (pts.length < 2) return null;
        return (
          <polyline key={u.id} points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke={u.color} strokeOpacity={0.35} strokeWidth={8} strokeDasharray="30 20" />
        );
      })}

      {/* landmarks */}
      {Object.entries(data.landmarks).map(([name, pos]) => {
        const [x, y] = P(pos);
        const hasVictim = name in caseRun.truth;
        const base = spotStatus(run, name, t);
        const key: SpotStatus | "missed" = base === "none" && hasVictim ? "missed" : base;
        const st = STATUS_STYLE[key];
        const show = hasVictim || base !== "none";
        return (
          <g key={name} opacity={show ? 1 : 0.45}>
            <title>{`${name}: ${st.text}${hasVictim ? " (a person is there)" : ""}`}</title>
            <circle cx={x} cy={y} r={hasVictim ? 38 : 26} fill={st.fill} stroke={st.stroke} strokeWidth={hasVictim ? 10 : 6} strokeDasharray={key === "missed" ? "14 10" : undefined} />
            <text x={x} y={y - 52} fill={show ? "#e3edf3" : "#8a9bab"} fontSize={46} textAnchor="middle">
              {name}
            </text>
          </g>
        );
      })}

      {/* base */}
      <rect x={bx - 22} y={by - 22} width={44} height={44} fill="#101923" stroke="#8a9bab" strokeWidth={6} />
      <text x={bx + 40} y={by + 16} fill="#8a9bab" fontSize={40}>
        Base
      </text>

      {/* UAVs */}
      {data.uavs.map((u) => {
        const [x, y] = P(uavPosition(u, run.result.visits, data.landmarks, t));
        return (
          <g key={u.id}>
            <circle cx={x} cy={y} r={30} fill={u.color} stroke="#0b1119" strokeWidth={6} />
            <text x={x} y={y + 14} fill="#0b1119" fontSize={40} fontWeight={700} textAnchor="middle">
              {u.id.slice(-1)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function ArmPanel({ arm, run, gold, data, t, caseRun }: { arm: string; run: ArmRun; gold: ArmRun; data: DemoPayload; t: number; caseRun: CaseRun }) {
  const label = ARM_LABEL[arm] ?? { name: arm, note: "" };
  const delta = run.result.rmivt - gold.result.rmivt;
  const victims = Object.keys(caseRun.truth);
  return (
    <div style={css.card}>
      <div style={{ ...css.row, justifyContent: "space-between" }}>
        <strong style={{ fontSize: 15 }}>{label.name}</strong>
        <span style={css.muted}>{label.note}</span>
      </div>
      <div style={{ margin: "8px 0", ...css.muted }}>Decision: <span style={{ color: "var(--text)" }}>{describe(run.decision)}</span></div>
      <ArmMap run={run} data={data} t={t} caseRun={caseRun} />
      <div style={{ ...css.row, marginTop: 10, gap: 16 }}>
        <div>
          <div style={css.muted}>RMIVT</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{fmt(run.result.rmivt)} s</div>
          {arm !== "gold" && (
            <div style={{ color: delta > 0.05 ? "#ff7b7b" : "var(--muted)" }}>{delta > 0.05 ? `+${fmt(delta)} s vs answer key` : "same as answer key"}</div>
          )}
        </div>
        <div>
          <div style={css.muted}>Missed</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: run.result.missed ? "#ff7b7b" : "var(--text)" }}>{run.result.missed}</div>
        </div>
        <div>
          <div style={css.muted}>Wasted visits</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>{run.result.wasted}</div>
        </div>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
        <thead>
          <tr>
            <th style={css.th}>Person at</th>
            <th style={css.th}>Verified at</th>
          </tr>
        </thead>
        <tbody>
          {victims.map((v) => {
            const vt = run.result.verify_time[v];
            return (
              <tr key={v}>
                <td style={css.td}>{v}</td>
                <td style={{ ...css.td, color: vt == null ? "#ff7b7b" : "var(--text)" }}>{vt == null ? `missed (counted as ${data.horizon} s)` : `${fmt(vt)} s`}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function AllocationPage() {
  const [data, setData] = useState<DemoPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [caseId, setCaseId] = useState("c0093");
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(15);
  const [showRules, setShowRules] = useState(false);
  const last = useRef(0);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/api/allocation/demo`)
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<DemoPayload>;
      })
      .then((d) => alive && setData(d))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, []);

  const current: CaseRun | undefined = useMemo(() => data?.cases.find((c) => c.id === caseId) ?? data?.cases[0], [data, caseId]);
  const tMax = current ? lastEventTime(current) : 100;

  // reset the clock when the case changes
  useEffect(() => {
    setT(0);
    setPlaying(false);
  }, [caseId]);

  // simple animation loop: speed = simulated seconds per real second
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    last.current = performance.now();
    const tick = (now: number) => {
      const dt = (now - last.current) / 1000;
      last.current = now;
      let done = false;
      setT((prev) => {
        const next = prev + dt * speed;
        if (next >= tMax) {
          done = true;
          return tMax;
        }
        return next;
      });
      if (done) setPlaying(false);
      else raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, tMax]);

  if (error) {
    return (
      <main style={css.page}>
        <a href="/" style={{ color: "var(--accent)" }}>← Mission control</a>
        <h1>Allocation POC</h1>
        <div style={{ ...css.card, borderColor: "#ff7b7b" }}>
          <strong>Could not load the results from the backend.</strong>
          <p style={css.muted}>Error: {error}</p>
          <p style={css.muted}>
            Check that the API is running at {API} and that <code>allocation_router</code> is included in <code>apps/api/app/main.py</code>. Then reload this page.
          </p>
        </div>
      </main>
    );
  }
  if (!data || !current) {
    return (
      <main style={css.page}>
        <p style={css.muted}>Loading results…</p>
      </main>
    );
  }

  const gold = current.arms["gold"];
  return (
    <main style={css.page}>
      <div style={{ ...css.row, justifyContent: "space-between" }}>
        <a href="/" style={{ color: "var(--accent)" }}>← Mission control</a>
        <span style={css.muted}>EdgeSAR · allocation proof of concept</span>
      </div>
      <h1 style={{ margin: "8px 0 4px", fontSize: 22 }}>Same CBBA, three task tables</h1>
      <p style={{ ...css.muted, margin: "0 0 12px", maxWidth: 900 }}>
        Each map uses the same UAVs and the same allocator. Only the task table changes: the answer key, what FP16 decided, or what Q4 decided. If the maps differ, the model's decision changed the mission.
      </p>

      <div style={{ ...css.card, borderColor: "#ffc66d", marginBottom: 12 }}>
        <div style={{ ...css.row, justifyContent: "space-between" }}>
          <strong style={{ color: "#ffc66d" }}>Mechanism POC. Not evidence.</strong>
          <button onClick={() => setShowRules((s) => !s)} style={{ padding: "4px 10px" }}>
            {showRules ? "Hide rules" : "Show all rules"}
          </button>
        </div>
        <div style={css.muted}>5 selected cases. Tasks are known at t = 0. Truth is the gold table. Do not quote these numbers as results.</div>
        {showRules && (
          <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
            {data.assumptions.map((a) => (
              <li key={a} style={{ marginBottom: 2 }}>{a}</li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ ...css.row, marginBottom: 12 }}>
        {data.cases.map((c) => (
          <button
            key={c.id}
            onClick={() => setCaseId(c.id)}
            style={{ padding: "6px 12px", borderColor: c.id === current.id ? "var(--accent)" : undefined, color: c.id === current.id ? "var(--accent)" : undefined }}
          >
            {c.id}
          </button>
        ))}
      </div>

      <div style={{ ...css.card, marginBottom: 12 }}>
        <div style={css.muted}>Field report</div>
        <div style={{ margin: "4px 0 8px", fontSize: 14 }}>{current.text}</div>
        <div style={css.muted}>
          Open incidents before the report:{" "}
          <span style={{ color: "var(--text)" }}>
            {current.open.length === 0 ? "none" : current.open.map((o) => `${o.id} ${o.landmark} (${o.sensor}, P${o.priority})`).join("; ")}
          </span>
        </div>
        {CASE_NOTE[current.id] && <div style={{ marginTop: 8 }}><span style={css.muted}>What to look at: </span>{CASE_NOTE[current.id]}</div>}
      </div>

      <div style={{ ...css.card, marginBottom: 12 }}>
        <div style={css.row}>
          <button onClick={() => { if (t >= tMax) setT(0); setPlaying((p) => !p); }} style={{ padding: "6px 14px", minWidth: 72 }}>
            {playing ? "Pause" : "Play"}
          </button>
          <button onClick={() => { setPlaying(false); setT(0); }} style={{ padding: "6px 14px" }}>Reset</button>
          <input
            type="range"
            min={0}
            max={tMax}
            step={0.5}
            value={t}
            onChange={(e) => { setPlaying(false); setT(Number(e.target.value)); }}
            aria-label="Mission time"
            style={{ flex: 1, minWidth: 160 }}
          />
          <strong style={{ minWidth: 90, textAlign: "right" }}>t = {Math.round(t)} s</strong>
          <label style={css.muted}>
            Speed{" "}
            <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))} style={{ background: "#17232e", color: "var(--text)", border: "1px solid #34424f", borderRadius: 6, padding: 3 }}>
              <option value={5}>5×</option>
              <option value={15}>15×</option>
              <option value={40}>40×</option>
            </select>
          </label>
        </div>
        <div style={{ ...css.row, marginTop: 8, ...css.muted }}>
          {data.uavs.map((u) => (
            <span key={u.id}><span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 5, background: u.color, marginRight: 4 }} />{u.id} ({u.sensors.join("+")}, {u.speed} m/s)</span>
          ))}
          <span>· Ring colour: <span style={{ color: "#6fdc8c" }}>verified</span>, <span style={{ color: "#ff7b7b" }}>wrong camera / missed</span>, grey = nobody there</span>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 12 }}>
        {ARM_ORDER.map((arm) => (
          <ArmPanel key={arm} arm={arm} run={current.arms[arm]} gold={gold} data={data} t={t} caseRun={current} />
        ))}
      </div>

      <h2 style={{ fontSize: 16, margin: "20px 0 8px" }}>All five cases (RMIVT in seconds, lower is better)</h2>
      <div style={{ ...css.card, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 560 }}>
          <thead>
            <tr>
              <th style={css.th}>Case</th>
              {ARM_ORDER.map((a) => (
                <th key={a} style={css.th}>{ARM_LABEL[a]?.name ?? a}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.cases.map((c) => (
              <tr key={c.id} onClick={() => setCaseId(c.id)} style={{ cursor: "pointer", background: c.id === current.id ? "#17232e" : undefined }}>
                <td style={css.td}>{c.id}</td>
                {ARM_ORDER.map((a) => {
                  const r = c.arms[a].result;
                  return (
                    <td key={a} style={css.td}>
                      {fmt(r.rmivt)}
                      <span style={css.muted}> · missed {r.missed} · wasted {r.wasted}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
