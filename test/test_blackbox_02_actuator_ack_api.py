# test_blackbox_02_actuator_ack_api.py
# -*- coding: utf-8 -*-
import os
import sys
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import requests

BASE = os.getenv("API_BASE", "http://127.0.0.1:8003")


def now_iso_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def banner(title: str):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def jdump(x) -> str:
    return json.dumps(x, ensure_ascii=False, indent=2)


def http_get(path: str, **kwargs) -> Any:
    url = BASE + path
    r = requests.get(url, timeout=5, **kwargs)
    if r.status_code != 200:
        raise AssertionError(f"GET {path} -> {r.status_code}\n{r.text}")
    return r.json()


def http_post(path: str, json_body=None, **kwargs) -> Any:
    url = BASE + path
    r = requests.post(url, json=json_body, timeout=5, **kwargs)
    if r.status_code != 200:
        raise AssertionError(f"POST {path} -> {r.status_code}\n{r.text}")
    return r.json()


def iso_to_unix(ts: str) -> float:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()


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
    items: List[TestItem] = field(default_factory=list)

    # 关键数据用于总结
    health: Dict[str, Any] = field(default_factory=dict)
    actuators_before: Dict[str, Any] = field(default_factory=dict)
    actuators_after: Dict[str, Any] = field(default_factory=dict)
    lights_before: Optional[bool] = None
    lights_after: Optional[bool] = None
    event_found: Optional[Dict[str, Any]] = None
    ack_ret: Optional[Dict[str, Any]] = None
    ack_verified: bool = False

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

        event_id = None
        event_msg = ""
        event_cat = ""
        event_ts = ""
        if self.event_found:
            event_id = self.event_found.get("id")
            event_msg = str(self.event_found.get("message", ""))
            event_cat = str(self.event_found.get("category", ""))
            event_ts = str(self.event_found.get("ts", ""))

        ack_ok = None
        if self.ack_ret is not None:
            ack_ok = self.ack_ret.get("ok", None)

        lines = []
        lines.append("【黑盒测试用例总结】")
        lines.append(f"用例编号：{self.case_id}")
        lines.append(f"用例名称：{self.title}")
        lines.append(f"测试时间：{self.started_at}")
        lines.append(f"服务地址：{self.base_url}")
        lines.append("")
        lines.append("（1）测试说明")
        lines.append("本用例面向后端对外接口进行闭环验证：通过执行器控制接口触发状态更新，并检查事件列表是否产生对应事件，随后对事件进行 ACK 确认，最终验证事件确认状态可被查询到，从而证明“控制—事件—确认”的业务链路可用。")
        lines.append("")
        lines.append("（2）覆盖接口与检查点")
        lines.append("- GET /health：服务可用、数据库连接信息可读取")
        lines.append("- GET /api/actuators：获取执行器当前状态")
        lines.append("- POST /api/actuators：更新执行器状态并返回最新结果")
        lines.append("- GET /api/events?acked=false：出现“执行器状态更新”类未确认事件")
        lines.append("- POST /api/events/{id}/ack：事件确认成功")
        lines.append("- GET /api/events?acked=true：已确认列表中可检索到该事件")
        lines.append("")
        lines.append("（3）测试结果统计")
        lines.append(f"- 测试项总数：{total}")
        lines.append(f"- 通过项数：{passed}")
        lines.append(f"- 失败项数：{failed}")
        lines.append(f"- 成功率：{rate:.2f}%")
        lines.append("")
        lines.append("（4）关键输出摘录（用于结果佐证）")
        lines.append(f"- 健康检查：ok={self.health.get('ok', None)}，ts={ts}")
        if mysql or db or user or (pwd_empty is not None):
            lines.append(f"- 数据库信息：mysql={mysql}，db={db}，user={user}，pwd_empty={pwd_empty}")
        lines.append(f"- 执行器 lights 状态：before={self.lights_before} -> after={self.lights_after}")
        lines.append(f"- 触发事件：id={event_id}，category={event_cat}，ts={event_ts}")
        if event_msg:
            lines.append(f"- 事件 message：{event_msg}")
        lines.append(f"- ACK 返回：ok={ack_ok}")
        lines.append(f"- ACK 验证：acked_list_contains_event={self.ack_verified}")
        lines.append("")
        lines.append("（5）结论")
        if failed == 0 and total > 0:
            lines.append("本次用例执行全部通过，说明后端执行器控制能够正确触发事件产生，且事件确认（ACK）状态可被稳定查询，业务闭环满足演示与验收要求。")
        else:
            lines.append("本次用例存在未通过项，需结合失败原因排查事件落库/查询条件、ACK 更新逻辑或数据库连接状态。")

        print("\n" + "-" * 72)
        print("【复制到文档区】（从下一行开始整段复制）")
        print("\n".join(lines))
        print("【复制到文档区结束】")
        print("-" * 72 + "\n")


