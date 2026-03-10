<script setup>
import { ref } from "vue";
import { api } from "../lib/api";
import { Lightbulb, Fan, Sparkles, Thermometer } from "lucide-vue-next";

const props = defineProps({ actuators: Object });
const emit = defineEmits(["updated"]);
const saving = ref(false);

async function patch(p) {
  saving.value = true;
  try {
    const a = await api.setActuators(p);
    emit("updated", a);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="card p-4">
    <div class="flex items-end justify-between gap-3">
      <div>
        <div class="text-lg font-semibold tracking-tight text-slate-900">执行器控制（联动模拟）</div>
        <div class="text-xs text-slate-500 mt-1">新风降低 CO₂；净化器降低 PM2.5；灯提高光照；目标温度影响温度</div>
      </div>
      <div class="chip"
           :class="saving ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-slate-200 bg-white text-slate-600'">
        {{ saving ? "保存中…" : "可操作" }}
      </div>
    </div>

    <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
      <button class="btn justify-between" @click="patch({ lights: !props.actuators?.lights })">
        <span class="inline-flex items-center gap-2"><Lightbulb class="w-4 h-4" /> 灯光</span>
        <span class="chip" :class="props.actuators?.lights ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'">
          {{ props.actuators?.lights ? "ON" : "OFF" }}
        </span>
      </button>

      <button class="btn justify-between" @click="patch({ ventilation: !props.actuators?.ventilation })">
        <span class="inline-flex items-center gap-2"><Fan class="w-4 h-4" /> 新风</span>
        <span class="chip" :class="props.actuators?.ventilation ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'">
          {{ props.actuators?.ventilation ? "ON" : "OFF" }}
        </span>
      </button>

      <button class="btn justify-between" @click="patch({ purifier: !props.actuators?.purifier })">
        <span class="inline-flex items-center gap-2"><Sparkles class="w-4 h-4" /> 净化</span>
        <span class="chip" :class="props.actuators?.purifier ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-600'">
          {{ props.actuators?.purifier ? "ON" : "OFF" }}
        </span>
      </button>
    </div>

    <div class="mt-4 p-4 rounded-2xl bg-slate-50 border border-slate-200">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-slate-700">
          <Thermometer class="h-4 w-4" />
          <div class="text-sm font-medium">目标温度</div>
        </div>
        <div class="text-sm text-slate-900 font-semibold">{{ Number(props.actuators?.target_temp ?? 24).toFixed(1) }} °C</div>
      </div>

      <input class="mt-3 w-full accent-indigo-600" type="range" min="16" max="30" step="0.5"
             :value="props.actuators?.target_temp ?? 24"
             @input="(e) => patch({ target_temp: Number(e.target.value) })"/>
      <div class="text-xs text-slate-500 mt-2">范围 16~30°C</div>
    </div>
  </div>
</template>
