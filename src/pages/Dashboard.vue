<script setup>
import { computed, ref, watch } from "vue";
import KPIStat from "../components/KPIStat.vue";
import TrendPanel from "../components/TrendPanel.vue";
import SensorGrid from "../components/SensorGrid.vue";
import ActuatorPanel from "../components/ActuatorPanel.vue";
import ReadingTable from "../components/ReadingTable.vue";
import EventPanel from "../components/EventPanel.vue";
import GaugeChart from "../components/GaugeChart.vue";
import BarChart from "../components/BarChart.vue";
import { useStore } from "../lib/store";

const { state, selectedSensor, qualityCounts, selectSensor, ackEvent } = useStore();

// ✅ 修复：添加 updateCounter 依赖
const avgTemp = computed(() => {
  const _ = state.updateCounter; // 强制依赖
  const temps = state.sensors
    .filter((s) => s.type === "temperature")
    .map((s) => {
      const val = state.latestMap?.[s.id]?.value;
      return typeof val === "number" ? val : null;
    })
    .filter((v) => v !== null);

  if (temps.length === 0) return 0;
  const avg = temps.reduce((a, b) => a + b, 0) / temps.length;
  return Number(avg.toFixed(1));
});

const avgHumidity = computed(() => {
  const _ = state.updateCounter; // 强制依赖
  const hums = state.sensors
    .filter((s) => s.type === "humidity")
    .map((s) => {
      const val = state.latestMap?.[s.id]?.value;
      return typeof val === "number" ? val : null;
    })
    .filter((v) => v !== null);

  if (hums.length === 0) return 0;
  const avg = hums.reduce((a, b) => a + b, 0) / hums.length;
  return Number(avg.toFixed(1));
});

const totalSensors = computed(() => state.sensors.length || 12);

const realQualityCounts = computed(() => {
  const _ = state.updateCounter; // 强制依赖
  const events = state.events || [];
  const unackedEvents = events.filter(e => !e.acked);

  return {
    ok: 0,
    warn: unackedEvents.filter(e => e.level === "warn").length,
    alarm: unackedEvents.filter(e => e.level === "alarm").length
  };
});

const roomStats = computed(() => {
  const _ = state.updateCounter; // ✅ 强制依赖
  const rooms = {};
  const allRooms = ["客厅", "卧室"];

  allRooms.forEach(room => {
    rooms[room] = {
      sensors: [],
      avgTemp: 0,
      avgHumidity: 0,
      warnings: 0,
      alarms: 0,
      tempValues: [],
      humidityValues: []
    };
  });

  state.sensors.forEach(sensor => {
    const room = sensor.room;
    if (!rooms[room]) return;

    const reading = state.latestMap?.[sensor.id];
    rooms[room].sensors.push(sensor);

    if (reading) {
      if (sensor.type === 'temperature') {
        rooms[room].tempValues.push(reading.value);
      } else if (sensor.type === 'humidity') {
        rooms[room].humidityValues.push(reading.value);
      }

      if (reading.quality === 'warn') rooms[room].warnings++;
      if (reading.quality === 'alarm') rooms[room].alarms++;
    }
  });

  allRooms.forEach(room => {
    const roomData = rooms[room];

    if (roomData.tempValues.length > 0) {
      const sum = roomData.tempValues.reduce((a, b) => a + b, 0);
      roomData.avgTemp = Number((sum / roomData.tempValues.length).toFixed(1));
    } else {
      roomData.avgTemp = room === "客厅" ? 22.5 : 21.5;
    }

    if (roomData.humidityValues.length > 0) {
      const sum = roomData.humidityValues.reduce((a, b) => a + b, 0);
      roomData.avgHumidity = Number((sum / roomData.humidityValues.length).toFixed(1));
    } else {
      roomData.avgHumidity = room === "客厅" ? 55 : 50;
    }
  });

  return rooms;
});

