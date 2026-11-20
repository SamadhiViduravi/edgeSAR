"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Envelope, Scenario, World } from "@/lib/types";
export const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok)
    throw new Error(`API ${response.status}: ${await response.text()}`);
  return response.json();
}

export function useMission() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [world, setWorld] = useState<World | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const revision = useRef(-1);
  const accept = useCallback((data: Envelope) => {
    if (data.schema_version !== 1 || data.type !== "world_state")
      throw new Error("Unsupported server protocol");
    if (data.revision >= revision.current) {
      revision.current = data.revision;
      setWorld(data.state);
    }
  }, []);
  useEffect(() => {
    let alive = true,
      socket: WebSocket | undefined,
      timer: ReturnType<typeof setTimeout>,
      attempts = 0;
    const connect = async () => {
      try {
        const definition = await request<Scenario>("/api/scenario");
        if (!alive) return;
        setScenario(definition);
        socket = new WebSocket(`${API.replace(/^http/, "ws")}/ws`);
        socket.onopen = () => {
          revision.current = -1;
          attempts = 0;
          setConnected(true);
          setError("");
        };
        socket.onmessage = (e) => {
          try {
            accept(JSON.parse(e.data));
          } catch {
            setError("Invalid simulation update");
          }
        };
        socket.onclose = () => {
          if (alive) {
            setConnected(false);
            timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 8000));
          }
        };
        socket.onerror = () => {
          if (alive) setError("Live connection interrupted. Reconnecting…");
        };
      } catch (e) {
        if (alive) {
          setError(e instanceof Error ? e.message : "Backend unavailable");
          timer = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 8000));
        }
      }
    };
    void connect();
    return () => {
      alive = false;
      clearTimeout(timer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [accept]);
  const command = async (action: "run" | "pause" | "step" | "reset") => {
    setBusy(true);
    setError("");
    try {
      accept(
        await request<Envelope>(`/api/control/${action}`, { method: "POST" }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Command failed");
    } finally {
      setBusy(false);
    }
  };
  const exportAudit = async () => {
    try {
      const data = await request<unknown>("/api/export");
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "edgesar-audit.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  };
  return { scenario, world, connected, error, busy, command, exportAudit };
}
