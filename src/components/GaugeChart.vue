<!-- src/components/GaugeChart.vue -->
<template>
  <div class="card p-4">
    <div class="mb-3">
      <div class="text-sm font-semibold text-slate-900">{{ title }}</div>
      <div class="text-xs text-slate-500">{{ subtitle }}</div>
    </div>

    <div
      ref="wrapEl"
      class="relative mx-auto"
      :style="{ width: size + 'px', height: size + 'px' }"
    >
      <div ref="chartEl" class="absolute inset-0"></div>

      <!-- 中心数值（我们自己画，保证好看且统一） -->
      <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <div class="text-3xl font-semibold tracking-tight" :style="{ color: currentColor }">
          {{ formattedValue }}
          <span class="text-sm font-medium text-slate-500 ml-1">{{ unit }}</span>
        </div>

        <div v-if="showStatus" class="mt-2">
          <span
            class="chip"
            :style="{
              borderColor: currentColor + '33',
              backgroundColor: currentColor + '14',
              color: currentColor
            }"
          >
            {{ statusLabel }}
          </span>
        </div>
      </div>
    </div>

    <div class="mt-3 flex justify-between text-xs text-slate-500">
      <span>{{ min }}</span>
      <span>{{ max }}</span>
    </div>

    <!-- 可选：阈值图例（更克制一点） -->
    <div v-if="showThresholds && thresholdsSorted.length" class="mt-3 flex flex-wrap gap-3">
      <div v-for="(t, i) in thresholdsSorted" :key="i" class="inline-flex items-center gap-2">
        <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: t.color }"></span>
        <span class="text-xs text-slate-600">
          {{ t.label ?? `${Math.round(t.position * 100)}%` }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  title: { type: String, default: "仪表盘" },
  subtitle: { type: String, default: "" },
  value: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: "" },
  size: { type: Number, default: 180 },
  strokeWidth: { type: Number, default: 14 },
  thresholds: {
    type: Array,
    default: () => [
      { position: 0.3, color: "#10b981", label: "低" },
      { position: 0.7, color: "#f59e0b", label: "中" },
      { position: 0.9, color: "#ef4444", label: "高" }
    ]
  },
  showThresholds: { type: Boolean, default: true },
  showStatus: { type: Boolean, default: true }
});

const emit = defineEmits(["threshold-reached"]);

const chartEl = ref(null);
const wrapEl = ref(null);
let chart = null;
let ro = null;

const thresholdsSorted = computed(() => {
  const ts = Array.isArray(props.thresholds) ? props.thresholds : [];
  return ts
    .map((t) => ({
      position: Math.max(0, Math.min(1, Number(t.position ?? 0))),
      color: String(t.color || "#64748b"),
      label: t.label
    }))
    .sort((a, b) => a.position - b.position);
});

const clampedValue = computed(() => {
  const v = Number(props.value ?? 0);
  return Math.max(props.min, Math.min(props.max, v));
});

const normalized = computed(() => {
  const denom = (props.max - props.min) || 1;
  return (clampedValue.value - props.min) / denom;
});

const formattedValue = computed(() => {
  const v = clampedValue.value;
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
});

function hexToRgba(hex, alpha = 0.2) {
  const h = String(hex || "").replace("#", "").trim();
  if (h.length !== 6) return `rgba(100,116,139,${alpha})`;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function pickFromThreshold(p, field = "color", fallback = "#6366f1") {
  const ts = thresholdsSorted.value;
  if (!ts.length) return fallback;
  for (const t of ts) {
    if (p <= t.position) return t[field] ?? fallback;
  }
  return ts[ts.length - 1][field] ?? fallback;
}

const currentColor = computed(() => pickFromThreshold(normalized.value, "color", "#6366f1"));

const statusLabel = computed(() => {
  // 优先用 thresholds 的 label（你 Dashboard 里有 “舒适/偏干/过湿”等）
  const lbl = pickFromThreshold(normalized.value, "label", "");
  if (lbl) return lbl;
  // 没配 label 时给一个默认的
  const p = normalized.value;
  if (p < 0.25) return "优";
  if (p < 0.55) return "良";
  return "差";
});

const axisLineStops = computed(() => {
  if (!props.showThresholds || !thresholdsSorted.value.length) {
    return [[1, "rgba(226,232,240,1)"]];
  }
  const ts = thresholdsSorted.value;
  const stops = ts.map((t) => [t.position, hexToRgba(t.color, 0.22)]);
  const last = stops[stops.length - 1]?.[0] ?? 1;
  if (last < 1) stops.push([1, hexToRgba(ts[ts.length - 1].color, 0.22)]);
  return stops;
});

function render() {
  if (!chart) return;

  const option = {
    animation: true,
    animationDuration: 650,
    animationEasing: "cubicOut",
    series: [
      {
        type: "gauge",
        startAngle: 225,
        endAngle: -45,
        min: props.min,
        max: props.max,
        splitNumber: 5,
        center: ["50%", "55%"],
        radius: "92%",

        axisLine: {
          roundCap: true,
          lineStyle: {
            width: props.strokeWidth,
            color: axisLineStops.value
          }
        },

        progress: {
          show: true,
          roundCap: true,
          width: props.strokeWidth,
          itemStyle: { color: currentColor.value }
        },

        pointer: {
          length: "62%",
          width: 4,
          itemStyle: { color: currentColor.value }
        },

        anchor: {
          show: true,
          size: 10,
          showAbove: true,
          itemStyle: {
            color: currentColor.value,
            borderColor: "#fff",
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: hexToRgba(currentColor.value, 0.25)
          }
        },

        axisTick: { show: false },
        axisLabel: { show: false },

        splitLine: {
          show: true,
          distance: -props.strokeWidth - 6,
          length: 10,
          lineStyle: { color: "rgba(148,163,184,0.35)", width: 2 }
        },

        title: { show: false },
        detail: { show: false },

        data: [{ value: clampedValue.value }]
      }
    ]
  };

  chart.setOption(option, { notMerge: true, lazyUpdate: true });
}

let prev = null;
watch(
  () => normalized.value,
  (nv, ov) => {
    // 跨阈值触发一次事件
    if (typeof ov === "number") {
      for (const t of thresholdsSorted.value) {
        if (ov < t.position && nv >= t.position) {
          emit("threshold-reached", { threshold: t, value: clampedValue.value, normalized: nv });
        }
      }
    }
    prev = nv;
    render();
  }
);

watch(
  () => [props.min, props.max, props.size, props.strokeWidth, props.showThresholds, props.thresholds],
  () => render(),
  { deep: true }
);

onMounted(() => {
  if (!chartEl.value) return;
  chart = echarts.init(chartEl.value);
  render();

  ro = new ResizeObserver(() => chart?.resize());
  if (wrapEl.value) ro.observe(wrapEl.value);
});

onBeforeUnmount(() => {
  try {
    ro?.disconnect();
  } catch {}
  try {
    chart?.dispose();
  } catch {}
  chart = null;
});
</script>
