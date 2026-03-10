<script setup>
defineProps({
  title: String,
  value: [String, Number],
  hint: String,
  tone: { type: String, default: "slate" } // slate/indigo/emerald/amber/rose
});
</script>

<template>
  <div class="card card-hover p-4">
    <div class="text-sm text-slate-500">{{ title }}</div>
    <div class="mt-2 text-2xl font-semibold" :class="`text-${tone}-700`">{{ value }}</div>
    <div v-if="hint" class="mt-2 text-xs text-slate-500">{{ hint }}</div>
  </div>
</template>
