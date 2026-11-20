export type Point = { x: number; y: number };
export type Region = {
  id: string;
  label: string;
  kind: "building" | "water" | "no_fly" | "debris" | "blocked_road";
  polygon: Point[];
};
export type Sector = { id: string; label: string; polygon: Point[] };
export type UAV = {
  id: string;
  position: Point;
  speed_mps: number;
  battery_percent: number;
  capabilities: string[];
  color: string;
  status: string;
  heading_deg: number;
  distance_m: number;
  current_task_id: string | null;
};
export type Task = {
  id: string;
  label: string;
  type: string;
  location: Point;
  assigned_uav_id: string;
  route: Point[];
  service_seconds: number;
  sector_id: string | null;
  status: string;
  service_elapsed: number;
};
export type MissionEvent = {
  sequence: number;
  simulation_time: number;
  type: string;
  entity_ids: string[];
  message: string;
};
export type Scenario = {
  schema_version: 1;
  id: string;
  version: string;
  name: string;
  seed: number;
  width_m: number;
  height_m: number;
  origin: { longitude: number; latitude: number };
  base: Point;
  sectors: Sector[];
  regions: Region[];
  uavs: UAV[];
  tasks: Task[];
};
export type World = {
  tick: number;
  simulation_time: number;
  mission_status: "READY" | "RUNNING" | "PAUSED" | "COMPLETED";
  uavs: UAV[];
  tasks: Task[];
  events: MissionEvent[];
};
export type Envelope = {
  schema_version: 1;
  type: "world_state";
  revision: number;
  scenario_id: string;
  state: World;
};
export type Layers = { sectors: boolean; hazards: boolean; routes: boolean };
