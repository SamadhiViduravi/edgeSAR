"use client";
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource } from "maplibre-gl";
import { Maximize2 } from "lucide-react";
import type { Layers, Scenario, World } from "@/lib/types";
import { lngLat, staticGeo, tracksGeo } from "@/lib/geo";

type Props = {
  scenario: Scenario;
  world: World;
  selected: string | null;
  onSelect: (id: string) => void;
};
export default function MissionMap({
  scenario: s,
  world,
  selected,
  onSelect,
}: Props) {
  const container = useRef<HTMLDivElement>(null),
    map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<Record<string, maplibregl.Marker>>({});
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;
  const [ready, setReady] = useState(false),
    [error, setError] = useState("");
  const [layers, setLayers] = useState<Layers>({
    sectors: true,
    hazards: true,
    routes: true,
  });
  const fit = () =>
    map.current?.fitBounds(
      [lngLat({ x: -90, y: -130 }, s), lngLat({ x: 2090, y: 2110 }, s)],
      { padding: 36, duration: 500 },
    );
  useEffect(() => {
    if (!container.current) return;
    let m: maplibregl.Map;
    try {
      maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');
      m = new maplibregl.Map({
        container: container.current,
        style: {
          version: 8,
          sources: {},
          layers: [
            {
              id: "background",
              type: "background",
              paint: { "background-color": "#101e29" },
            },
          ],
        },
        center: lngLat({ x: 1000, y: 1000 }, s),
        zoom: 14,
        pitch: 0,
        maxPitch: 0,
        attributionControl: false,
      });
    } catch {
      setError(
        "WebGL is unavailable. Enable hardware acceleration to display the mission map.",
      );
      return;
    }
    map.current = m;
    m.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    m.on("error", (e) => setError(`Map error: ${e.error.message}`));
    m.on("idle", () => {
      if (m.getSource('routes') && m.isSourceLoaded('routes') && m.isSourceLoaded('regions')) {
        container.current?.setAttribute('data-map-ready', 'true');
      }
    });
    m.on("load", () => {
      const geo = staticGeo(s);
      Object.entries(geo).forEach(([id, data]) =>
        m.addSource(id, { type: "geojson", data }),
      );
      m.addSource("tracks", { type: "geojson", data: tracksGeo(s, world) });
      m.addLayer({
        id: "sectors-fill",
        type: "fill",
        source: "sectors",
        paint: { "fill-color": "#243a47", "fill-opacity": 0.22 },
      });
      m.addLayer({
        id: "sectors-line",
        type: "line",
        source: "sectors",
        paint: {
          "line-color": "#49606d",
          "line-width": 1,
          "line-dasharray": [4, 4],
        },
      });
      m.addLayer({
        id: "boundary",
        type: "line",
        source: "boundary",
        paint: { "line-color": "#8aabb8", "line-width": 2 },
      });
      const colors = {
        water: "#247ca6",
        building: "#526675",
        debris: "#a57642",
        no_fly: "#e76470",
        blocked_road: "#d78b49",
      };
      Object.entries(colors).forEach(([kind, color]) => {
        m.addLayer({
          id: `${kind}-fill`,
          type: "fill",
          source: "regions",
          filter: ["==", ["get", "kind"], kind],
          paint: {
            "fill-color": color,
            "fill-opacity": kind === "no_fly" ? 0.15 : 0.5,
          },
        });
        m.addLayer({
          id: `${kind}-line`,
          type: "line",
          source: "regions",
          filter: ["==", ["get", "kind"], kind],
          paint: {
            "line-color": color,
            "line-width": kind === "no_fly" ? 2.5 : 1.5,
            ...(kind === "no_fly" ? { "line-dasharray": [3, 2] } : {}),
          },
        });
      });
      const pixels = new Uint8Array(16 * 16 * 4);
      for (let y = 0; y < 16; y++)
        for (let x = 0; x < 16; x++)
          if ((x + y) % 16 < 3) {
            const i = (y * 16 + x) * 4;
            pixels[i] = 231;
            pixels[i + 1] = 100;
            pixels[i + 2] = 112;
            pixels[i + 3] = 90;
          }
      m.addImage("stripe", { width: 16, height: 16, data: pixels });
      m.addLayer({
        id: "no_fly-hatch",
        type: "fill",
        source: "regions",
        filter: ["==", ["get", "kind"], "no_fly"],
        paint: { "fill-pattern": "stripe" },
      });
      m.addLayer({
        id: "routes-casing",
        type: "line",
        source: "routes",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": "#081119", "line-width": 8 },
      });
      m.addLayer({
        id: "routes-line",
        type: "line",
        source: "routes",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3,
          "line-dasharray": [2, 1.5],
        },
      });
      m.addLayer({
        id: "tracks-line",
        type: "line",
        source: "tracks",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": ["get", "color"], "line-width": 4 },
      });
      m.addLayer({
        id: "selected-route",
        type: "line",
        source: "routes",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#ffffff", "line-width": 1.5 },
      });
      const label = (
        id: string,
        position: { x: number; y: number },
        text: string,
        cls: string,
        interactive = false,
      ) => {
        const el = document.createElement(interactive ? "button" : "div");
        el.className = cls;
        el.textContent = text;
        if (interactive) {
          el.setAttribute("aria-label", `Select ${id}`);
          el.onclick = () => selectRef.current(id);
        }
        markers.current[id] = new maplibregl.Marker({ element: el })
          .setLngLat(lngLat(position, s))
          .addTo(m);
      };
      s.sectors.forEach((r) =>
        label(
          r.id,
          { x: r.polygon[0].x + 75, y: r.polygon[0].y + 920 },
          r.id,
          "sector-label",
        ),
      );
      s.regions
        .filter((r) => r.kind !== "building")
        .forEach((r) => {
          const points = r.polygon.slice(0, -1);
          const position = {
            x: points.reduce((a, p) => a + p.x, 0) / points.length,
            y: points.reduce((a, p) => a + p.y, 0) / points.length,
          };
          label(
            r.id,
            position,
            r.kind === "no_fly"
              ? "⊘ NO-FLY ZONE"
              : r.kind === "water"
                ? "≈ FLOODPLAIN"
                : r.kind === "blocked_road"
                  ? "× BLOCKED ROAD"
                  : "▧ DEBRIS",
            `hazard-label ${r.kind}`,
          );
        });
      label("BASE", s.base, "⌂ BASE / COMMAND", "base-marker");
      s.tasks.forEach((t, i) =>
        label(t.id, t.location, String(i + 1), "task-marker", true),
      );
      s.uavs.forEach((u, index) => {
        label(u.id, u.position, "", "uav-marker", true);
        const el = markers.current[u.id].getElement();
        el.style.setProperty("--uav", u.color);
        const arrow = document.createElement("span");
        arrow.className = "uav-arrow";
        arrow.textContent = "▲";
        el.appendChild(arrow);
        const name = document.createElement("span");
        name.className = "uav-name";
        name.style.top = `${-21-index*18}px`;
        name.textContent = u.id;
        el.appendChild(name);
      });
      fit();
      setReady(true);
    });
    const resize = new ResizeObserver(() => m.resize());
    resize.observe(container.current);
    return () => {
      resize.disconnect();
      Object.values(markers.current).forEach((marker) => marker.remove());
      markers.current = {};
      m.remove();
      map.current = null;
      setReady(false);
    };
    // A scenario revision rebuilds the map; telemetry never does.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.id, s.version]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const m = map.current;
    (m.getSource("tracks") as GeoJSONSource).setData(tracksGeo(s, world));
    world.uavs.forEach((u) => {
      const marker = markers.current[u.id];
      marker?.setLngLat(lngLat(u.position, s));
      const arrow = marker
        ?.getElement()
        .querySelector<HTMLElement>(".uav-arrow");
      if (arrow) arrow.style.transform = `rotate(${u.heading_deg}deg)`;
      marker?.getElement().classList.toggle("selected", selected === u.id);
    });
    world.tasks.forEach((t) => {
      const el = markers.current[t.id]?.getElement();
      el?.classList.toggle("completed", t.status === "COMPLETED");
      el?.classList.toggle("selected", selected === t.id);
    });
    m.setFilter("selected-route", [
      "any",
      ["==", ["get", "id"], selected || ""],
      ["==", ["get", "uav"], selected || ""],
    ]);
  }, [world, selected, ready, s]);
  useEffect(() => {
    if (!ready || !map.current) return;
    const groups = {
      sectors: ["sectors-fill", "sectors-line"],
      hazards: [
        "water-fill",
        "water-line",
        "building-fill",
        "building-line",
        "debris-fill",
        "debris-line",
        "no_fly-fill",
        "no_fly-line",
        "no_fly-hatch",
        "blocked_road-fill",
        "blocked_road-line",
      ],
      routes: ["routes-casing", "routes-line", "tracks-line", "selected-route"],
    };
    Object.entries(groups).forEach(([group, ids]) =>
      ids.forEach((id) =>
        map.current!.setLayoutProperty(
          id,
          "visibility",
          layers[group as keyof Layers] ? "visible" : "none",
        ),
      ),
    );
    s.sectors.forEach((r) => {
      const el = markers.current[r.id]?.getElement();
      if (el) el.style.display = layers.sectors ? "" : "none";
    });
    s.regions.forEach((r) => {
      const el = markers.current[r.id]?.getElement();
      if (el) el.style.display = layers.hazards ? "" : "none";
    });
  }, [layers, ready, s]);
  return (
    <section className="map-panel" aria-label="Interactive mission map">
      <div className="map-top">
        <span>
          <i className="live-dot" /> SYNTHETIC OPERATING AREA
        </span>
        <span>2,000 × 2,000 m</span>
      </div>
      <div ref={container} className="map-canvas" data-testid="mission-map" />
      {error && (
        <div className="map-error" role="alert">
          {error}
        </div>
      )}
      <button className="fit-button" onClick={fit} title="Fit mission extent">
        <Maximize2 size={15} /> Fit area
      </button>
      <div className="map-north">
        N<span>↑</span>
      </div>
      <div className="map-legend">
        <strong>MAP LAYERS</strong>
        <div className="layer-toggles">
          {Object.keys(layers).map((key) => (
            <label key={key}>
              <input
                type="checkbox"
                checked={layers[key as keyof Layers]}
                onChange={(e) =>
                  setLayers({ ...layers, [key]: e.target.checked })
                }
              />
              {key}
            </label>
          ))}
        </div>
        <div className="legend-keys">
          <span>
            <i className="key building" />
            Building
          </span>
          <span>
            <i className="key water" />
            Water
          </span>
          <span>
            <i className="key debris" />
            Debris
          </span>
          <span>
            <i className="key no_fly" />
            No-fly
          </span>
        </div>
        <p>
          Dashed: planned route · Solid: flown path
          <br />
          Water permits overflight · Hard obstacles: 12 m clearance
        </p>
      </div>
      <div className="map-caption">
        LOCAL METRES / SYNTHETIC SCENARIO{" "}
        <span>Authored routes · no automatic planner</span>
      </div>
    </section>
  );
}
