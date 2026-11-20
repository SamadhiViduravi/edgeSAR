import {
  Battery,
  Radio,
  Thermometer,
  Camera,
  Check,
  ChevronRight,
  Navigation,
} from "lucide-react";
import type { MissionEvent, Task, UAV, World } from "@/lib/types";
export const clock = (seconds: number) =>
  `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const readable = (value: string) => value.replaceAll("_", " ").toLowerCase();

export function FleetPanel({
  world,
  selected,
  onSelect,
}: {
  world: World;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="fleet-panel">
      <div className="panel-heading">
        <span>01 / FLEET</span>
        <span className="count">3 online</span>
      </div>
      <h2>Air operations</h2>
      <p className="panel-intro">Three aircraft. One shared mission.</p>
      <div className="fleet-cards">
        {world.uavs.map((u) => (
          <UAVCard
            key={u.id}
            uav={u}
            selected={selected === u.id}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="scenario-note">
        <Radio size={17} />
        <div>
          <strong>Base station connected</strong>
          <p>
            Local simulation · seed 42
            <br />
            Fixed scenario assignments
          </p>
        </div>
      </div>
      <div className="scope-note">
        <span className="eyebrow">PHASE 01</span>
        <p>Mission visualization & execution</p>
        <small>Authored routes. No CBBA or AI decisions in this version.</small>
      </div>
    </aside>
  );
}
function UAVCard({
  uav: u,
  selected,
  onSelect,
}: {
  uav: UAV;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`uav-card ${selected ? "active" : ""}`}
      style={{ "--uav": u.color } as React.CSSProperties}
      onClick={() => onSelect(u.id)}
      aria-pressed={selected}
    >
      <div className="card-title">
        <span className="aircraft-icon">
          <Navigation size={17} />
        </span>
        <strong>{u.id}</strong>
        <ChevronRight size={14} />
      </div>
      <div className="uav-status">
        <i />
        {readable(u.status)}
      </div>
      <div className="battery-row">
        <span>
          <Battery size={14} /> Battery
        </span>
        <b>{u.battery_percent.toFixed(1)}%</b>
      </div>
      <div className="battery-track">
        <i style={{ width: `${u.battery_percent}%` }} />
      </div>
      <div className="uav-meta">
        <span>
          <Camera size={12} /> RGB
        </span>
        {u.capabilities.includes("THERMAL") && (
          <span>
            <Thermometer size={12} /> Thermal
          </span>
        )}
        <span>{u.speed_mps} m/s</span>
      </div>
      <div className="uav-target">
        {u.current_task_id
          ? `Target ${u.current_task_id}`
          : u.status === "DONE"
            ? "All assigned points complete"
            : "Standing by at base"}
      </div>
    </button>
  );
}
export function TaskPanel({
  world,
  selected,
  onSelect,
}: {
  world: World;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const uav = world.uavs.find((u) => u.id === selected),
    task = world.tasks.find((t) => t.id === selected);
  return (
    <aside className="task-panel">
      <div className="panel-heading">
        <span>02 / TASK QUEUE</span>
        <span className="count">{world.tasks.length} points</span>
      </div>
      <h2>Mission objectives</h2>
      <p className="panel-intro">Scenario-defined execution order</p>
      <div className="task-cards">
        {world.tasks.map((t, i) => (
          <TaskCard
            key={t.id}
            task={t}
            index={i}
            color={world.uavs.find((u) => u.id === t.assigned_uav_id)!.color}
            selected={selected === t.id}
            onSelect={onSelect}
          />
        ))}
      </div>
      <div className="entity-detail">
        <span className="eyebrow">
          {selected ? "ENTITY INSPECTOR" : "MISSION NOTE"}
        </span>
        {uav ? (
          <>
            <h3>{uav.id}</h3>
            <dl>
              <dt>Local position</dt>
              <dd>
                {uav.position.x.toFixed(1)}, {uav.position.y.toFixed(1)} m
              </dd>
              <dt>Heading</dt>
              <dd>{uav.heading_deg.toFixed(0)}°</dd>
              <dt>Distance flown</dt>
              <dd>{uav.distance_m.toFixed(1)} m</dd>
              <dt>Capabilities</dt>
              <dd>{uav.capabilities.join(" + ")}</dd>
            </dl>
          </>
        ) : task ? (
          <>
            <h3>{task.label}</h3>
            <dl>
              <dt>Owner</dt>
              <dd>{task.assigned_uav_id}</dd>
              <dt>Location</dt>
              <dd>
                {task.location.x}, {task.location.y} m
              </dd>
              <dt>Service</dt>
              <dd>
                {task.service_elapsed.toFixed(1)} / {task.service_seconds} s
              </dd>
              <dt>Status</dt>
              <dd>{readable(task.status)}</dd>
            </dl>
          </>
        ) : (
          <p>
            Search tasks service a designated point. Completion does not
            represent full sector coverage. Select an aircraft or task to
            inspect.
          </p>
        )}
      </div>
    </aside>
  );
}
function TaskCard({
  task: t,
  index,
  color,
  selected,
  onSelect,
}: {
  task: Task;
  index: number;
  color: string;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      className={`task-card ${selected ? "active" : ""}`}
      onClick={() => onSelect(t.id)}
      aria-pressed={selected}
    >
      <span className={`task-index ${t.status === "COMPLETED" ? "done" : ""}`}>
        {t.status === "COMPLETED" ? (
          <Check size={14} />
        ) : (
          String(index + 1).padStart(2, "0")
        )}
      </span>
      <span className="task-content">
        <strong>{t.label}</strong>
        <span className="task-owner" style={{ color }}>
          {t.assigned_uav_id} <small>· {t.service_seconds}s service</small>
        </span>
        <span className={`task-status ${t.status.toLowerCase()}`}>
          {readable(t.status)}
        </span>
      </span>
    </button>
  );
}
export function EventLog({
  events,
  onSelect,
  onExport,
}: {
  events: MissionEvent[];
  onSelect: (id: string) => void;
  onExport: () => void;
}) {
  return (
    <section className="event-panel">
      <div className="event-header">
        <div>
          <span className="eyebrow">03 / AUDIT TRAIL</span>
          <h2>
            Mission events <span>{events.length}</span>
          </h2>
        </div>
        <button className="text-button" onClick={onExport}>
          Export audit JSON ↗
        </button>
      </div>
      <div className="events" role="log" aria-label="Mission event log">
        {events
          .slice()
          .reverse()
          .map((e) => (
            <button
              key={e.sequence}
              className="event-row"
              disabled={!e.entity_ids.length}
              onClick={() => e.entity_ids[0] && onSelect(e.entity_ids[0])}
            >
              <time>{clock(e.simulation_time)}</time>
              <span
                className={`event-dot ${e.type.includes("COMPLETED") ? "success" : ""}`}
              />
              <span className="event-type">{e.type.replaceAll("_", " ")}</span>
              <span>{e.message}</span>
              <small>#{String(e.sequence).padStart(3, "0")}</small>
            </button>
          ))}
      </div>
    </section>
  );
}
