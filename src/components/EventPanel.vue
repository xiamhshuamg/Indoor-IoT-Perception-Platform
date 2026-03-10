<template>
  <div class="card p-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Bell class="w-4 h-4 text-slate-700" />
        <div class="text-lg font-semibold text-slate-900">告警 / 日志</div>
      </div>
      <button class="btn btn-primary" @click="router.push('/alerts')">查看全部</button>
    </div>

    <div v-if="!shown.length" class="text-sm text-slate-500 mt-3">
      暂无事件
    </div>

<div v-else class="mt-3 space-y-2">
    <div
      v-for="e in shown"
      :key="e.id"
      class="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 px-3 py-2"
      :class="e.category === 'special_event' ? 'bg-violet-50/30' : ''"
    >
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <Sparkles v-if="e.category === 'special_event'" class="w-3.5 h-3.5 text-violet-600" />

          <span class="chip" :class="chipClass(e)">
             {{ e.category === 'special_event' ? '特殊事件' : e.level }}
          </span>

          <span class="text-xs text-slate-500">{{ fmtTime(e.ts) }}</span>
          </div>
          <div class="text-sm text-slate-800 mt-1 break-words">
            {{ e.message }}
          </div>
        </div>

        <!-- 确认按钮 -->
        <button v-if="!e.acked" class="btn" @click="handleAck(e.id)">确认</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Bell, CheckCircle2, Sparkles } from "lucide-vue-next";
import { computed } from "vue";
import { useRouter } from "vue-router";
import { fmtTime } from "../lib/utils";

const props = defineProps({
  events: { type: Array, default: () => [] },
  limit: { type: Number, default: 8 }
});

const emit = defineEmits(["ack"]);

const router = useRouter();

const shown = computed(() => (props.events ?? []).slice(0, props.limit));

// 处理确认操作
function handleAck(eventId) {
  emit('ack', eventId);
}

function chipClass(e) {
  // ✅ 新增：特殊事件使用紫色样式
  if (e?.category === "special_event") return "border-violet-200 bg-violet-50 text-violet-700 font-bold";

  if (e?.level === "alarm") return "border-rose-200 bg-rose-50 text-rose-700";
  if (e?.level === "warn") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}
</script>
