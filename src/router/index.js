// src/router/index.js
import { createRouter, createWebHistory } from "vue-router";
import AppShell from "../components/AppShell.vue";

import Dashboard from "../pages/Dashboard.vue";
import Rooms from "../pages/Rooms.vue";
import Analytics from "../pages/Analytics.vue";
import Alerts from "../pages/Alerts.vue";
import Settings from "../pages/Settings.vue";
import About from "../pages/About.vue";
import Automation from "../pages/Automation.vue";

const routes = [
  {
    path: "/",
    component: AppShell,
    children: [
      { path: "", redirect: "/dashboard" },
      { path: "dashboard", component: Dashboard, meta: { title: "总览" } },
      { path: "rooms", component: Rooms, meta: { title: "房间" } },
      { path: "analytics", component: Analytics, meta: { title: "分析" } },
      { path: "alerts", component: Alerts, meta: { title: "告警" } },
      { path: "automation", component: Automation, meta: { title: "自动化" } },
      { path: "settings", component: Settings, meta: { title: "设置" } },
      { path: "about", component: About, meta: { title: "关于" } }
    ]
  }
];

export default createRouter({
  history: createWebHistory(),
  routes
});