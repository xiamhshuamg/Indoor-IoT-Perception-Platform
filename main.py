# main.py (MySQL 版，整文件覆盖)
# -*- coding: utf-8 -*-

"""
室内感知平台后端（MySQL 版）
- mock 数据来自 data.py 的 MockDataEngine（默认启用）
- real 数据来自 real_driver.py 的 RealDriver（检测到就自动切换）
- 后端落库到 MySQL：readings / events / kv 三张表

准备工作：
1) pip 安装：py -m pip install pymysql
2) main.py 同目录新增 .env（非常重要）例如：
   MYSQL_HOST=127.0.0.1
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=你的密码
   MYSQL_DB=iot_platform
   SERIAL_PORT=COM6
   SERIAL_BAUD=115200

启动：
py -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import pymysql
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data import MockDataEngine, Sensor


# =========================
# 1) 读取 .env（轻量，不依赖 python-dotenv）
# =========================
def _load_local_env_file(path: str) -> None:
    """
    轻量 .env 读取：
    - 支持 KEY=VALUE
    - 不覆盖已有环境变量
    - 允许 value 带引号
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and (k not in os.environ):
                    os.environ[k] = v
    except Exception:
        # 读不到就算了，不要影响启动
        pass


BASE_DIR = os.path.dirname(__file__)
_load_local_env_file(os.path.join(BASE_DIR, ".env"))


# =========================
# 2) 小工具
# =========================
def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_to_unix(ts: str) -> float:
    if not ts:
        return time.time()
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def quality_by(sensor: Sensor, value: float) -> str:
    span = max(1.0, float(sensor.warn_high - sensor.warn_low))
    if value < sensor.warn_low - 0.15 * span or value > sensor.warn_high + 0.15 * span:
        return "alarm"
    if value < sensor.warn_low or value > sensor.warn_high:
        return "warn"
    return "ok"


def comfort_score(temp_c: Optional[float], hum: Optional[float]) -> Dict[str, Any]:
    """简易舒适度（课设够用）"""
    if temp_c is None or hum is None:
        return {"score": None, "label": "unknown"}

    t = float(temp_c)
    h = float(hum)

    score = 100.0
    score -= abs(t - 23.0) * 6.0
    score -= abs(h - 50.0) * 1.2
    score = clamp(score, 0.0, 100.0)

    if score >= 80:
        label = "舒适"
    elif score >= 60:
        label = "一般"
    elif score >= 40:
        label = "不舒适"
    else:
        label = "很不舒适"
    return {"score": int(round(score)), "label": label, "temp": round(t, 1), "humidity": round(h, 1)}


