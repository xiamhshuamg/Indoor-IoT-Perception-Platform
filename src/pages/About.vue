<template>
  <div class="space-y-4">
    <div class="card p-5">
      <div class="text-2xl font-semibold text-slate-900">关于本系统</div>
      <p class="mt-3 text-slate-600 leading-relaxed">
        这是一个“基于物联网技术的室内感知平台”演示项目：包含传感器数据采集（模拟）、实时推送、趋势分析、告警提示与执行器联动控制。
      </p>
    </div>

    <div class="card p-5">
      <div class="text-lg font-semibold text-slate-900">模块划分</div>
      <ul class="mt-3 text-slate-600 space-y-2">
        <li>• 数据层：后端模拟传感器数据（温湿度/CO₂/PM2.5/光照等）</li>
        <li>• 通信层：REST 获取静态数据 + WebSocket 推送实时数据</li>
        <li>• 展示层：总览 / 房间 / 分析 / 设置 多页面可视化</li>
      </ul>
    </div>
  </div>
</template>
