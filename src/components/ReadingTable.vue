<script setup>
defineProps({
  sensors: Array,
  latestMap: Object
});
</script>

<template>
  <div class="card p-4">
    <div class="flex items-center justify-between">
      <div class="text-lg font-semibold text-slate-900">实时数据表</div>
      <div class="text-sm text-slate-500">用于展示全部传感器最新值</div>
    </div>

    <div class="mt-4 overflow-auto">
      <table class="w-full text-sm">
        <thead class="text-slate-500">
          <tr class="border-b border-slate-200">
            <th class="py-2 text-left font-medium">房间</th>
            <th class="py-2 text-left font-medium">传感器</th>
            <th class="py-2 text-left font-medium">类型</th>
            <th class="py-2 text-left font-medium">最新值</th>
            <th class="py-2 text-left font-medium">电量</th>
            <th class="py-2 text-left font-medium">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sensors" :key="s.id" class="border-b border-slate-100">
            <td class="py-2">{{ s.room }}</td>
            <td class="py-2">
              <div class="font-medium text-slate-800">{{ s.name }}</div>
              <div class="text-xs text-slate-500">{{ s.id }}</div>
            </td>
            <td class="py-2 text-slate-700">{{ s.type }}</td>
            <td class="py-2 font-semibold text-slate-900">
              {{ latestMap?.[s.id]?.value ?? "--" }} <span class="text-xs text-slate-500">{{ s.unit }}</span>
            </td>
            <td class="py-2">{{ latestMap?.[s.id]?.battery ?? "--" }}%</td>
            <td class="py-2">
              <span class="chip"
                :class="latestMap?.[s.id]?.quality==='ok' ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : latestMap?.[s.id]?.quality==='warn' ? 'border-amber-200 bg-amber-50 text-amber-700'
                      : 'border-rose-200 bg-rose-50 text-rose-700'">
                {{ latestMap?.[s.id]?.quality ?? "ok" }}
              </span>
            </td>
          </tr>

          <tr v-if="!sensors?.length">
            <td class="py-6 text-slate-500" colspan="6">
              暂无传感器数据（后端为空或未启动）。下面我已经给你加了“自动模拟数据”，刷新后会有数据。
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
