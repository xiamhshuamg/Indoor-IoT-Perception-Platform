<script setup>
import { Thermometer, Droplets, Sun, Wind, Sparkles, Volume2, Users } from "lucide-vue-next";
const props = defineProps({ sensor: Object, reading: Object, selected: Boolean });
const emit = defineEmits(["select"]);

function iconOf(type) {
  switch (type) {
    case "temperature": return Thermometer;
    case "humidity": return Droplets;
    case "light": return Sun;
    case "co2": return Wind;
    case "pm25": return Sparkles;
    case "noise": return Volume2;
    case "occupancy": return Users;
    default: return Sparkles;
  }
}
function badge(quality) {
  if (quality === "ok") return { text: "正常", cls: "border-emerald-200 bg-emerald-50 text-emerald-700" };
  if (quality === "warn") return { text: "注意", cls: "border-amber-200 bg-amber-50 text-amber-700" };
  return { text: "告警", cls: "border-rose-200 bg-rose-50 text-rose-700" };
}
</script>

<template>
  <button class="card card-hover p-4 w-full text-left"
          :class="selected ? 'ring-2 ring-indigo-200' : ''"
          @click="emit('select')">
    <div class="flex items-start justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="rounded-2xl p-2 bg-slate-50 border border-slate-200">
          <component :is="iconOf(sensor.type)" class="h-5 w-5 text-slate-700" />
        </div>
        <div>
          <div class="text-sm text-slate-800 font-medium">{{ sensor.room }} · {{ sensor.name }}</div>
          <div class="text-xs text-slate-500 mt-0.5">{{ sensor.id }}</div>
        </div>
      </div>

      <div class="chip" :class="badge(reading?.quality ?? 'ok').cls">
        {{ badge(reading?.quality ?? 'ok').text }}
      </div>
    </div>

    <div class="mt-4 flex items-end justify-between">
      <div class="text-3xl font-semibold tracking-tight text-slate-900">
        {{ reading ? reading.value : "--" }}
        <span class="text-sm font-medium text-slate-500 ml-1">{{ sensor.unit }}</span>
      </div>
      <div class="text-xs text-slate-500">电量 <span class="text-slate-700 font-medium">{{ reading ? reading.battery : "--" }}%</span></div>
    </div>

    <div class="mt-3 text-xs text-slate-500">
      阈值：{{ sensor.warn_low ?? "—" }} ~ {{ sensor.warn_high ?? "—" }} {{ sensor.unit }}
    </div>
  </button>
</template>