# =========================
# 3) MySQL Storage（用 to_thread 避免阻塞 FastAPI）
# =========================
class MySQLStorage:
    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self.kw = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )

    def _connect(self):
        return pymysql.connect(**self.kw)

    async def _run(self, fn):
        #fn 必须是普通 def，不能是 async def
        return await asyncio.to_thread(fn)

    async def init_schema(self) -> None:

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS readings
                        (
                            id
                            BIGINT
                            PRIMARY
                            KEY
                            AUTO_INCREMENT,
                            ts_iso
                            VARCHAR
                        (
                            40
                        ) NOT NULL,
                            ts_unix DOUBLE NOT NULL,
                            mode VARCHAR
                        (
                            16
                        ) NOT NULL,
                            sensor_id VARCHAR
                        (
                            32
                        ) NOT NULL,
                            room VARCHAR
                        (
                            32
                        ),
                            type VARCHAR
                        (
                            32
                        ),
                            value DOUBLE,
                            battery INT,
                            quality VARCHAR
                        (
                            16
                        ),
                            KEY idx_readings_sensor_time
                        (
                            sensor_id,
                            ts_unix
                        ),
                            KEY idx_readings_mode_time
                        (
                            mode,
                            ts_unix
                        )
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS events
                        (
                            id
                            BIGINT
                            PRIMARY
                            KEY,
                            ts_iso
                            VARCHAR
                        (
                            40
                        ) NOT NULL,
                            ts_unix DOUBLE NOT NULL,
                            mode VARCHAR
                        (
                            16
                        ) NOT NULL,
                            level VARCHAR
                        (
                            16
                        ) NOT NULL,
                            category VARCHAR
                        (
                            32
                        ) NOT NULL,
                            message VARCHAR
                        (
                            255
                        ) NOT NULL,
                            sensor_id VARCHAR
                        (
                            32
                        ),
                            value DOUBLE,
                            meta_json LONGTEXT,
                            acked TINYINT NOT NULL DEFAULT 0,
                            KEY idx_events_time
                        (
                            ts_unix
                        ),
                            KEY idx_events_acked
                        (
                            acked
                        )
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS kv
                        (
                            `key`
                            VARCHAR
                        (
                            64
                        ) PRIMARY KEY,
                            value_json LONGTEXT NOT NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                        """
                    )

        await self._run(_do)

    async def kv_get(self, key: str, default: Any = None) -> Any:
        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT value_json FROM kv WHERE `key`=%s", (key,))
                    row = cur.fetchone()
                    return row["value_json"] if row else None

        raw = await self._run(_do)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    async def kv_set(self, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False)

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO kv(`key`,value_json) VALUES(%s,%s) "
                        "ON DUPLICATE KEY UPDATE value_json=VALUES(value_json)",
                        (key, payload),
                    )

        await self._run(_do)

    async def insert_reading(self, mode: str, sensor: Dict[str, Any], reading: Dict[str, Any]) -> None:
        ts_iso = str(reading.get("ts") or iso_now())
        ts_unix = parse_iso_to_unix(ts_iso)

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO readings(ts_iso, ts_unix, mode, sensor_id, room, type, value, battery, quality)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            ts_iso,
                            ts_unix,
                            mode,
                            str(reading.get("sensor_id")),
                            str(sensor.get("room") or ""),
                            str(sensor.get("type") or ""),
                            float(reading.get("value")) if reading.get("value") is not None else None,
                            int(reading.get("battery") or 0),
                            str(reading.get("quality") or ""),
                        ),
                    )

        await self._run(_do)

    async def insert_event(self, mode: str, ev: Dict[str, Any]) -> None:
        ts_iso = str(ev.get("ts") or iso_now())
        ts_unix = parse_iso_to_unix(ts_iso)
        meta_json = json.dumps(ev.get("meta") or {}, ensure_ascii=False)

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO events(id, ts_iso, ts_unix, mode, level, category, message, sensor_id, value,
                                           meta_json, acked)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY
                        UPDATE
                            ts_iso=
                        VALUES (ts_iso), ts_unix=
                        VALUES (ts_unix), mode=
                        VALUES (mode), level =
                        VALUES (level), category=
                        VALUES (category), message=
                        VALUES (message), sensor_id=
                        VALUES (sensor_id), value =
                        VALUES (value), meta_json=
                        VALUES (meta_json), acked=
                        VALUES (acked)
                        """,
                        (
                            int(ev["id"]),
                            ts_iso,
                            ts_unix,
                            mode,
                            str(ev.get("level") or "info"),
                            str(ev.get("category") or "system"),
                            str(ev.get("message") or ""),
                            ev.get("sensor_id"),
                            float(ev["value"]) if ev.get("value") is not None else None,
                            meta_json,
                            1 if ev.get("acked") else 0,
                        ),
                    )

        await self._run(_do)

    async def list_events(self, limit: int = 200, acked: Optional[bool] = None, mode: Optional[str] = None) -> List[
        Dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        where = []
        args: List[Any] = []

        if acked is not None:
            where.append("acked=%s")
            args.append(1 if acked else 0)
        if mode:
            where.append("mode=%s")
            args.append(mode)

        sql = "SELECT * FROM events"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ts_unix DESC LIMIT %s"
        args.append(limit)

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(args))
                    rows = cur.fetchall()
                    out = []
                    for r in rows:
                        out.append(
                            {
                                "id": int(r["id"]),
                                "ts": r["ts_iso"],
                                "level": r["level"],
                                "category": r["category"],
                                "message": r["message"],
                                "sensor_id": r["sensor_id"],
                                "value": r["value"],
                                "meta": json.loads(r["meta_json"] or "{}"),
                                "acked": bool(r["acked"]),
                            }
                        )
                    return out

        return await self._run(_do)

    async def ack_event(self, event_id: int) -> bool:
        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE events SET acked=1 WHERE id=%s", (int(event_id),))
                    return cur.rowcount > 0

        return await self._run(_do)

    async def ack_all(self, levels: Optional[List[str]] = None) -> List[int]:
        levels_set = set(levels or [])

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if levels_set:
                        placeholders = ",".join(["%s"] * len(levels_set))
                        cur.execute(
                            f"SELECT id FROM events WHERE acked=0 AND level IN ({placeholders})",
                            tuple(levels_set),
                        )
                        ids = [int(x["id"]) for x in cur.fetchall()]
                        cur.execute(
                            f"UPDATE events SET acked=1 WHERE acked=0 AND level IN ({placeholders})",
                            tuple(levels_set),
                        )
                    else:
                        cur.execute("SELECT id FROM events WHERE acked=0")
                        ids = [int(x["id"]) for x in cur.fetchall()]
                        cur.execute("UPDATE events SET acked=1 WHERE acked=0")
                    return ids

        return await self._run(_do)

    async def stats(self, sensor_id: str, minutes: int, mode: Optional[str] = None) -> Dict[str, Any]:
        minutes = max(1, int(minutes))
        cutoff = time.time() - minutes * 60

        where = ["sensor_id=%s", "ts_unix>=%s", "value IS NOT NULL"]
        args: List[Any] = [sensor_id, cutoff]
        if mode:
            where.append("mode=%s")
            args.append(mode)

        sql = f"""
        SELECT
          COUNT(*) as cnt,
          MIN(value) as vmin,
          MAX(value) as vmax,
          AVG(value) as vavg,
          SUM(value) as vsum,
          SUM(value*value) as vsum2,
          SUM(CASE WHEN quality='warn' THEN 1 ELSE 0 END) as warn_cnt,
          SUM(CASE WHEN quality='alarm' THEN 1 ELSE 0 END) as alarm_cnt,
          MAX(ts_unix) as last_ts
        FROM readings
        WHERE {" AND ".join(where)}
        """

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(args))
                    r = cur.fetchone() or {}
                    cnt = int(r.get("cnt") or 0)
                    if cnt <= 0:
                        return {"sensor_id": sensor_id, "minutes": minutes, "count": 0}

                    vsum = float(r.get("vsum") or 0.0)
                    vsum2 = float(r.get("vsum2") or 0.0)
                    ex = vsum / cnt
                    ex2 = vsum2 / cnt
                    var = max(0.0, ex2 - ex * ex)
                    std = var ** 0.5

                    return {
                        "sensor_id": sensor_id,
                        "minutes": minutes,
                        "count": cnt,
                        "min": float(r["vmin"]) if r.get("vmin") is not None else None,
                        "max": float(r["vmax"]) if r.get("vmax") is not None else None,
                        "avg": float(r["vavg"]) if r.get("vavg") is not None else None,
                        "std": std,
                        "warn_count": int(r.get("warn_cnt") or 0),
                        "alarm_count": int(r.get("alarm_cnt") or 0),
                        "last_ts_unix": float(r["last_ts"]) if r.get("last_ts") is not None else None,
                    }

        return await self._run(_do)

    async def cleanup(self, keep_days: int = 7) -> None:
        cutoff = time.time() - int(keep_days) * 86400

        def _do():
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM readings WHERE ts_unix < %s", (cutoff,))
                    cur.execute("DELETE FROM events WHERE ts_unix < %s", (cutoff,))

        await self._run(_do)


# =========================
# 4) 平台配置（保存在 kv 表里）
# =========================
@dataclass
class PlatformConfig:
    auto_mode: bool = True
    offline_seconds: float = 8.0
    retention_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "auto_mode": self.auto_mode,
            "offline_seconds": self.offline_seconds,
            "retention_days": self.retention_days,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "PlatformConfig":
        cfg = PlatformConfig()
        if isinstance(d, dict):
            cfg.auto_mode = bool(d.get("auto_mode", True))
            try:
                cfg.offline_seconds = float(d.get("offline_seconds", 8.0))
            except Exception:
                pass
            try:
                cfg.retention_days = int(d.get("retention_days", 7))
            except Exception:
                pass
        cfg.offline_seconds = clamp(cfg.offline_seconds, 2.0, 120.0)
        cfg.retention_days = max(1, min(cfg.retention_days, 90))
        return cfg


# =========================
# 5) 读取环境变量
# =========================
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "iot_platform")

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM6")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "115200"))

