<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";
import { fmtTime } from "../lib/utils";

const props = defineProps({ sensor: Object, history: Array });

const el = ref(null);
let chart = null;
let ro = null;
let currentOption = null;

function render() {
  if (!chart) return;
  const h = props.history ?? [];
  const data = h.slice(-240).map((r) => [fmtTime(r.ts), r.value]);

  const newOption = {
    grid: { left: 52, right: 18, top: 48, bottom: 32 },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "rgba(148,163,184,0.35)",
      textStyle: { color: "#0f172a" }
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      axisLabel: { color: "#64748b" },
      axisLine: { lineStyle: { color: "rgba(148,163,184,0.5)" } },
      data: data.map((d) => d[0])
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.25)" } }
    },
    series: [{
      type: "line",
      smooth: true,
      showSymbol: false,
      data: data.map((d) => d[1]),
      areaStyle: { opacity: 0.12 },
      lineStyle: { width: 2 }
    }]
  };

  // 只在实际变化时才更新
  if (JSON.stringify(newOption) !== JSON.stringify(currentOption)) {
    chart.setOption(newOption);
    currentOption = newOption;
  }
}

onMounted(() => {
  if (!el.value) return;
  chart = echarts.init(el.value);
  render();
  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

onBeforeUnmount(() => {
  try { ro?.disconnect(); } catch {}
  try { chart?.dispose(); } catch {}
  chart = null;
  currentOption = null;
});

// 使用 debounce 避免频繁更新
let renderTimer = null;
watch(() => props.history, () => {
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 100);
}, { deep: true });

watch(() => props.sensor?.id, () => {
  if (renderTimer) clearTimeout(renderTimer);
  renderTimer = setTimeout(render, 100);
});
</script>

<template>
  <div class="card p-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <div class="text-lg font-semibold tracking-tight text-slate-900">
          趋势曲线 {{ sensor ? `· ${sensor.room} ${sensor.name}` : "" }}
        </div>
        <div class="text-xs text-slate-500 mt-1">实时更新 · 点击下方/右侧传感器切换</div>
      </div>
      <div class="text-sm text-slate-500">
        单位：<span class="text-slate-800 font-medium">{{ sensor?.unit ?? "--" }}</span>
      </div>
    </div>

    <div ref="el" class="mt-4 h-[260px] w-full"></div>
  </div>
</template>
