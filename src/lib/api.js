// lib/api.js
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8003";

async function j(path, init) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) }
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
  return res.json();
}

export const api = {
  sensors: () => j("/api/sensors"),
  latest: () => j("/api/readings/latest"),
  history: (sensorId, minutes = 30) =>
    j(`/api/readings/history?sensor_id=${encodeURIComponent(sensorId)}&minutes=${minutes}`),

  getActuators: () => j("/api/actuators"),
  setActuators: (patch) =>
    j("/api/actuators", { method: "POST", body: JSON.stringify(patch) }),

  // ✅ 新增：事件中心（告警/日志）
  events: (limit = 200, acked = null) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (acked !== null && acked !== undefined) q.set("acked", String(acked));
    return j(`/api/events?${q.toString()}`);
  },
  ackEvent: (id) => j(`/api/events/${id}/ack`, { method: "POST" }),

    ackAllEvents: (levels = "warn,alarm") =>
  j(`/api/events/ack_all?levels=${encodeURIComponent(levels)}`, { method: "POST" }),

  // ✅ 新增：配置中心（interval/阈值/范围）
  getConfig: () => j("/api/config"),
  setConfig: (patch) => j("/api/config", { method: "POST", body: JSON.stringify(patch) })
};
