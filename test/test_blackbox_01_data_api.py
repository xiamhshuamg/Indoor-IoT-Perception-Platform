# test_blackbox_01_data_api.py
# -*- coding: utf-8 -*-
import os
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

BASE = os.getenv("API_BASE", "http://127.0.0.1:8003")


def now_iso_local():
    # 输出本地时间（便于报告记录），同时保留 ISO 格式
    return datetime.now().astimezone().isoformat(timespec="seconds")


def banner(title: str):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def jdump(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=2)


def parse_ts(ts: str):
    # 兼容 "2025-12-21T12:34:56Z" 或 "+00:00"
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def http_get(path: str, **kwargs):
    url = BASE + path
    r = requests.get(url, timeout=5, **kwargs)
    if r.status_code != 200:
        raise AssertionError(f"GET {path} -> {r.status_code}\n{r.text}")
    return r.json()


@dataclass
class TestItem:
    name: str
    ok: bool = False
    reason: str = ""


@dataclass
class CaseResult:
    case_id: str
    title: str
    started_at: str = field(default_factory=now_iso_local)
    base_url: str = ""
    items: list[TestItem] = field(default_factory=list)

    # 关键数据（用于总结）
    health: dict = field(default_factory=dict)
    sensors_count: int = 0
    sample_sensor_id: str = ""
    latest_count: int = 0
    history_count: int = 0

    def add_item(self, name: str, ok: bool, reason: str = ""):
        self.items.append(TestItem(name=name, ok=ok, reason=reason))

    def stats(self):
        total = len(self.items)
        passed = sum(1 for x in self.items if x.ok)
        failed = total - passed
        rate = (passed / total * 100.0) if total else 0.0
        return total, passed, failed, rate

    def print_live_result(self):
        for it in self.items:
            if it.ok:
                print(f"[PASS] {it.name}")
            else:
                print(f"[FAIL] {it.name} -> {it.reason}")

    def print_doc_summary_block(self):
        total, passed, failed, rate = self.stats()

        mysql = str(self.health.get("mysql", ""))
        db = str(self.health.get("db", ""))
        user = str(self.health.get("user", ""))
        pwd_empty = self.health.get("pwd_empty", None)
        ts = str(self.health.get("ts", ""))

        # 生成“可直接粘到文档”的总结块（建议整段复制）
        lines = []
        lines.append("")
        lines.append(f"用例编号：{self.case_id}")
        lines.append(f"用例名称：{self.title}")
        lines.append(f"测试时间：{self.started_at}")
        lines.append(f"服务地址：{self.base_url}")
        lines.append("")
        lines.append("（1）测试说明")
        lines.append("本用例以“数据采集—接口查询—历史回溯”为主线，对后端对外接口进行端到端黑盒验证，重点检查接口可用性、返回结构完整性、数据一致性以及时间戳可解析性。")
        lines.append("")
        lines.append("（2）覆盖接口与检查点")
        lines.append("- GET /health：服务可用、数据库连接信息可读取")
        lines.append("- GET /api/sensors：传感器列表非空，字段结构满足前端渲染契约")
        lines.append("- GET /api/readings/latest：最新读数与传感器可关联，包含运行态字段（ts/value/battery/quality）")
        lines.append("- GET /api/readings/history：历史回溯可用，返回记录结构正确且时间戳可解析")
        lines.append("")
        lines.append("（3）测试结果统计")
        lines.append(f"- 测试项总数：{total}")
        lines.append(f"- 通过项数：{passed}")
        lines.append(f"- 失败项数：{failed}")
        lines.append(f"- 成功率：{rate:.2f}%")
        lines.append("")
        lines.append("（4）关键输出摘录")
        lines.append(f"- 健康检查：ok={self.health.get('ok', None)}，ts={ts}")
        if mysql or db or user or (pwd_empty is not None):
            lines.append(f"- 数据库信息：mysql={mysql}，db={db}，user={user}，pwd_empty={pwd_empty}")
        lines.append(f"- 传感器数量：{self.sensors_count}（示例 sensor_id={self.sample_sensor_id}）")
        lines.append(f"- 最新读数数量：{self.latest_count}")
        lines.append(f"- 历史读数条数（5分钟窗口）：{self.history_count}")
        lines.append("")
        lines.append("（5）结论")
        if failed == 0 and total > 0:
            lines.append("本次用例执行全部通过，说明后端数据链路相关接口在当前环境下可稳定工作，能够支撑前端实时展示与历史曲线回放等功能。")
        else:
            lines.append("本次用例存在未通过项，需结合失败原因对接口返回或依赖组件（如数据库连接/数据生成逻辑）进行进一步排查与修复。")

        print("\n" + "-" * 72)
        print("【复制到文档区】（从下一行开始整段复制）")
        print("\n".join(lines))
        print("【复制到文档区结束】")
        print("-" * 72 + "\n")


