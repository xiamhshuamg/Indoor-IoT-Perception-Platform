<script setup>
import { Activity, Wifi, WifiOff } from "lucide-vue-next";
defineProps({ title: String, subtitle: String, wsOnline: Boolean });
</script>

<template>
  <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
    <div class="flex items-start gap-3">
      <div class="glass shadow-soft rounded-2xl p-3">
        <Activity class="h-6 w-6" />
      </div>
      <div>
        <div class="text-2xl md:text-3xl font-semibold tracking-tight">{{ title }}</div>
        <div class="text-zinc-300/80 text-sm mt-1">{{ subtitle }}</div>
      </div>
    </div>

    <div class="glass shadow-soft rounded-2xl px-4 py-3 flex items-center gap-2">
      <Wifi v-if="wsOnline" class="h-4 w-4" />
      <WifiOff v-else class="h-4 w-4" />
      <span class="text-sm text-zinc-200">{{ wsOnline ? "实时连接正常" : "正在重连..." }}</span>
    </div>
  </div>
</template>
