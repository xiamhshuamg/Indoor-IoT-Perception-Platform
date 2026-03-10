// lib/store.js
import { reactive, computed } from "vue";
import { api } from "./api";
import { connectWs } from "./ws";

const state = reactive({
  started: false,
  wsOnline: false,

  sensors: [],
  latestMap: {},
  history: [],
  selectedId: "",

  actuators: { lights: false, ventilation: false, purifier: false, target_temp: 24 },

  events: [],
  config: null,

  // ✅ 新增：强制更新计数器
  updateCounter: 0
});

let stopWs = null;
let mockTimer = null;

function nowISO() {
  return new Date().toISOString();
}

function initMock() {
  state.wsOnline = true;

  state.sensors = [
    // 客厅传感器
    { id: "T-101", room: "客厅", name: "温度", type: "temperature", unit: "°C", warn_low: 18, warn_high: 28 },
    { id: "H-101", room: "客厅", name: "湿度", type: "humidity", unit: "%", warn_low: 30, warn_high: 70 },
    { id: "C-101", room: "客厅", name: "CO₂", type: "co2", unit: "ppm", warn_low: 400, warn_high: 1200 },
    { id: "P-101", room: "客厅", name: "PM2.5", type: "pm25", unit: "µg/m³", warn_low: 0, warn_high: 75 },
    { id: "N-101", room: "客厅", name: "噪声", type: "noise", unit: "dB", warn_low: 30, warn_high: 65 },
    { id: "L-101", room: "客厅", name: "光照", type: "light", unit: "lx", warn_low: 80, warn_high: 800 },

    // 卧室传感器
    { id: "T-102", room: "卧室", name: "温度", type: "temperature", unit: "°C", warn_low: 18, warn_high: 28 },
    { id: "H-102", room: "卧室", name: "湿度", type: "humidity", unit: "%", warn_low: 30, warn_high: 70 },
    { id: "C-102", room: "卧室", name: "CO₂", type: "co2", unit: "ppm", warn_low: 400, warn_high: 1200 },
    { id: "P-102", room: "卧室", name: "PM2.5", type: "pm25", unit: "µg/m³", warn_low: 0, warn_high: 75 },
    { id: "N-102", room: "卧室", name: "噪声", type: "noise", unit: "dB", warn_low: 30, warn_high: 65 },
    { id: "L-102", room: "卧室", name: "光照", type: "light", unit: "lx", warn_low: 80, warn_high: 800 },
  ];

  state.selectedId = state.sensors[0].id;

  state.config = {
    interval: 2,
    sensors: state.sensors.map((s) => ({
      ...s,
      gen_low: s.type === "temperature" ? 16 : s.type === "humidity" ? 20 : s.type === "co2" ? 350 : s.type === "pm25" ? 0 : s.type === "noise" ? 20 : s.type === "light" ? 10 : 0,
      gen_high: s.type === "temperature" ? 30 : s.type === "humidity" ? 80 : s.type === "co2" ? 2000 : s.type === "pm25" ? 180 : s.type === "noise" ? 95 : s.type === "light" ? 1200 : 1000,
      step: s.type === "temperature" ? 0.35 : s.type === "humidity" ? 1.2 : s.type === "co2" ? 45 : s.type === "pm25" ? 6 : s.type === "noise" ? 2.5 : s.type === "light" ? 60 : 1
    }))
  };

  state.events = [
    { id: 1, ts: nowISO(), level: "info", category: "system", message: "当前为前端 Mock 模式（后端未连接）", acked: true }
  ];

  const base = {
    "T-101": 24, "H-101": 55, "C-101": 800, "P-101": 35, "N-101": 45, "L-101": 260,
    "T-102": 22, "H-102": 50, "C-102": 750, "P-102": 30, "N-102": 40, "L-102": 180
  };

  function qualityBy(s, v) {
    if (typeof s.warn_low === "number" && v < s.warn_low) return "warn";
    if (typeof s.warn_high === "number" && v > s.warn_high) return "alarm";
    return "ok";
  }

  const mp = {};
  for (const s of state.sensors) {
    const v = base[s.id];
    mp[s.id] = { sensor_id: s.id, ts: nowISO(), value: v, battery: 86, quality: qualityBy(s, v) };
  }
  state.latestMap = mp;
  state.history = [];

  if (mockTimer) clearInterval(mockTimer);
  mockTimer = setInterval(() => {
    const mp2 = { ...state.latestMap };

    const t1 = mp2["T-101"].value + (Math.random() - 0.5) * 0.25 + ((state.actuators.target_temp - mp2["T-101"].value) * 0.02);
    const h1 = mp2["H-101"].value + (Math.random() - 0.5) * 0.6;
    const co2_1 = mp2["C-101"].value + (Math.random() - 0.5) * 12 + (state.actuators.ventilation ? -18 : +6);
    const pm1 = mp2["P-101"].value + (Math.random() - 0.5) * 2 + (state.actuators.purifier ? -3 : +1);
    const noise1 = mp2["N-101"].value + (Math.random() - 0.5) * 1.5;
    const lx1 = mp2["L-101"].value + (state.actuators.lights ? +18 : -10) + (Math.random() - 0.5) * 10;

    const t2 = mp2["T-102"].value + (Math.random() - 0.5) * 0.25;
    const h2 = mp2["H-102"].value + (Math.random() - 0.5) * 0.6;
    const co2_2 = mp2["C-102"].value + (Math.random() - 0.5) * 12;
    const pm2 = mp2["P-102"].value + (Math.random() - 0.5) * 2;
    const noise2 = mp2["N-102"].value + (Math.random() - 0.5) * 1.5;
    const lx2 = mp2["L-102"].value + (state.actuators.lights ? +12 : -8) + (Math.random() - 0.5) * 8;

    const next = {
      "T-101": t1, "H-101": h1, "C-101": co2_1, "P-101": pm1, "N-101": noise1, "L-101": lx1,
      "T-102": t2, "H-102": h2, "C-102": co2_2, "P-102": pm2, "N-102": noise2, "L-102": lx2
    };

    for (const s of state.sensors) {
      const v = Number(next[s.id].toFixed(s.type === "temperature" ? 1 : 0));
      mp2[s.id] = {
        sensor_id: s.id,
        ts: nowISO(),
        value: v,
        battery: Math.max(20, (mp2[s.id].battery ?? 86) - (Math.random() * 0.02)),
        quality: qualityBy(s, v)
      };
    }

    // ✅ 关键修复：替换整个对象并增加计数器
    state.latestMap = mp2;
    state.updateCounter++;

    const r = mp2[state.selectedId];
    if (r) state.history = [...state.history, r].slice(-300);
  }, 1000);
}

