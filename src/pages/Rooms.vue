<script setup>
import { computed, ref } from "vue";
import TrendPanel from "../components/TrendPanel.vue";
import SensorGrid from "../components/SensorGrid.vue";
import { useStore } from "../lib/store";

const { state, selectedSensor, selectSensor } = useStore();
const room = ref("全部");

const rooms = computed(() => ["全部", ...Array.from(new Set(state.sensors.map(s => s.room))).filter(Boolean)]);
const filtered = computed(() => room.value === "全部" ? state.sensors : state.sensors.filter(s => s.room === room.value));
</script>

<template>
  <div class="space-y-4">
    <div class="card p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div>
        <div class="text-lg font-semibold text-slate-900">按房间查看</div>
        <div class="text-sm text-slate-500 mt-1">选择房间过滤传感器</div>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm text-slate-600">房间</span>
        <select v-model="room" class="btn">
          <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-4">
      <div class="xl:col-span-2">
        <div class="card p-4">
          <div class="text-sm text-slate-500 mb-3">当前房间：{{ room }}</div>
          <SensorGrid :sensors="filtered" :latestMap="state.latestMap" :selectedId="state.selectedId" @select="selectSensor" />
        </div>
      </div>
      <div class="xl:col-span-1">
        <TrendPanel :sensor="selectedSensor" :history="state.history" />
      </div>
    </div>
  </div>
</template>
