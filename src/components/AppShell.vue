<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import {
  LayoutDashboard, Home, LineChart, Bell, Settings, Info,
  Wifi, WifiOff, Zap  // 移除了 Download
} from "lucide-vue-next";
import { useStore } from "../lib/store";

const route = useRoute();
const { state } = useStore();

const title = computed(() => route.meta?.title ?? "室内感知平台");
const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8001";

// 安全地处理 URL 显示
const displayApiBase = computed(() => {
  try {
    const url = new URL(apiBase);
    return `${url.protocol}//${url.host}`;
  } catch {
    return apiBase;
  }
});

const unacked = computed(() => {
  const es = state.events ?? [];
  return es.filter((e) => !e?.acked && (e?.level === "warn" || e?.level === "alarm")).length;
});
</script>

<template>
  <div class="min-h-screen">
    <div class="w-full px-6 py-6 grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
      <aside class="card p-4 h-fit lg:sticky lg:top-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-lg font-semibold">室内感知平台</div>
            <div class="text-xs text-slate-500 mt-1">IoT · 实时 · 可视化</div>
          </div>

          <div
            class="chip"
            :class="
              state.wsOnline
                ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                : 'border-amber-200 bg-amber-50 text-amber-700'
            "
          >
            <span class="inline-flex items-center gap-1">
              <Wifi v-if="state.wsOnline" class="w-3.5 h-3.5" />
              <WifiOff v-else class="w-3.5 h-3.5" />
              {{ state.wsOnline ? "在线" : "重连" }}
            </span>
          </div>
        </div>

        <div class="mt-4 space-y-2">
          <router-link to="/dashboard" class="side-link" :class="$route.path==='/dashboard' ? 'side-link-active':''">
            <LayoutDashboard class="w-4 h-4" /> 总览
          </router-link>

          <router-link to="/rooms" class="side-link" :class="$route.path==='/rooms' ? 'side-link-active':''">
            <Home class="w-4 h-4" /> 房间
          </router-link>

          <router-link to="/analytics" class="side-link" :class="$route.path==='/analytics' ? 'side-link-active':''">
            <LineChart class="w-4 h-4" /> 分析
          </router-link>

          <router-link to="/alerts" class="side-link" :class="$route.path==='/alerts' ? 'side-link-active':''">
            <Bell class="w-4 h-4" />
            <span class="flex-1">告警</span>
            <span v-if="unacked>0" class="chip border-rose-200 bg-rose-50 text-rose-700">
              {{ unacked }}
            </span>
          </router-link>

          <!-- 新增：自动化 -->
          <router-link to="/automation" class="side-link" :class="$route.path==='/automation' ? 'side-link-active':''">
            <Zap class="w-4 h-4" /> 自动化
          </router-link>

          <router-link to="/settings" class="side-link" :class="$route.path==='/settings' ? 'side-link-active':''">
            <Settings class="w-4 h-4" /> 设置
          </router-link>

          <router-link to="/about" class="side-link" :class="$route.path==='/about' ? 'side-link-active':''">
            <Info class="w-4 h-4" /> 关于
          </router-link>
        </div>

        <div class="mt-4 p-3 rounded-2xl bg-slate-50 border border-slate-200">
          <div class="text-xs text-slate-500">后端地址</div>
          <div class="text-sm font-medium text-slate-700 mt-1">{{ displayApiBase }}</div>
        </div>
      </aside>

      <main class="space-y-4">
        <header class="card p-4">
          <div class="flex items-end justify-between">
            <div>
              <div class="text-2xl font-semibold tracking-tight">{{ title }}</div>
              <div class="text-sm text-slate-500 mt-1">模拟数据 + WebSocket 实时推送</div>
            </div>
            <span class="chip border-slate-200 bg-white text-slate-700">传感器 {{ state.sensors.length }}</span>
          </div>
        </header>

        <router-view />
      </main>
    </div>
  </div>
</template>