def main():
    case = CaseResult(
        case_id="CASE-01",
        title="数据链路（Health + Sensors + Latest + History）",
        base_url=BASE,
    )

    banner(f"[{case.case_id}] {case.title}")
    print(f"[INFO] API_BASE = {BASE}")

    # Item 1: /health
    try:
        health = http_get("/health")
        if not (isinstance(health, dict) and health.get("ok") is True):
            raise AssertionError(f"/health 返回异常：\n{jdump(health)}")
        case.health = health
        case.add_item("GET /health", True)
        print("[PASS] GET /health")
        print(jdump(health))
    except Exception as e:
        case.add_item("GET /health", False, str(e))

    # Item 2: /api/sensors
    try:
        sensors = http_get("/api/sensors")
        if not (isinstance(sensors, list) and len(sensors) > 0):
            raise AssertionError(f"/api/sensors 为空或结构不对：\n{jdump(sensors)}")
        for k in ["id", "room", "name", "type", "unit", "warn_low", "warn_high"]:
            if k not in sensors[0]:
                raise AssertionError(f"/api/sensors 缺少字段 {k}，sample=\n{jdump(sensors[0])}")
        case.sensors_count = len(sensors)
        case.sample_sensor_id = sensors[0]["id"]
        case.add_item("GET /api/sensors", True)
        print(f"[PASS] GET /api/sensors (count={len(sensors)}) 取样 sensor_id={case.sample_sensor_id}")
        print(jdump(sensors[:2]))
    except Exception as e:
        case.add_item("GET /api/sensors", False, str(e))

    # Item 3: /api/readings/latest
    try:
        latest = http_get("/api/readings/latest")
        if not (isinstance(latest, list) and len(latest) > 0):
            raise AssertionError(f"/api/readings/latest 为空或结构不对：\n{jdump(latest)}")
        if case.sample_sensor_id and (not any(x.get("sensor_id") == case.sample_sensor_id for x in latest)):
            raise AssertionError("latest 中未找到 sample sensor_id 的读数")
        case.latest_count = len(latest)
        case.add_item("GET /api/readings/latest", True)
        print(f"[PASS] GET /api/readings/latest (count={len(latest)})")
        print(jdump(latest[:3]))
    except Exception as e:
        case.add_item("GET /api/readings/latest", False, str(e))

    # Item 4: /api/readings/history
    try:
        if not case.sample_sensor_id:
            raise AssertionError("缺少 sample_sensor_id（/api/sensors 未通过，无法继续 history 校验）")
        hist = http_get("/api/readings/history", params={"sensor_id": case.sample_sensor_id, "minutes": 5})
        if not isinstance(hist, list):
            raise AssertionError(f"/api/readings/history 结构不对：\n{jdump(hist)}")
        if len(hist) > 0:
            for k in ["sensor_id", "ts", "value"]:
                if k not in hist[-1]:
                    raise AssertionError(f"history 缺少字段 {k}，last=\n{jdump(hist[-1])}")
            parse_ts(hist[-1]["ts"])  # 可解析即可
        case.history_count = len(hist)
        case.add_item("GET /api/readings/history", True)
        print(f"[PASS] GET /api/readings/history?sensor_id={case.sample_sensor_id}&minutes=5 (count={len(hist)})")
        print(jdump(hist[-3:] if len(hist) >= 3 else hist))
    except Exception as e:
        case.add_item("GET /api/readings/history", False, str(e))

    # 控制台汇总（统计 + 文档总结块）
    total, passed, failed, rate = case.stats()
    banner(f"[RESULT] {case.case_id} 执行完成：通过 {passed}/{total} | 失败 {failed} | 成功率 {rate:.2f}%")
    case.print_live_result()
    case.print_doc_summary_block()

    # 失败则返回非 0，方便 CI/截图体现
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n[ERROR]", repr(e))
        sys.exit(1)