# =========================
# 6) 引擎 + 驱动
# =========================
engine = MockDataEngine(interval=2.0)

storage = MySQLStorage(MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
platform_cfg = PlatformConfig()

MODE_LOCK = asyncio.Lock()
DATA_MODE: str = "mock"  # 默认 mock

WS_CLIENTS: Set[WebSocket] = set()
WS_LOCK = asyncio.Lock()
LAST_SEEN_UNIX: Dict[str, float] = {}
ONLINE_STATE: Dict[str, bool] = {}

# =========================
# 7) FastAPI
# =========================
app = FastAPI(title="Indoor Sensing Platform (Backend)", version="mysql-fixed-1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def broadcast_json(msg: Dict[str, Any]) -> None:
    dead: List[WebSocket] = []
    async with WS_LOCK:
        clients = list(WS_CLIENTS)
    for ws in clients:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    if dead:
        async with WS_LOCK:
            for ws in dead:
                WS_CLIENTS.discard(ws)


async def mark_seen(sensor_id: str) -> None:
    LAST_SEEN_UNIX[sensor_id] = time.time()
    if sensor_id not in ONLINE_STATE:
        ONLINE_STATE[sensor_id] = True


async def snapshot() -> Dict[str, Any]:
    """汇总当前状态（仅 mock；real_driver 已移除）"""
    snap = await engine.snapshot()
    snap["platform"] = platform_cfg.to_dict()
    return snap


async def engine_broadcaster_loop() -> None:
    """把 mock 引擎产出的 reading/event 广播给前端 + 落库"""
    last_rule_check = 0
    print(" engine_broadcaster_loop 已启动")

    while True:
        msg = await engine.queue.get() # 从模拟引擎的队列中取出一条消息
        async with MODE_LOCK:
            mode = DATA_MODE
        if mode != "mock":
            continue

        try:
            if msg.get("type") == "reading":
                r = msg.get("data") or {}
                sid = r.get("sensor_id")
                if sid:
                    # 调试输出 - 显示关键传感器数据
                    if sid in ["T-101", "H-101", "C-101", "T-102", "H-102", "C-102"]:
                        print(f" 发送传感器数据: {sid} = {r.get('value')} {r.get('quality', 'ok')}")

                    sensors = await engine.get_sensors()
                    sensor_map = {x["id"]: x for x in sensors}
                    s = sensor_map.get(sid, {"id": sid})
                    # 写入readings表
                    await storage.insert_reading("mock", s, r)
                    await mark_seen(sid)

                    # 广播到前端
                    await broadcast_json(msg)

                    # 定期检查规则
                    current_time = time.time()
                    if current_time - last_rule_check >= 5:
                        last_rule_check = current_time
                        latest_data = await engine.get_latest()
                        await rule_engine.check_rules(latest_data)

            elif msg.get("type") == "event":
                ev = msg.get("data") or {}
                if "id" in ev:
                    await storage.insert_event("mock", ev)
                    # 广播事件
                    await broadcast_json(msg)
                    # 调试输出
                    if ev.get("level") in ["warn", "alarm"]:
                        print(f" 发送事件: {ev.get('level')} - {ev.get('message')}")

        except Exception as e:
            print(f" engine_broadcaster_loop error: {e}")


async def cleanup_loop() -> None:
    """定期清理历史数据（可选）"""
    while True:
        try:
            await storage.cleanup(keep_days=int(platform_cfg.retention_days))
        except Exception:
            pass
        await asyncio.sleep(600)


@app.on_event("shutdown")
async def on_shutdown():
    await engine.stop()


# =========================
# 8) API（保持前端原接口不变）
# =========================
@app.get("/health")
async def health():
    return {
        "ok": True,
        "ts": iso_now(),
        "mysql": f"{MYSQL_HOST}:{MYSQL_PORT}",
        "db": MYSQL_DB,
        "user": MYSQL_USER,
        "pwd_empty": (MYSQL_PASSWORD == ""),
    }


@app.get("/api/sensors")
async def api_sensors():
    # 仅使用 mock 数据源（real_driver 已移除）
    return await engine.get_sensors()


@app.get("/api/readings/latest")
async def api_latest():
    # 仅使用 mock 数据源（real_driver 已移除）
    return await engine.get_latest()


@app.get("/api/readings/history")
async def api_history(sensor_id: str = Query(...), minutes: int = Query(60, ge=1, le=24 * 60)):
    # 仅使用 mock 数据源（real_driver 已移除）
    return await engine.get_history(sensor_id=sensor_id, minutes=minutes)


@app.get("/api/actuators")
async def api_get_actuators():
    return await engine.get_actuators()


@app.post("/api/actuators")
async def api_set_actuators(patch: Dict[str, Any]):
    return await engine.set_actuators(patch)


@app.get("/api/config")
async def api_get_config():
    return await engine.get_config()


@app.post("/api/config")
async def api_set_config(patch: Dict[str, Any]):
    return await engine.set_config(patch)


@app.get("/api/events")
async def api_events(limit: int = Query(200, ge=1, le=1000), acked: Optional[bool] = Query(None)):
    async with MODE_LOCK:
        mode = DATA_MODE
    return await storage.list_events(limit=limit, acked=acked, mode=mode)


@app.post("/api/events/{event_id}/ack")
async def api_ack_event(event_id: int):
    ok = await storage.ack_event(event_id)
    # 修正：简单返回 id 和 ok 状态即可，避免复杂的查询逻辑
    return {"ok": ok, "id": event_id}

@app.post("/api/events/ack_all")
async def api_ack_all(levels: Optional[str] = Query("warn,alarm")):
    levels_list = [x.strip() for x in (levels or "").split(",") if x.strip()]
    ids = await storage.ack_all(levels=levels_list or None)
    return {"ok": True, "acked": len(ids), "ids": ids}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    async with WS_LOCK:
        WS_CLIENTS.add(ws)
    try:
        await ws.send_json({"type": "snapshot", "data": await snapshot()})
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with WS_LOCK:
            WS_CLIENTS.discard(ws)


# =========================
# 9) 新增能力接口（你可直接用浏览器调）
# =========================
@app.get("/api/mode")
async def api_mode():
    async with MODE_LOCK:
        mode = DATA_MODE
    return {
        "mode": mode,
        "available_modes": ["mock", "dataset"],
        "ts": iso_now(),
        "mysql": f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}",
        # 为了不让前端报空字段，这里保留 serial 结构，但不再使用
        "serial": {"port": SERIAL_PORT, "baud": SERIAL_BAUD},
        "real_latest": {"ok": False, "error": "real_driver 已移除，仅支持 mock"},
        "platform": platform_cfg.to_dict(),
    }

@app.get("/api/real/latest")
async def api_real_latest():
    # 兼容旧前端接口：real_driver 已删除
    return {"ok": False, "error": "real_driver 已移除，仅支持 mock"}


@app.get("/api/stats")
async def api_stats(
    sensor_id: Optional[str] = Query(None),
    minutes: int = Query(60, ge=1, le=24 * 60),
    data_mode: Optional[str] = Query(
        None,
        description="mock 或 dataset；默认使用当前运行模式（一般为 mock）",
    ),
):
    async with MODE_LOCK:
        mode = DATA_MODE
    # 如果显式传了 data_mode，就覆盖当前模式
    if data_mode in ("mock", "dataset"):
        mode = data_mode

    sensors = await api_sensors()
    sids = [sensor_id] if sensor_id else [s["id"] for s in sensors]

    out = []
    for sid in sids:
        st = await storage.stats(sid, minutes=minutes, mode=mode)
        s = next((x for x in sensors if x["id"] == sid), None)
        if s:
            st.update(
                {
                    "room": s.get("room"),
                    "name": s.get("name"),
                    "type": s.get("type"),
                    "unit": s.get("unit"),
                }
            )
        out.append(st)

    return out[0] if sensor_id else out



@app.get("/api/comfort")
async def api_comfort():
    latest = await api_latest()
    mp = {x["sensor_id"]: x for x in latest if x and x.get("sensor_id")}
    t = mp.get("T-101", {}).get("value")
    h = mp.get("H-101", {}).get("value")
    t2 = mp.get("T-102", {}).get("value")
    h2 = mp.get("H-102", {}).get("value")
    return {
        "ts": iso_now(),
        "living_room": comfort_score(t, h),
        "bedroom": comfort_score(t2, h2)
    }


@app.get("/api/report")
async def api_report(
    hours: int = Query(24, ge=1, le=168),
    data_mode: Optional[str] = Query(
        None,
        description="mock 或 dataset；默认使用当前运行模式（一般为 mock）",
    ),
):
    async with MODE_LOCK:
        mode = DATA_MODE
    # data_mode 显式指定时，强制使用对应 mode（mock / dataset）
    if data_mode in ("mock", "dataset"):
        mode = data_mode

    sensors = await api_sensors()
    minutes = int(hours * 60)

    stats_list = []
    for s in sensors:
        st = await storage.stats(s["id"], minutes=minutes, mode=mode)
        st.update(
            {
                "room": s.get("room"),
                "name": s.get("name"),
                "type": s.get("type"),
                "unit": s.get("unit"),
            }
        )
        stats_list.append(st)

    events = await storage.list_events(limit=1000, acked=None, mode=mode)
    warn_cnt = sum(1 for e in events if e.get("level") == "warn")
    alarm_cnt = sum(1 for e in events if e.get("level") == "alarm")

    # 简单建议：这里仍然基于实时 mock 数据（强调"实时为仿真"）
    suggestions = []
    mp = {x["sensor_id"]: x for x in (await api_latest())}

    # 检查客厅
    if "C-101" in mp and float(mp["C-101"]["value"]) > 1000:
        suggestions.append("客厅 CO₂ 偏高：建议开启新风/通风。")
    if "P-101" in mp and float(mp["P-101"]["value"]) > 55:
        suggestions.append("客厅 PM2.5 偏高：建议开启净化器。")
    if "L-101" in mp and float(mp["L-101"]["value"]) < 120:
        suggestions.append("客厅光照偏低：建议开灯或调整窗帘。")

    # 检查卧室
    if "C-102" in mp and float(mp["C-102"]["value"]) > 1000:
        suggestions.append("卧室 CO₂ 偏高：建议开启卧室新风/通风。")
    if "P-102" in mp and float(mp["P-102"]["value"]) > 55:
        suggestions.append("卧室 PM2.5 偏高：建议开启卧室净化器。")
    if "L-102" in mp and float(mp["L-102"]["value"]) < 120:
        suggestions.append("卧室光照偏低：建议开灯或调整窗帘。")

    # 检查噪声
    if "N-101" in mp and float(mp["N-101"]["value"]) > 65:
        suggestions.append("客厅噪声偏高：建议降低音量。")
    if "N-102" in mp and float(mp["N-102"]["value"]) > 65:
        suggestions.append("卧室噪声偏高：建议保持安静环境。")

    # 报告中补充"数据来源说明"
    if mode == "dataset":
        data_source = {
            "mode": "dataset",
            "realtime": "实时页面（WebSocket / 仪表盘）仍使用 MockDataEngine 生成的仿真数据。",
            "history": "本报告中的统计/历史分析部分使用导入到 MySQL 的公开数据集（readings.mode = 'dataset'）。",
            # 这里给一个示例数据集，方便在报告里写引用，你可以根据实际使用的数据集改掉
            "dataset_example": {
                "name": "UCI Occupancy Detection Data Set",
                "url": "https://archive.ics.uci.edu/ml/datasets/Occupancy+Detection+Data+Set",
            },
        }
    else:
        data_source = {
            "mode": "mock",
            "realtime": "当前平台仅启用了 MockDataEngine 仿真数据（未接真实硬件）。",
            "history": "如需历史分析，可先导入公开数据集到 MySQL（readings.mode = 'dataset'），"
                       "然后调用 /api/report?data_mode=dataset 查看基于数据集的统计结果。",
            "dataset_example": None,
        }

    return {
        "ts": iso_now(),
        "mode": mode,
        "hours": hours,
        "comfort": await api_comfort(),
        "stats": stats_list,
        "event_summary": {"warn": warn_cnt, "alarm": alarm_cnt, "total": len(events)},
        "suggestions": suggestions,
        "platform": platform_cfg.to_dict(),
        "data_source": data_source,
    }



@app.get("/api/special_event")
async def api_special_event():
    """获取当前特殊事件信息（仅 mock；real_driver 已移除）"""
    return await engine.get_special_event_info()


@app.get("/api/time_effects")
async def api_time_effects():
    """获取时间效应信息"""
    now = datetime.now()
    hour = now.hour
    month = now.month

    # 季节判断
    if 3 <= month <= 5:
        season = "spring"
    elif 6 <= month <= 8:
        season = "summer"
    elif 9 <= month <= 11:
        season = "autumn"
    else:
        season = "winter"

    # 时间效应
    time_effect = "白天"
    if 6 <= hour <= 9:
        time_effect = "早晨"
    elif 10 <= hour <= 12:
        time_effect = "上午"
    elif 13 <= hour <= 17:
        time_effect = "下午"
    elif 18 <= hour <= 21:
        time_effect = "晚上"
    elif 22 <= hour or hour <= 5:
        time_effect = "深夜"

    return {
        "current_time": now.isoformat(),
        "hour": hour,
        "season": season,
        "time_effect": time_effect,
        "description": f"{season}季的{time_effect}时段"
    }

@dataclass
class AutomationRule:
    """自动化规则"""
    id: str
    name: str
    condition: Dict[str, Any]          # 条件表达式
    actions: List[Dict[str, Any]]      # 执行动作
    enabled: bool = True
    last_triggered: Optional[str] = None
    trigger_count: int = 0
    cooldown_seconds: int = 300        # 冷却时间（秒）


    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "condition": self.condition,
            "actions": self.actions,
            "last_triggered": self.last_triggered,
            "trigger_count": self.trigger_count,
            "cooldown_seconds": self.cooldown_seconds
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AutomationRule":
        return AutomationRule(
            id=d.get("id", ""),
            name=d.get("name", "未命名规则"),
            enabled=bool(d.get("enabled", True)),
            condition=d.get("condition", {}),
            actions=d.get("actions", []),
            last_triggered=d.get("last_triggered"),
            trigger_count=int(d.get("trigger_count", 0)),
            cooldown_seconds=int(d.get("cooldown_seconds", 300))
        )


class RuleEngine:
    """规则引擎"""


    def __init__(self, storage: MySQLStorage, engine: MockDataEngine):
        self.storage = storage
        self.engine = engine
        self.rules: Dict[str, AutomationRule] = {}
        self.running = False
        self._condition_start_times = {}
        # 默认规则
        self.default_rules = [
            AutomationRule(
                id="rule_temp_high",
                name="温度过高自动通风",
                enabled=True,
                condition={
                    "type": "sensor_threshold",
                    "sensor_id": "T-101",  # 客厅温度
                    "operator": ">",
                    "value": 28.0,
                    "duration": 60  # 持续60秒
                },
                actions=[
                    {
                        "type": "set_actuator",
                        "actuator": "ventilation",
                        "value": True
                    },
                    {
                        "type": "send_notification",
                        "message": "客厅温度过高，已自动开启通风"
                    }
                ]
            ),
            AutomationRule(
                id="rule_pm25_high",
                name="PM2.5过高自动净化",
                enabled=True,
                condition={
                    "type": "sensor_threshold",
                    "sensor_id": "P-101",  # 客厅PM2.5
                    "operator": ">",
                    "value": 75.0,
                    "duration": 30
                },
                actions=[
                    {
                        "type": "set_actuator",
                        "actuator": "purifier",
                        "value": True
                    },
                    {
                        "type": "send_notification",
                        "message": "PM2.5过高，已自动开启净化器"
                    }
                ]
            ),
            AutomationRule(
                id="rule_co2_high",
                name="CO₂过高自动通风",
                enabled=True,
                condition={
                    "type": "sensor_threshold",
                    "sensor_id": "C-101",  # 客厅CO₂
                    "operator": ">",
                    "value": 1200.0,
                    "duration": 45
                },
                actions=[
                    {
                        "type": "set_actuator",
                        "actuator": "ventilation",
                        "value": True
                    },
                    {
                        "type": "send_notification",
                        "message": "CO₂浓度过高，已自动开启通风"
                    }
                ]
            ),
            AutomationRule(
                id="rule_night_lights_off",
                name="夜间自动关灯",
                enabled=True,
                condition={
                    "type": "time_based",
                    "time_range": "22:00-06:00",  # 晚上10点到早上6点
                    "days_of_week": [1, 2, 3, 4, 5, 6, 7]  # 每天
                },
                actions=[
                    {
                        "type": "set_actuator",
                        "actuator": "lights",
                        "value": False
                    },
                    {
                        "type": "send_notification",
                        "message": "夜间时段，已自动关闭灯光"
                    }
                ]
            ),
            AutomationRule(
                id="rule_morning_temp_adjust",
                name="早晨温度调节",
                enabled=True,
                condition={
                    "type": "time_based",
                    "time_range": "06:00-08:00",  # 早上6点到8点
                    "days_of_week": [1, 2, 3, 4, 5]  # 周一到周五
                },
                actions=[
                    {
                        "type": "set_actuator",
                        "actuator": "target_temp",
                        "value": 22.0
                    }
                ]
            )
        ]

    async def init(self) -> None:
        """初始化规则引擎"""
        # 从存储加载规则
        saved_rules = await self.storage.kv_get("automation_rules", default=[])

        if saved_rules:
            # 加载保存的规则
            for rule_data in saved_rules:
                rule = AutomationRule.from_dict(rule_data)
                self.rules[rule.id] = rule
        else:
            # 使用默认规则
            for rule in self.default_rules:
                self.rules[rule.id] = rule
            await self.save_rules()

    async def save_rules(self) -> None:
        """保存规则到存储"""
        rules_data = [rule.to_dict() for rule in self.rules.values()]
        await self.storage.kv_set("automation_rules", rules_data)

    async def evaluate_condition(self, rule: AutomationRule, sensor_data: Dict[str, Any]) -> bool:
        """评估条件是否满足"""
        condition = rule.condition

        if condition["type"] == "sensor_threshold":
            sensor_id = condition["sensor_id"]
            operator = condition["operator"]
            threshold = condition["value"]
            duration = condition.get("duration", 0)

            # 获取传感器当前值
            current_value = None
            for data in sensor_data:
                if data["sensor_id"] == sensor_id:
                    current_value = data["value"]
                    break

            if current_value is None:
                return False

            # 检查条件
            condition_met = False
            if operator == ">":
                condition_met = current_value > threshold
            elif operator == ">=":
                condition_met = current_value >= threshold
            elif operator == "<":
                condition_met = current_value < threshold
            elif operator == "<=":
                condition_met = current_value <= threshold
            elif operator == "==":
                condition_met = abs(current_value - threshold) < 0.01

            # 检查持续时间
            if not condition_met:
                # 如果条件不满足，清除记录的时间
                if rule.id in self._condition_start_times:
                    del self._condition_start_times[rule.id]
                return False

                # 如果条件满足
            if duration > 0:
                now_ts = time.time()
                if rule.id not in self._condition_start_times:
                    # 第一次满足，记录开始时间
                    self._condition_start_times[rule.id] = now_ts
                    return False  # 尚未达到持续时间
                else:
                    # 已经满足过，检查是否超时
                    start_ts = self._condition_start_times[rule.id]
                    if (now_ts - start_ts) >= duration:
                        # 达到持续时间，允许触发
                        # (可选：触发后是否重置？通常为了避免重复触发，
                        # 冷却时间 cooldown_seconds 已经处理了频率问题，这里可以不重置)
                        return True
                    else:
                        return False  # 时间未到
            else:
                return True

        elif condition["type"] == "time_based":
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.isoweekday()  # 1=Monday, 7=Sunday

            time_range = condition["time_range"]
            days_of_week = condition.get("days_of_week", [1, 2, 3, 4, 5, 6, 7])

            # 检查星期几
            if current_day not in days_of_week:
                return False

            # 检查时间范围
            start_str, end_str = time_range.split("-")
            start_time = datetime.strptime(start_str, "%H:%M").time()
            end_time = datetime.strptime(end_str, "%H:%M").time()
            current_time_obj = datetime.strptime(current_time, "%H:%M").time()

            if start_time <= end_time:
                # 同一天内的时间范围
                return start_time <= current_time_obj <= end_time
            else:
                # 跨天的时间范围（如22:00-06:00）
                return current_time_obj >= start_time or current_time_obj <= end_time

        elif condition["type"] == "compound":
            # 复合条件（AND/OR）
            operator = condition.get("operator", "AND")
            sub_conditions = condition.get("conditions", [])

            results = []
            for sub_cond in sub_conditions:
                # 递归评估子条件
                temp_rule = AutomationRule(id="temp", name="temp", condition=sub_cond, actions=[])
                results.append(await self.evaluate_condition(temp_rule, sensor_data))

            if operator == "AND":
                return all(results)
            elif operator == "OR":
                return any(results)

        return False

    async def execute_actions(self, rule: AutomationRule) -> None:
        """执行规则动作"""
        now_iso = iso_now()

        for action in rule.actions:
            action_type = action["type"]

            if action_type == "set_actuator":
                actuator = action["actuator"]
                value = action["value"]

                # 更新执行器状态
                patch = {actuator: value}
                await self.engine.set_actuators(patch)

                # 记录事件
                await self.storage.insert_event("automation", {
                    "id": int(time.time() * 1000),
                    "ts": now_iso,
                    "level": "info",
                    "category": "automation",
                    "message": f"规则 '{rule.name}' 触发：设置 {actuator} 为 {value}",
                    "meta": {"rule_id": rule.id, "action": action},
                    "acked": False
                })

            elif action_type == "send_notification":
                message = action["message"]

                # 创建通知事件
                await self.storage.insert_event("automation", {
                    "id": int(time.time() * 1000),
                    "ts": now_iso,
                    "level": "info",
                    "category": "notification",
                    "message": message,
                    "meta": {"rule_id": rule.id},
                    "acked": False
                })

            elif action_type == "log_event":
                message = action["message"]
                level = action.get("level", "info")

                await self.storage.insert_event("automation", {
                    "id": int(time.time() * 1000),
                    "ts": now_iso,
                    "level": level,
                    "category": "automation",
                    "message": message,
                    "meta": {"rule_id": rule.id},
                    "acked": False
                })

    async def check_rules(self, sensor_data: List[Dict[str, Any]]) -> None:
        """检查所有规则"""
        now = datetime.now(timezone.utc)
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # 检查冷却时间
            if rule.last_triggered:
                last_triggered = datetime.fromisoformat(rule.last_triggered.replace("Z", "+00:00"))
                seconds_since = (now - last_triggered).total_seconds()
                if seconds_since < rule.cooldown_seconds:
                    continue
            # 评估条件
            condition_met = await self.evaluate_condition(rule, sensor_data)
            if condition_met:
                # 执行动作
                await self.execute_actions(rule)
                # 更新规则状态
                rule.last_triggered = now.isoformat()
                rule.trigger_count += 1
                # 保存规则状态
                await self.save_rules()

    async def add_rule(self, rule_data: Dict[str, Any]) -> AutomationRule:
        """添加新规则"""
        rule_id = rule_data.get("id") or f"rule_{int(time.time())}"
        rule = AutomationRule.from_dict({**rule_data, "id": rule_id})

        self.rules[rule.id] = rule
        await self.save_rules()

        return rule

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[AutomationRule]:
        """更新规则"""
        if rule_id not in self.rules:
            return None

        rule = self.rules[rule_id]

        # 更新字段
        if "name" in updates:
            rule.name = updates["name"]
        if "enabled" in updates:
            rule.enabled = bool(updates["enabled"])
        if "condition" in updates:
            rule.condition = updates["condition"]
        if "actions" in updates:
            rule.actions = updates["actions"]
        if "cooldown_seconds" in updates:
            rule.cooldown_seconds = int(updates["cooldown_seconds"])

        await self.save_rules()
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            await self.save_rules()
            return True
        return False

    async def get_rules(self) -> List[Dict[str, Any]]:
        """获取所有规则"""
        return [rule.to_dict() for rule in self.rules.values()]

    async def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """获取单个规则"""
        if rule_id in self.rules:
            return self.rules[rule_id].to_dict()
        return None


# =========================
# 在全局变量中添加规则引擎
# =========================

# 在engine和storage定义之后添加
rule_engine = RuleEngine(storage, engine)


# =========================
# 修改engine_broadcaster_loop函数，添加规则检查
# =========================
async def engine_broadcaster_loop() -> None:
    """把 mock 引擎产出的 reading/event 广播给前端 + 落库"""
    last_rule_check = 0

    while True:
        msg = await engine.queue.get()
        async with MODE_LOCK:
            mode = DATA_MODE
        if mode != "mock":
            continue

        await broadcast_json(msg)

        try:
            if msg.get("type") == "reading":
                r = msg.get("data") or {}
                sid = r.get("sensor_id")
                if sid:
                    sensors = await engine.get_sensors()
                    sensor_map = {x["id"]: x for x in sensors}
                    s = sensor_map.get(sid, {"id": sid})
                    await storage.insert_reading("mock", s, r)
                    await mark_seen(sid)

                    # 定期检查规则（每5秒检查一次）
                    current_time = time.time()
                    if current_time - last_rule_check >= 5:
                        last_rule_check = current_time
                        latest_data = await engine.get_latest()
                        await rule_engine.check_rules(latest_data)

            elif msg.get("type") == "event":
                ev = msg.get("data") or {}
                if "id" in ev:
                    await storage.insert_event("mock", ev)
        except Exception as e:
            print(f"engine_broadcaster_loop error: {e}")
            pass


# =========================
# 修改on_startup函数，初始化规则引擎
# =========================
@app.on_event("startup")
async def on_startup():
    # 1) 先确保 MySQL 表存在
    await storage.init_schema()

    # 2) 读取平台配置
    global platform_cfg
    cfg = await storage.kv_get("platform", default=None)
    if cfg:
        platform_cfg = PlatformConfig.from_dict(cfg)
    else:
        await storage.kv_set("platform", platform_cfg.to_dict())

    # 2.5) 初始化规则引擎
    await rule_engine.init()

    # 3) 启动 mock 引擎 + real 串口驱动
    await engine.start()

    # 4) 后台任务
    asyncio.create_task(engine_broadcaster_loop())
    asyncio.create_task(cleanup_loop())


# =========================
# 自动化规则API
# =========================

@app.get("/api/automation/rules")
async def api_get_rules():
    """获取所有自动化规则"""
    return await rule_engine.get_rules()


@app.get("/api/automation/rules/{rule_id}")
async def api_get_rule(rule_id: str):
    """获取单个规则"""
    rule = await rule_engine.get_rule(rule_id)
    if rule:
        return rule
    return {"error": "Rule not found"}, 404


@app.post("/api/automation/rules")
async def api_create_rule(rule_data: Dict[str, Any]):
    """创建新规则"""
    try:
        rule = await rule_engine.add_rule(rule_data)
        return {"ok": True, "rule": rule.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.put("/api/automation/rules/{rule_id}")
async def api_update_rule(rule_id: str, updates: Dict[str, Any]):
    """更新规则"""
    rule = await rule_engine.update_rule(rule_id, updates)
    if rule:
        return {"ok": True, "rule": rule.to_dict()}
    return {"ok": False, "error": "Rule not found"}


@app.delete("/api/automation/rules/{rule_id}")
async def api_delete_rule(rule_id: str):
    """删除规则"""
    success = await rule_engine.delete_rule(rule_id)
    return {"ok": success}


@app.post("/api/automation/rules/{rule_id}/test")
async def api_test_rule(rule_id: str):
    """测试规则"""
    rule_data = await rule_engine.get_rule(rule_id)
    if not rule_data:
        return {"ok": False, "error": "Rule not found"}

    rule = AutomationRule.from_dict(rule_data)

    # 获取当前传感器数据
    async with MODE_LOCK:
        mode = DATA_MODE

    if mode == "mock":
        sensor_data = await engine.get_latest()
    else:
        # real模式下的处理
        sensor_data = await api_latest()

    # 评估条件
    condition_met = await rule_engine.evaluate_condition(rule, sensor_data)

    return {
        "ok": True,
        "condition_met": condition_met,
        "sensor_data": sensor_data,
        "rule": rule_data
    }


@app.post("/api/automation/rules/{rule_id}/trigger")
async def api_trigger_rule(rule_id: str):
    """手动触发规则"""
    rule_data = await rule_engine.get_rule(rule_id)
    if not rule_data:
        return {"ok": False, "error": "Rule not found"}

    rule = AutomationRule.from_dict(rule_data)

    # 执行动作
    await rule_engine.execute_actions(rule)

    # 更新触发次数
    rule.trigger_count += 1
    rule.last_triggered = iso_now()
    await rule_engine.update_rule(rule_id, rule.to_dict())

    return {"ok": True, "message": "Rule triggered manually"}


@app.get("/api/automation/status")
async def api_automation_status():
    """获取自动化状态"""
    rules = await rule_engine.get_rules()
    enabled_count = sum(1 for r in rules if r["enabled"])
    triggered_count = sum(r["trigger_count"] for r in rules)

    return {
        "total_rules": len(rules),
        "enabled_rules": enabled_count,
        "total_triggers": triggered_count,
        "last_checked": iso_now()
    }