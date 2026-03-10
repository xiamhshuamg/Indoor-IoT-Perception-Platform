<script setup>
import SensorCard from "./SensorCard.vue";
defineProps({ sensors: Array, latestMap: Object, selectedId: String });
const emit = defineEmits(["select"]);
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
    <SensorCard
        v-for="s in sensors"
        :key="s.id"
        :sensor="s"
        :reading="latestMap?.[s.id]"
        :selected="selectedId === s.id"
        @select="emit('select', s.id)"
    />
  </div>
</template>
