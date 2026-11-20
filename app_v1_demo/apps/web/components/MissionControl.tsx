"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import {
  Crosshair,
  Play,
  Pause,
  RotateCcw,
  StepForward,
  ArrowUpRight,
} from "lucide-react";
import { useMission } from "@/hooks/useMission";
import { clock, EventLog, FleetPanel, TaskPanel } from "./Panels";
const MissionMap = dynamic(() => import("./MissionMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Initializing mission map…</div>,
});

export default function MissionControl() {
  const { scenario, world, connected, error, busy, command, exportAudit } =
    useMission();
  const [selected, setSelected] = useState<string | null>(null);
  const disabled = busy || !connected || !world;
  return (
    <main>
      <header className="mission-header">
        <a className="brand" href="/" aria-label="EdgeSAR Lab home">
          <span className="brand-icon">
            <Crosshair size={25} />
          </span>
          <span>
            EdgeSAR <b>Lab</b>
            <small>SEARCH & RESCUE RESEARCH PLATFORM</small>
          </span>
        </a>
        <div className="header-context">
          <span className="eyebrow">ACTIVE SCENARIO</span>
          <strong>{scenario?.name || "Connecting to mission…"}</strong>
        </div>
        <span
          className={`connection ${connected ? "online" : ""}`}
          role="status"
        >
          <i />
          {connected ? "Live link" : "Disconnected"}
        </span>
        <div className="mission-controls">
          <button
            className="run-button"
            disabled={
              disabled ||
              world?.mission_status === "RUNNING" ||
              world?.mission_status === "COMPLETED"
            }
            onClick={() => command("run")}
          >
            <Play size={15} />
            {world?.mission_status === "PAUSED" ? "Resume" : "Run"}
          </button>
          <button
            aria-label="Pause mission"
            title="Pause mission"
            disabled={disabled || world?.mission_status !== "RUNNING"}
            onClick={() => command("pause")}
          >
            <Pause size={16} />
          </button>
          <button
            aria-label="Step one tick"
            title="Advance 0.25 seconds"
            disabled={
              disabled ||
              world?.mission_status === "RUNNING" ||
              world?.mission_status === "COMPLETED"
            }
            onClick={() => command("step")}
          >
            <StepForward size={16} />
          </button>
          <button
            aria-label="Reset mission"
            title="Reset mission"
            disabled={disabled}
            onClick={() => {
              setSelected(null);
              void command("reset");
            }}
          >
            <RotateCcw size={15} />
            <span>Reset</span>
          </button>
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          {error}
          <span>
            Backend:{" "}
            {process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}
          </span>
        </div>
      )}
      <section className="workspace-title">
        <div>
          <div className="breadcrumb">
            WORKSPACE <span>/</span> SIMULATOR
            {" · "}
            <a href="/allocation" style={{ color: "var(--accent)" }}>Allocation POC →</a>
          </div>
          <h1>
            Mission control<span className="version-tag">PHASE 01</span>
          </h1>
        </div>
        <p>
          Observe the mission.
          <br />
          <span>Trace every decision.</span>
        </p>
      </section>
      <section className="mission-summary" aria-label="Mission summary">
        <div>
          <span className="eyebrow">MISSION STATE</span>
          <strong className="state-value">
            <i
              className={world?.mission_status === "RUNNING" ? "live-dot" : ""}
            />
            {world?.mission_status || "CONNECTING"}
          </strong>
        </div>
        <div>
          <span className="eyebrow">SIMULATION TIME</span>
          <strong data-testid="sim-clock">
            {clock(world?.simulation_time || 0)}
            <small> / 1×</small>
          </strong>
        </div>
        <div>
          <span className="eyebrow">TASKS COMPLETED</span>
          <strong>
            {world?.tasks.filter((t) => t.status === "COMPLETED").length || 0}
            <small> / 5</small>
          </strong>
        </div>
        <div>
          <span className="eyebrow">FLEET DISTANCE</span>
          <strong>
            {(
              (world?.uavs.reduce((sum, u) => sum + u.distance_m, 0) || 0) /
              1000
            ).toFixed(2)}
            <small> km</small>
          </strong>
        </div>
        <div className="seed-summary">
          <span className="eyebrow">REPRODUCIBILITY</span>
          <strong>
            Seed {scenario?.seed ?? "—"}
            <small> · fixed ticks</small>
          </strong>
        </div>
      </section>
      {scenario && world ? (
        <>
          <div className="mission-workspace">
            <FleetPanel
              world={world}
              selected={selected}
              onSelect={setSelected}
            />
            <MissionMap
              scenario={scenario}
              world={world}
              selected={selected}
              onSelect={setSelected}
            />
            <TaskPanel
              world={world}
              selected={selected}
              onSelect={setSelected}
            />
          </div>
          <EventLog
            events={world.events}
            onSelect={setSelected}
            onExport={() => void exportAudit()}
          />
        </>
      ) : (
        <div className="initial-loading">
          <Crosshair size={32} />
          <h2>Establishing mission link</h2>
          <p>
            Start the FastAPI service on port 8000. This workspace reconnects
            automatically.
          </p>
        </div>
      )}
      <footer>
        <span>
          <i className="live-dot" /> EdgeSAR simulation core v0.1.0
        </span>
        <span>
          Synthetic environment · Mission-layer simulation{" "}
          <ArrowUpRight size={12} />
        </span>
      </footer>
    </main>
  );
}