async function loadHistory(sensorId) {
  if (!sensorId) return;
  state.history = await api.history(sensorId, 30);
}

async function loadEvents() {
  state.events = await api.events(200);
  return state.events;
}

async function ackEvent(id) {
  const res = await api.ackEvent(id);
  if (res?.ok) {
    const events = state.events ?? [];
    const updatedEvents = events.map((e) => {
      if (e.id === id) {
        return { ...e, acked: true };
      }
      return e;
    });
    state.events = updatedEvents;
    state.updateCounter++; // ✅ 强制更新
  }
  return res;
}

async function loadConfig() {
  state.config = await api.getConfig();
  return state.config;
}

async function saveConfig(patch) {
  state.config = await api.setConfig(patch);
  return state.config;
}

async function ackAllEvents(levels = "warn,alarm") {
  const res = await api.ackAllEvents(levels);
  const ids = res?.ids ?? [];
  if (ids.length) {
    const idset = new Set(ids);
    state.events = (state.events ?? []).map((e) => (idset.has(e.id) ? { ...e, acked: true } : e));
    state.updateCounter++; // ✅ 强制更新
  }
  return res;
}

export async function startStore() {
  if (state.started) return;
  state.started = true;

  try {
    state.sensors = await api.sensors();
    if (!state.sensors.length) {
      initMock();
      return;
    }

    state.selectedId = state.sensors[0]?.id ?? "";

    const latest = await api.latest();
    const map = {};

    for (const r of latest) {
      const value = typeof r.value === "number" ? r.value : parseFloat(r.value ?? 0);
      let battery = typeof r.battery === "number" ? r.battery : parseInt(r.battery ?? 0, 10);

      if (!Number.isFinite(battery) || battery <= 0) {
        battery = 86;
      }

      map[r.sensor_id] = {
        ...r,
        value,
        battery
      };
    }

    state.latestMap = map;
    state.actuators = await api.getActuators();
    await loadHistory(state.selectedId);

    try { await loadEvents(); } catch {}
    try { await loadConfig(); } catch {}

    stopWs = connectWs(
      (m) => {
        if (m?.type === "snapshot") {
          // snapshot 处理
        }

        if (m?.type === "reading") {
          const r = m.data;
          if (!r?.sensor_id) return;

          console.log(`📈 收到传感器数据更新: ${r.sensor_id} = ${r.value}`);

          const prev = state.latestMap[r.sensor_id] || {};
          const value = typeof r.value === "number" ? r.value : parseFloat(r.value ?? prev.value ?? 0);

          let battery = typeof r.battery === "number" ? r.battery : parseInt(r.battery ?? prev.battery ?? 0, 10);
          if (!Number.isFinite(battery) || battery <= 0) {
            battery = prev.battery > 0 ? prev.battery : 86;
          }

          const quality = r.quality || prev.quality || "ok";
          const ts = r.ts || prev.ts || nowISO();

          // ✅ 关键修复1：创建全新的 latestMap 对象
          const newMap = {};
          for (const key in state.latestMap) {
            newMap[key] = state.latestMap[key];
          }

          // ✅ 关键修复2：更新特定传感器的数据
          newMap[r.sensor_id] = {
            sensor_id: r.sensor_id,
            ts,
            value,
            battery,
            quality
          };

          // ✅ 关键修复3：替换整个对象并增加计数器
          state.latestMap = newMap;
          state.updateCounter++;

          if (r.sensor_id === state.selectedId) {
            state.history = [
              ...(state.history || []),
              { sensor_id: r.sensor_id, ts, value }
            ].slice(-300);
          }

          return;
        }

        if (m?.type === "actuators") {
          if (m.data) {
            state.actuators = m.data;
            state.updateCounter++; // ✅ 强制更新
          }
          return;
        }

        if (m?.type === "event") {
          if (m.data) {
            // 1. 先定义 newEvent 对象
            const newEvent = {
              ...m.data,
              id: parseInt(m.data.id || 0),
              value: typeof m.data.value === 'number' ? m.data.value : parseFloat(m.data.value || 0),
              acked: Boolean(m.data.acked)
            };

            // 更新状态列表
            state.events = [newEvent, ...(state.events || [])].slice(0, 200);
            state.updateCounter++;

            if (newEvent.category === 'special_event') {
               // 1. 控制台炫酷输出
               console.log(
                 `%c🔥 触发特殊事件: ${newEvent.message}`,
                 "color: #fff; background: #7c3aed; font-size: 14px; padding: 4px; border-radius: 4px;"
               );

               // 2. 弹窗提醒 (注意：alert会暂时阻塞页面，点击确定后继续)
               alert(`特殊事件触发：${newEvent.message}`);
            }

            // 原有的普通告警打印
            if (m.data.level === 'warn' || m.data.level === 'alarm') {
              console.log('收到新告警事件:', m.data.message);
            }
          }
          return;
        }

        if (m?.type === "config") {
          if (m.data) {
            state.config = m.data;
            state.updateCounter++; // ✅ 强制更新
          }
        }
      },
      (online) => {
        state.wsOnline = online;
        console.log(`WebSocket状态: ${online ? '在线' : '离线'}`);
      }
    );
  } catch (e) {
    initMock();
  }
}

export function useStore() {
  const selectedSensor = computed(() => state.sensors.find((s) => s.id === state.selectedId));

  const qualityCounts = computed(() => {
    // ✅ 添加 updateCounter 依赖，确保每次数据更新都重新计算
    const _ = state.updateCounter;
    const values = Object.values(state.latestMap);
    return {
      ok: values.filter((r) => r?.quality === "ok").length,
      warn: values.filter((r) => r?.quality === "warn").length,
      alarm: values.filter((r) => r?.quality === "alarm").length
    };
  });

  const unackedCount = computed(() => {
    const _ = state.updateCounter; // ✅ 添加依赖
    const es = state.events ?? [];
    return es.filter((e) => !e?.acked && (e?.level === "warn" || e?.level === "alarm")).length;
  });

  async function selectSensor(id) {
    state.selectedId = id;
    if (mockTimer) return;
    await loadHistory(id);
  }

  return {
    state,
    selectedSensor,
    qualityCounts,
    unackedCount,
    selectSensor,
    loadEvents,
    ackEvent,
    loadConfig,
    ackAllEvents,
    saveConfig
  };
}