def main():
    case = CaseResult(
        case_id="CASE-02",
        title="执行器控制与ACK闭环（Actuators -> Event -> ACK）",
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

    # Item 2: GET /api/actuators
    try:
        before = http_get("/api/actuators")
        if not isinstance(before, dict):
            raise AssertionError(f"/api/actuators 结构不对：\n{jdump(before)}")
        case.actuators_before = before
        case.lights_before = bool(before.get("lights", False))
        case.add_item("GET /api/actuators (before)", True)
        print("[PASS] GET /api/actuators (before)")
        print(jdump(before))
    except Exception as e:
        case.add_item("GET /api/actuators (before)", False, str(e))

    # Item 3: POST /api/actuators (flip lights)
    try:
        if case.lights_before is None:
            raise AssertionError("缺少 lights_before（上一步失败）")
        new_lights = not case.lights_before
        after = http_post("/api/actuators", json_body={"lights": new_lights})
        if after.get("lights") != new_lights:
            raise AssertionError(f"POST /api/actuators 后 lights 未更新：\n{jdump(after)}")
        case.actuators_after = after
        case.lights_after = bool(after.get("lights", False))
        case.add_item("POST /api/actuators (flip lights)", True)
        print(f"[PASS] POST /api/actuators -> lights={new_lights}")
        print(jdump(after))
    except Exception as e:
        case.add_item("POST /api/actuators (flip lights)", False, str(e))

    # Item 4: find actuator event in /api/events?acked=false
    try:
        cutoff = time.time() - 120
        found = None
        for i in range(12):
            events = http_get("/api/events", params={"limit": 50, "acked": False})
            if not isinstance(events, list):
                raise AssertionError(f"/api/events 返回结构不对：\n{jdump(events)}")

            for ev in events:
                if ev.get("category") != "actuator":
                    continue
                if "执行器状态更新" not in str(ev.get("message", "")):
                    continue
                meta = ev.get("meta") or {}
                changes = meta.get("changes") or {}
                if "lights" not in changes:
                    continue
                ts = ev.get("ts")
                if ts and iso_to_unix(ts) >= cutoff:
                    found = ev
                    break

            if found:
                break

            print(f"[INFO] 等待事件落库... ({i+1}/12)")
            time.sleep(0.3)

        if not found:
            raise AssertionError("未找到最近的执行器更新事件（检查：MySQL 是否正常、事件是否落库）")

        case.event_found = found
        case.add_item("GET /api/events?acked=false (find actuator event)", True)
        print("[PASS] GET /api/events?acked=false 找到执行器事件（未确认）")
        print(jdump(found))
    except Exception as e:
        case.add_item("GET /api/events?acked=false (find actuator event)", False, str(e))

    # Item 5: POST /api/events/{id}/ack
    try:
        if not case.event_found:
            raise AssertionError("缺少 event_found（上一步失败）")
        event_id = int(case.event_found["id"])
        ack_ret = http_post(f"/api/events/{event_id}/ack")
        if ack_ret.get("ok") is not True:
            raise AssertionError(f"ACK 返回异常：\n{jdump(ack_ret)}")
        case.ack_ret = ack_ret
        case.add_item(f"POST /api/events/{event_id}/ack", True)
        print(f"[PASS] POST /api/events/{event_id}/ack")
        print(jdump(ack_ret))
    except Exception as e:
        case.add_item("POST /api/events/{id}/ack", False, str(e))

    # Item 6: verify /api/events?acked=true contains event
    try:
        if not case.event_found:
            raise AssertionError("缺少 event_found（上一步失败）")
        event_id = int(case.event_found["id"])

        ok_in_acked = False
        for i in range(12):
            acked_events = http_get("/api/events", params={"limit": 50, "acked": True})
            if isinstance(acked_events, list) and any(int(e.get("id", -1)) == event_id for e in acked_events):
                ok_in_acked = True
                break
            print(f"[INFO] 等待ACK状态刷新... ({i+1}/12)")
            time.sleep(0.2)

        if not ok_in_acked:
            raise AssertionError("已确认列表中未出现该事件（ACK闭环未成立）")

        case.ack_verified = True
        case.add_item("GET /api/events?acked=true (verify)", True)
        print("[PASS] GET /api/events?acked=true 中已出现该事件（闭环成立）")
    except Exception as e:
        case.add_item("GET /api/events?acked=true (verify)", False, str(e))

    # 汇总输出
    total, passed, failed, rate = case.stats()
    banner(f"[RESULT] {case.case_id} 执行完成：通过 {passed}/{total} | 失败 {failed} | 成功率 {rate:.2f}%")
    case.print_live_result()
    case.print_doc_summary_block()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n[ERROR]", repr(e))
        sys.exit(1)
