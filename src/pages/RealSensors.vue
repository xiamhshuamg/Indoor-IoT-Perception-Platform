<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";

const base = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8001";
const data = ref({ ok:false, ts:null, temperature:null, humidity:null, light:null });
let timer = null;

async function tick(){
  try{
    const res = await fetch(`${base}/api/real/latest`, { cache:"no-store" });
    data.value = await res.json();
  }catch(e){
    data.value = { ok:false, ts:null, temperature:null, humidity:null, light:null };
  }
}

onMounted(()=>{
  tick();
  timer = setInterval(tick, 1000);
});
onBeforeUnmount(()=> timer && clearInterval(timer));
</script>

<template>
  <div class="card p-4">
    <div class="text-lg font-semibold">真实传感器（温湿度/光照）</div>
    <div class="text-sm text-slate-500 mt-1">
      状态：<span :class="data.ok ? 'text-emerald-700' : 'text-rose-700'">{{ data.ok ? '在线' : '离线' }}</span>
      <span class="ml-2">ts：{{ data.ts ?? '--' }}</span>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
      <div class="card p-4">
        <div class="text-sm text-slate-500">温度 (°C)</div>
        <div class="text-3xl font-bold mt-2">{{ data.temperature ?? '--' }}</div>
      </div>
      <div class="card p-4">
        <div class="text-sm text-slate-500">湿度 (%)</div>
        <div class="text-3xl font-bold mt-2">{{ data.humidity ?? '--' }}</div>
      </div>
      <div class="card p-4">
        <div class="text-sm text-slate-500">光照 (lx)</div>
        <div class="text-3xl font-bold mt-2">{{ data.light ?? '--' }}</div>
      </div>
    </div>
  </div>
</template>
