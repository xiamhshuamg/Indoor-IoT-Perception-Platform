<!-- src/components/BarChart.vue -->
<template>
  <div class="card p-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <div class="text-sm font-semibold text-slate-900">{{ title }}</div>
        <div class="text-xs text-slate-500">{{ subtitle }}</div>
      </div>

      <div v-if="showLegend" class="flex flex-wrap gap-3">
        <div v-for="item in legendItems" :key="item.name" class="inline-flex items-center gap-2">
          <span class="h-2.5 w-2.5 rounded-full" :style="{ backgroundColor: item.color }"></span>
          <span class="text-xs text-slate-600">{{ item.name }}</span>
        </div>
      </div>
    </div>

    <div ref="chartRef" class="mt-3 w-full" :style="{ height: height + 'px' }"></div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  title: { type: String, default: "柱状图" },
  subtitle: { type: String, default: "" },
  data: { type: Array, default: () => [] },
  categories: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  height: { type: Number, default: 300 },
  colors: {
    type: Array,
    default: () => ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
  },
  showLegend: { type: Boolean, default: true },
  horizontal: { type: Boolean, default: false },
  stacked: { type: Boolean, default: false }
});

const chartRef = ref(null);
let chart = null;
let ro = null;
let timer = null;

const builtSeries = computed(() => {
  if (props.series?.length) return props.series;
  return [
    {
      name: "数值",
      type: "bar",
      data: props.data,
      itemStyle: { color: props.colors[0] }
    }
  ];
});

const legendItems = computed(() =>
  (builtSeries.value || []).map((s, idx) => ({
    name: s.name ?? `系列${idx + 1}`,
    color: s.itemStyle?.color ?? props.colors[idx % props.colors.length]
  }))
);

function render() {
  if (!chart) return;

  const radius = props.horizontal ? [6, 10, 10, 6] : [10, 10, 4, 4];

  const option = {
    animation: true,
    animationDuration: 600,
    animationEasing: "cubicOut",
    grid: { left: 40, right: 16, top: 16, bottom: 24, containLabel: true },

    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(255,255,255,0.96)",
      borderColor: "rgba(148,163,184,0.35)",
      textStyle: { color: "#0f172a" }
    },

    xAxis: {
      type: props.horizontal ? "value" : "category",
      data: props.horizontal ? undefined : props.categories,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: "#64748b" },
      splitLine: { show: false }
    },

    yAxis: {
      type: props.horizontal ? "category" : "value",
      data: props.horizontal ? props.categories : undefined,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: "#64748b" },
      splitLine: { lineStyle: { color: "rgba(148,163,184,0.22)", type: "dashed" } }
    },

    // 禁用 echarts 自带 legend（我们用更干净的自定义 legend）
    legend: { show: false },

    series: builtSeries.value.map((s, idx) => ({
      ...s,
      type: "bar",
      stack: props.stacked ? (s.stack ?? "total") : s.stack,
      barMaxWidth: 28,
      barCategoryGap: "45%",
      itemStyle: {
        borderRadius: radius,
        ...(s.itemStyle || { color: props.colors[idx % props.colors.length] })
      },
      showBackground: true,
      backgroundStyle: { color: "rgba(148,163,184,0.10)" },
      label: {
        show: true,
        position: props.horizontal ? "right" : "top",
        color: "#64748b",
        fontSize: 11
      },
      emphasis: {
        focus: "series",
        itemStyle: { opacity: 0.92 }
      }
    }))
  };

  chart.setOption(option, { notMerge: true, lazyUpdate: true });
}

onMounted(() => {
  if (!chartRef.value) return;
  chart = echarts.init(chartRef.value);
  render();

  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(chartRef.value);
});

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer);
  try {
    ro?.disconnect();
  } catch {}
  try {
    chart?.dispose();
  } catch {}
  chart = null;
});

watch(
  () => [
    props.data,
    props.categories,
    props.series,
    props.height,
    props.horizontal,
    props.stacked,
    props.colors
  ],
  () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(render, 60);
  },
  { deep: true }
);
</script>
