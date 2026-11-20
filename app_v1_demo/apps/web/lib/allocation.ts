// Types and small helpers for the allocation POC page. Display logic only: no simulation here.
export type Point = [number, number];

export interface Uav {
  id: string;
  speed: number;
  sensors: string[];
  start: Point;
  color: string;
}
export interface Task {
  id: string;
  landmark: string;
  sensor: string;
  priority: number;
}
export interface Decision {
  action: string;
  incident?: string;
  landmark?: string;
  sensor?: string;
  priority?: number;
}
export interface Visit {
  uav: string;
  task: string;
  landmark: string;
  start: number;
  arrive: number;
  finish: number;
  result: "verified" | "failed" | "empty";
}
export interface MissionResult {
  verify_time: Record<string, number | null>;
  missed: number;
  rmivt: number;
  wasted: number;
  visits: Visit[];
}
export interface ArmRun {
  decision: Decision;
  table: Task[];
  result: MissionResult;
}
export interface CaseRun {
  id: string;
  text: string;
  open: Task[];
  truth: Record<string, string>;
  arms: Record<string, ArmRun>;
}
export interface DemoPayload {
  landmarks: Record<string, Point>;
  base: Point;
  uavs: Uav[];
  dwell: number;
  horizon: number;
  assumptions: string[];
  cases: CaseRun[];
}

export const ARM_ORDER = ["gold", "FP16", "Q4"];

/** Where is this UAV at time t? Straight line from its last position to the landmark of each visit. */
export function uavPosition(
  uav: Uav,
  visits: Visit[],
  landmarks: Record<string, Point>,
  t: number,
): Point {
  let pos: Point = uav.start;
  for (const v of visits) {
    if (v.uav !== uav.id) continue;
    const target = landmarks[v.landmark];
    if (t < v.start) return pos;
    if (t < v.arrive) {
      const f = (t - v.start) / (v.arrive - v.start);
      return [pos[0] + (target[0] - pos[0]) * f, pos[1] + (target[1] - pos[1]) * f];
    }
    pos = target;
  }
  return pos;
}

export type SpotStatus = "none" | "waiting" | "verified" | "failed" | "empty";

/** What do we know about one landmark at time t, in one arm? */
export function spotStatus(run: ArmRun, landmark: string, t: number): SpotStatus {
  const here = run.result.visits.filter((v) => v.landmark === landmark);
  if (here.some((v) => v.result === "verified" && v.finish <= t)) return "verified";
  if (here.some((v) => v.result === "failed" && v.arrive <= t)) return "failed";
  if (here.some((v) => v.result === "empty" && v.finish <= t)) return "empty";
  return run.table.some((task) => task.landmark === landmark) ? "waiting" : "none";
}

/** Last moment in the case where anything happens (used for the time slider). */
export function lastEventTime(c: CaseRun): number {
  let last = 60;
  for (const arm of Object.values(c.arms)) {
    for (const v of arm.result.visits) last = Math.max(last, v.finish);
  }
  return Math.ceil(last + 10);
}
