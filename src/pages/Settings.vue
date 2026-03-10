<script setup>
import { ref, watch } from "vue";
import ActuatorPanel from "../components/ActuatorPanel.vue";
import { useStore } from "../lib/store";

const { state, loadConfig, saveConfig } = useStore();

const saving = ref(false);
const draft = ref(null);

// 把后端 config 拷贝一份做编辑（避免直接改 state.config）
watch(
  () => state.config,
  (c) => {
    if (!c) {
      draft.value = null;
      return;
    }
    draft.value = JSON.parse(JSON.stringify(c));
  },
  { immediate: true }
);

async function reload() {
  try {
    await loadConfig();
  } catch (e) {
    console.error(e);
    alert("读取配置失败：请确认后端已启动并且 VITE_API_BASE 指向正确端口");
  }
}

async function save() {
  if (!draft.value) return;

  const patch = {
    interval: Number(draft.value.interval),
    sensors: (draft.value.sensors ?? []).map((s) => ({
      id: s.id,
      warn_low: Number(s.warn_low),
      warn_high: Number(s.warn_high),
      gen_low: Number(s.gen_low),
      gen_high: Number(s.gen_high),
      step: Number(s.step)
    }))
  };

  saving.value = true;
  try {
    await saveConfig(patch);
    alert("已保存：后端会按新范围/阈值重新生成数据");
  } catch (e) {
    console.error(e);
    alert("保存失败：请查看后端终端输出");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="card p-4">
      <div class="text-lg font-semibold text-slate-900">系统设置</div>
      <div class="text-sm text-slate-500 mt-1">用于演示执行器联动 + 后端模拟配置</div>
    </div>

    <ActuatorPanel :actuators="state.actuators" @updated="(a) => (state.actuators = a)" />

    <!-- ✅ 新增：后端模拟配置 -->
    <div class="card p-4">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-sm font-semibold text-slate-900">后端模拟配置</div>
          <div class="text-sm text-slate-500 mt-1">可修改采样周期/阈值/生成范围（保存后立即生效）</div>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn" @click="reload">刷新</button>
          <button class="btn btn-primary" :disabled="saving || !draft" @click="save">
            {{ saving ? "保存中..." : "保存" }}
          </button>
        </div>
      </div>

      <div v-if="!draft" class="text-sm text-slate-500 mt-3">
        未获取到后端配置。请确认后端已更新并启动（/api/config 可访问）。
      </div>

      <div v-else class="mt-4 space-y-4">
        <div class="flex items-center gap-3">
          <div class="text-sm text-slate-700 w-28">采样周期</div>
          <input
            class="btn w-28 justify-start"
            type="number"
            min="0.2"
            max="10"
            step="0.1"
            v-model="draft.interval"
          />
          <div class="text-sm text-slate-500">秒（越小更新越快）</div>
        </div>

        <div class="overflow-auto">
          <table class="w-full text-sm">
            <thead class="text-slate-500">
              <tr class="border-b">
                <th class="py-2 text-left font-medium">ID</th>
                <th class="py-2 text-left font-medium">位置</th>
                <th class="py-2 text-left font-medium">类型</th>
                <th class="py-2 text-left font-medium">warn_low</th>
                <th class="py-2 text-left font-medium">warn_high</th>
                <th class="py-2 text-left font-medium">gen_low</th>
                <th class="py-2 text-left font-medium">gen_high</th>
                <th class="py-2 text-left font-medium">step</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="s in draft.sensors"
                :key="s.id"
                class="border-b last:border-b-0 hover:bg-slate-50"
              >
                <td class="py-2 font-mono text-slate-700">{{ s.id }}</td>
                <td class="py-2 text-slate-700 whitespace-nowrap">{{ s.room }}·{{ s.name }}</td>
                <td class="py-2 text-slate-700 whitespace-nowrap">{{ s.type }}</td>

                <td class="py-2">
                  <input class="btn w-28 justify-start" type="number" step="0.1" v-model="s.warn_low" />
                </td>
                <td class="py-2">
                  <input class="btn w-28 justify-start" type="number" step="0.1" v-model="s.warn_high" />
                </td>
                <td class="py-2">
                  <input class="btn w-28 justify-start" type="number" step="0.1" v-model="s.gen_low" />
                </td>
                <td class="py-2">
                  <input class="btn w-28 justify-start" type="number" step="0.1" v-model="s.gen_high" />
                </td>
                <td class="py-2">
                  <input class="btn w-28 justify-start" type="number" step="0.1" v-model="s.step" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="text-xs text-slate-500">
          建议：gen 范围决定数据可能出现的上下限；warn 阈值决定什么时候触发 warn/alarm；step 决定随机波动幅度。
        </div>
      </div>
    </div>

    <div class="card p-4">
      <div class="text-sm font-semibold text-slate-900">说明</div>
      <div class="text-sm text-slate-600 mt-2">
        本项目前端为可视化展示层，数据由后端模拟生成并通过 WebSocket 实时推送。
      </div>
    </div>
  </div>
</template>
