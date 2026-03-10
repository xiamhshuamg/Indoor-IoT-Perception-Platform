<script setup>
import { computed, ref } from "vue";
import { fmtTime } from "../lib/utils";
import { useStore } from "../lib/store";
import { Bell, RefreshCw } from "lucide-vue-next";

const { state, ackEvent, loadEvents, ackAllEvents } = useStore();

const tab = ref("unacked"); // unacked | acked | all

const filtered = computed(() => {
  const es = state.events ?? [];

  // ✅ 可选：把旧的“ 一键确认：X条 ”日志也隐藏（防止历史里还有）
  const cleaned = es.filter((e) => !(e?.category === "event" && String(e?.message || "").startsWith("一键确认")));

  if (tab.value === "unacked") return cleaned.filter((e) => !e?.acked);
  if (tab.value === "acked") return cleaned.filter((e) => e?.acked);
  return cleaned;
});

function chipClass(e) {
  if (e?.level === "alarm") return "border-rose-200 bg-rose-50 text-rose-700";
  if (e?.level === "warn") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

async function refresh() {
  try {
    await loadEvents();
  } catch (e) {
    console.error(e);
  }
}

</script>

<template>
  <div class="space-y-4">
    <div class="card p-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="flex items-center gap-2">
            <Bell class="w-4 h-4 text-slate-700" />
            <div class="text-lg font-semibold text-slate-900">告警中心</div>
          </div>
          <div class="text-sm text-slate-500 mt-1">后端模拟产生的告警/日志，可确认(ack)</div>
        </div>

<div class="flex items-center gap-2">
  <button class="btn" @click="refresh">
    <RefreshCw class="w-4 h-4" /> 刷新
  </button>

  <button class="btn" :class="tab==='unacked' ? 'btn-primary' : ''" @click="tab='unacked'">未确认</button>
  <button class="btn" :class="tab==='acked' ? 'btn-primary' : ''" @click="tab='acked'">确认</button>
  <button class="btn" :class="tab==='all' ? 'btn-primary' : ''" @click="tab='all'">全部</button>

  <button class="btn btn-primary" @click="ackAllEvents('warn,alarm')">全部确认</button>
</div>
      </div>
    </div>

    <div class="card p-4">
      <div class="mt-2 overflow-auto">
        <table class="w-full text-sm">
          <thead class="text-slate-500">
            <tr class="border-b">
              <th class="py-2 text-left font-medium">时间</th>
              <th class="py-2 text-left font-medium">等级</th>
              <th class="py-2 text-left font-medium">类别</th>
              <th class="py-2 text-left font-medium">内容</th>
              <th class="py-2 text-right font-medium">操作</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="!filtered.length">
              <td colspan="5" class="py-6 text-center text-slate-500">暂无数据</td>
            </tr>

            <tr
              v-for="e in filtered"
              :key="e.id"
              class="border-b last:border-b-0 hover:bg-slate-50"
            >
              <td class="py-2 text-slate-700 whitespace-nowrap">{{ fmtTime(e.ts) }}</td>
              <td class="py-2">
                <span class="chip" :class="chipClass(e)">{{ e.level }}</span>
              </td>
              <td class="py-2 text-slate-700 whitespace-nowrap">{{ e.category }}</td>
              <td class="py-2 text-slate-800">{{ e.message }}</td>
              <td class="py-2 text-right">
                <span v-if="e.acked" class="text-xs text-emerald-700">已确认</span>
                <button v-else class="btn" @click="ackEvent(e.id)">确认</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="text-xs text-slate-500 mt-3">
        提示：告警会通过 WebSocket 实时推送到前端；你也可以点击“刷新”从 REST 拉取最新列表。
      </div>
    </div>
  </div>
</template>
