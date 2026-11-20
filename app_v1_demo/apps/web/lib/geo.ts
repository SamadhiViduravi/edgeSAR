import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Point, Scenario, World } from "./types";
export function lngLat(p: Point, s: Scenario): [number, number] {
  return [
    s.origin.longitude +
      p.x / (111320 * Math.cos((s.origin.latitude * Math.PI) / 180)),
    s.origin.latitude + p.y / 110540,
  ];
}
const collection = (features: Feature[]): FeatureCollection => ({
  type: "FeatureCollection",
  features,
});
const feature = (
  geometry: Geometry,
  properties: Record<string, unknown>,
): Feature => ({ type: "Feature", geometry, properties });
export function staticGeo(s: Scenario) {
  const polygon = (points: Point[]) => ({
    type: "Polygon" as const,
    coordinates: [points.map((p) => lngLat(p, s))],
  });
  return {
    sectors: collection(
      s.sectors.map((r) => feature(polygon(r.polygon), { id: r.id })),
    ),
    regions: collection(
      s.regions.map((r) =>
        feature(polygon(r.polygon), { id: r.id, kind: r.kind }),
      ),
    ),
    boundary: collection([
      feature(
        polygon([
          { x: 0, y: 0 },
          { x: s.width_m, y: 0 },
          { x: s.width_m, y: s.height_m },
          { x: 0, y: s.height_m },
          { x: 0, y: 0 },
        ]),
        {},
      ),
    ]),
    routes: collection(
      s.tasks.map((t) =>
        feature(
          { type: "LineString", coordinates: t.route.map((p) => lngLat(p, s)) },
          {
            id: t.id,
            uav: t.assigned_uav_id,
            color: s.uavs.find((u) => u.id === t.assigned_uav_id)!.color,
          },
        ),
      ),
    ),
  };
}
export function tracksGeo(s: Scenario, w: World) {
  return collection(
    w.uavs.flatMap((u) => {
      const points: Point[] = [];
      for (const t of w.tasks.filter((t) => t.assigned_uav_id === u.id)) {
        if (t.status === "PENDING") break;
        if (t.status === "COMPLETED" || t.status === "IN_PROGRESS") {
          points.push(...t.route);
          continue;
        }
        // Project traveled position to the ordered authored route using accumulated distance.
        let remaining =
          u.distance_m -
          w.tasks
            .filter(
              (a) => a.assigned_uav_id === u.id && a.status === "COMPLETED",
            )
            .reduce(
              (sum, a) =>
                sum +
                a.route
                  .slice(1)
                  .reduce(
                    (v, p, i) =>
                      v + Math.hypot(p.x - a.route[i].x, p.y - a.route[i].y),
                    0,
                  ),
              0,
            );
        points.push(t.route[0]);
        for (let i = 1; i < t.route.length; i++) {
          const d = Math.hypot(
            t.route[i].x - t.route[i - 1].x,
            t.route[i].y - t.route[i - 1].y,
          );
          if (remaining < d) break;
          points.push(t.route[i]);
          remaining -= d;
        }
        points.push(u.position);
        break;
      }
      return points.length > 1
        ? [
            feature(
              {
                type: "LineString",
                coordinates: points.map((p) => lngLat(p, s)),
              },
              { color: u.color, id: u.id },
            ),
          ]
        : [];
    }),
  );
}