const barChartData = computed(() => {
  const stats = roomStats.value;
  const categories = Object.keys(stats);

  if (categories.length === 0) {
    return {
      categories: ["客厅", "卧室"],
      series: [
        { name: '平均温度 (°C)', data: [22.5, 21.5], itemStyle: { color: '#ef4444' } },
        { name: '平均湿度 (%)', data: [55, 50], itemStyle: { color: '#3b82f6' } }
      ]
    };
  }

  const tempData = categories.map(room => stats[room].avgTemp);
  const humidityData = categories.map(room => stats[room].avgHumidity);

  return {
    categories,
    series: [
      { name: '平均温度 (°C)', data: tempData, itemStyle: { color: '#ef4444' } },
      { name: '平均湿度 (%)', data: humidityData, itemStyle: { color: '#3b82f6' } }
    ]
  };
});

// ✅ 监听数据变化（调试用）
watch(() => state.updateCounter, (newVal) => {
  console.log('🔄 数据更新计数器:', newVal);
});
</script>


<template>
  <div class="space-y-4">
    <!-- 修复KPIStat组件，使用 realQualityCounts -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <KPIStat title="传感器总数" :value="totalSensors" hint="客厅6个 + 卧室6个" tone="indigo" />
      <KPIStat title="平均温度(°C)" :value="avgTemp" hint="所有温度传感器均值" tone="emerald" />
      <KPIStat title="告警(ALARM)" :value="realQualityCounts.alarm" hint="需要立即处理" tone="rose" />
      <KPIStat title="注意(WARN)" :value="realQualityCounts.warn" hint="建议关注" tone="amber" />
    </div>

    <!-- 仪表盘区域 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <GaugeChart
        title="客厅温度"
        :value="state.latestMap?.['T-101']?.value || 22.5"
        :min="16"
        :max="30"
        unit="°C"
        :thresholds="[
          { position: 0.3, color: '#10b981', label: '舒适' },
          { position: 0.7, color: '#f59e0b', label: '偏高' },
          { position: 0.9, color: '#ef4444', label: '过高' }
        ]"
      />

      <GaugeChart
        title="客厅湿度"
        :value="state.latestMap?.['H-101']?.value || 55"
        :min="20"
        :max="80"
        unit="%"
        :thresholds="[
          { position: 0.25, color: '#f59e0b', label: '偏干' },
          { position: 0.4, color: '#10b981', label: '舒适' },
          { position: 0.75, color: '#f59e0b', label: '偏湿' },
          { position: 0.9, color: '#ef4444', label: '过湿' }
        ]"
      />

      <GaugeChart
        title="CO₂浓度"
        :value="state.latestMap?.['C-101']?.value || 800"
        :min="350"
        :max="2000"
        unit="ppm"
        :thresholds="[
          { position: 0.3, color: '#10b981', label: '优' },
          { position: 0.6, color: '#f59e0b', label: '良' },
          { position: 0.8, color: '#ef4444', label: '差' }
        ]"
      />
    </div>

    <!-- 柱状图区域 -->
    <div class="card p-4">
      <div class="text-lg font-semibold text-slate-900 mb-4">各房间环境指标对比</div>
      <BarChart
        :title="'房间环境指标'"
        :subtitle="'对比各房间平均温湿度'"
        :categories="barChartData.categories"
        :series="barChartData.series"
        :height="300"
        :stacked="false"
      />
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div class="xl:col-span-2">
        <TrendPanel :sensor="selectedSensor" :history="state.history" />
      </div>
      <div class="xl:col-span-1">
        <ActuatorPanel :actuators="state.actuators" @updated="(a) => (state.actuators = a)" />
      </div>
    </div>

    <EventPanel :events="state.events" @ack="ackEvent" />

    <div class="card p-4">
      <div class="flex items-center justify-between">
        <div class="text-lg font-semibold text-slate-900">传感器总览（{{ totalSensors }}个）</div>
        <div class="text-sm text-slate-500">点击卡片切换趋势，支持客厅/卧室所有传感器</div>
      </div>
      <div class="mt-4">
        <SensorGrid
          :sensors="state.sensors"
          :latestMap="state.latestMap"
          :selectedId="state.selectedId"
          @select="selectSensor"
        />
      </div>
    </div>

    <ReadingTable :sensors="state.sensors" :latestMap="state.latestMap" />
  </div>
</template>