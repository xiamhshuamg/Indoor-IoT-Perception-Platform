
from __future__ import annotations

import asyncio
import random
import math
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Deque, Dict, List, Optional
from enum import Enum


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class EventType(Enum):
    """特殊事件类型"""
    NORMAL = "normal"
    WINDOW_OPEN = "window_open"  # 开窗
    COOKING = "cooking"  # 做饭
    PARTY = "party"  # 聚会
    CLEANING = "cleaning"  # 打扫
    SLEEPING = "sleeping"  # 睡眠


@dataclass
class TimeEffect:
    """时间效应配置"""
    hour: int
    temperature_effect: float = 0.0
    humidity_effect: float = 0.0
    light_effect: float = 0.0
    co2_effect: float = 0.0
    noise_effect: float = 0.0


@dataclass
class SeasonEffect:
    """季节性效应配置"""
    season: str  # spring, summer, autumn, winter
    temperature_base: float = 0.0
    humidity_base: float = 0.0


@dataclass
class Sensor:
    id: str
    room: str
    name: str
    type: str
    unit: str
    warn_low: float
    warn_high: float
    gen_low: float
    gen_high: float
    step: float

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "room": self.room,
            "name": self.name,
            "type": self.type,
            "unit": self.unit,
            "warn_low": self.warn_low,
            "warn_high": self.warn_high,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        d = self.to_public_dict()
        d.update({"gen_low": self.gen_low, "gen_high": self.gen_high, "step": self.step})
        return d


@dataclass
class Reading:
    sensor_id: str
    ts: str
    value: float
    battery: int
    quality: str  # ok | warn | alarm

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Actuators:
    lights: bool = False
    ventilation: bool = False
    purifier: bool = False
    target_temp: float = 24.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    id: int
    ts: str
    level: str  # info | warn | alarm
    category: str  # sensor | battery | actuator | config | special_event
    message: str
    sensor_id: Optional[str] = None
    value: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    acked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MockDataEngine:
    def __init__(self, interval: float = 2.0, history_hours: int = 2, events_maxlen: int = 1000):
        self.interval = float(interval)
        self.actuators = Actuators()

        # 特殊事件相关
        self.current_event: Optional[EventType] = None
        self.event_end_time: Optional[datetime] = None
        self.event_probability = 0.01  # 1%的概率触发特殊事件

        # 时间效应配置（昼夜模式）
        self.time_effects = [
            TimeEffect(0, temperature_effect=-1.5, light_effect=-300, noise_effect=-10),  # 午夜
            TimeEffect(6, temperature_effect=-0.5, light_effect=100, noise_effect=5),  # 早晨
            TimeEffect(12, temperature_effect=2.0, light_effect=500, noise_effect=15),  # 中午
            TimeEffect(18, temperature_effect=0.5, light_effect=200, noise_effect=10),  # 傍晚
            TimeEffect(22, temperature_effect=-1.0, light_effect=-100, noise_effect=-5),  # 晚上
        ]

        # 季节性效应配置
        self.season_effects = {
            "spring": SeasonEffect("spring", temperature_base=0.0, humidity_base=10.0),
            "summer": SeasonEffect("summer", temperature_base=5.0, humidity_base=20.0),
            "autumn": SeasonEffect("autumn", temperature_base=0.0, humidity_base=5.0),
            "winter": SeasonEffect("winter", temperature_base=-5.0, humidity_base=-10.0),
        }

        # 获取当前季节
        self.current_season = self._get_current_season()

        # 完整的传感器列表：客厅6个，卧室6个
        self.sensors: List[Sensor] = [
            # 客厅传感器
            Sensor("T-101", "客厅", "温度", "temperature", "°C", 18, 28, 16, 30, 0.35),
            Sensor("H-101", "客厅", "湿度", "humidity", "%", 30, 70, 20, 80, 1.2),
            Sensor("C-101", "客厅", "CO₂", "co2", "ppm", 400, 1200, 350, 2000, 45),
            Sensor("P-101", "客厅", "PM2.5", "pm25", "µg/m³", 0, 75, 0, 180, 6),
            Sensor("N-101", "客厅", "噪声", "noise", "dB", 30, 65, 20, 95, 2.5),
            Sensor("L-101", "客厅", "光照", "light", "lx", 80, 800, 10, 1200, 60),

            # 卧室传感器
            Sensor("T-102", "卧室", "温度", "temperature", "°C", 18, 28, 16, 30, 0.35),
            Sensor("H-102", "卧室", "湿度", "humidity", "%", 30, 70, 20, 80, 1.2),
            Sensor("C-102", "卧室", "CO₂", "co2", "ppm", 400, 1200, 350, 2000, 45),
            Sensor("P-102", "卧室", "PM2.5", "pm25", "µg/m³", 0, 75, 0, 180, 6),
            Sensor("N-102", "卧室", "噪声", "noise", "dB", 30, 65, 20, 95, 2.5),
            Sensor("L-102", "卧室", "光照", "light", "lx", 80, 800, 10, 1200, 60),
        ]
        self._sensor_by_id: Dict[str, Sensor] = {s.id: s for s in self.sensors}

        self.queue: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()

        self._values: Dict[str, float] = {}
        self._battery: Dict[str, int] = {}

        maxlen = int((history_hours * 3600) / max(self.interval, 0.1))
        self._history: Dict[str, Deque[Reading]] = {s.id: deque(maxlen=maxlen) for s in self.sensors}

        self._events: Deque[Event] = deque(maxlen=events_maxlen)
        self._event_id = 1

        self._last_quality: Dict[str, str] = {s.id: "ok" for s in self.sensors}
        self._last_event_time: Dict[str, datetime] = {}
        self._last_batt_event_time: Dict[str, datetime] = {}

        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

        self._init_state()

    def _get_current_season(self) -> str:
        """根据月份获取当前季节"""
        month = datetime.now().month
        if 3 <= month <= 5:
            return "spring"
        elif 6 <= month <= 8:
            return "summer"
        elif 9 <= month <= 11:
            return "autumn"
        else:
            return "winter"

    def _get_time_effect(self, current_hour: int) -> TimeEffect:
        """获取当前时间的效应"""
        # 找到最近的时间点
        sorted_effects = sorted(self.time_effects, key=lambda x: abs(x.hour - current_hour))
        return sorted_effects[0]

    def _calculate_time_effect(self, sensor: Sensor, base_value: float) -> float:
        """
        计算时间 / 季节效应

        关键点：
        - 不再直接加减一个很大的数，而是让数值慢慢向“目标舒适值”靠拢
        - 目标值会受到：季节 + 昼夜 时间效应影响
        - 这样温度就不会被一脚踢到 16，光照不会一直锁在 1200
        """
        now = datetime.now()
        hour = now.hour
        time_effect = self._get_time_effect(hour)
        season_effect = self.season_effects.get(
            self.current_season,
            SeasonEffect("normal"),
        )

        v = float(base_value)

        # 温度：向一个“季节 + 昼夜”决定的舒适温度缓慢靠拢
        if sensor.type == "temperature":
            # 基础舒适温度 24℃，冬天会整体低一点，夏天高一点
            base_target = 24.0 + season_effect.temperature_base
            # 再叠加一点昼夜影响（中午略高，凌晨略低）
            base_target += time_effect.temperature_effect
            # 每一步只往目标走 10%，不会一下子改变太多
            v += (base_target - v) * 0.10

        # 湿度：向 50% 左右缓慢靠拢，季节/时间略有偏移
        elif sensor.type == "humidity":
            base_target = 50.0 + season_effect.humidity_base
            base_target += time_effect.humidity_effect
            # 10% 的“回弹”力度
            v += (base_target - v) * 0.10

        # 光照：白天高一点，夜里自动往低值收敛
        elif sensor.type == "light":
            # 中午附近 target 大，凌晨 target 小
            base_target = 200.0 + time_effect.light_effect
            # 夜间再稍微降低一点
            if hour >= 20 or hour <= 5:
                base_target -= 150.0
            # 不要太极端，限制一下范围
            base_target = clamp(base_target, 10.0, 1000.0)
            # 光照变化
            v += (base_target - v) * 0.15

        # 噪声：白天略高，夜间略低，在 25~60 之间缓慢波动
        elif sensor.type == "noise":
            base_target = 35.0 + time_effect.noise_effect
            # 工作时间稍微吵一点
            if 9 <= hour <= 17:
                base_target += 5.0
            # 深夜更安静
            if 22 <= hour or hour <= 6:
                base_target -= 5.0
            base_target = clamp(base_target, 25.0, 60.0)
            v += (base_target - v) * 0.10

        # CO₂ / PM2.5 不在这里加时间效应，纯靠随机 + 执行器 / 特殊事件
        return v

    def _check_special_event(self) -> bool:
        """检查是否触发特殊事件"""
        now = datetime.now(timezone.utc)

        # 如果当前有事件，检查是否结束
        if self.current_event and self.event_end_time:
            if now >= self.event_end_time:
                self._end_special_event()
                return False

        # 随机触发新事件
        if random.random() < self.event_probability and not self.current_event:
            event_type = random.choice(list(EventType))
            if event_type != EventType.NORMAL:
                self._start_special_event(event_type)
                return True

        return False

    def _start_special_event(self, event_type: EventType):
        """开始特殊事件"""
        self.current_event = event_type
        duration = random.randint(300, 1800)  # 5-30分钟
        self.event_end_time = datetime.now(timezone.utc) + timedelta(seconds=duration)

        # 生成事件消息
        messages = {
            EventType.WINDOW_OPEN: "检测到窗户打开，通风增强",
            EventType.COOKING: "检测到烹饪活动，PM2.5和CO₂可能升高",
            EventType.PARTY: "检测到聚会活动，噪声和CO₂升高",
            EventType.CLEANING: "正在进行清洁活动",
            EventType.SLEEPING: "进入睡眠模式，环境要求更安静"
        }

        if event_type in messages:
            self._push_event(
                level="info",
                category="special_event",
                message=messages[event_type],
                meta={"event_type": event_type.value, "duration": duration}
            )

    def _end_special_event(self):
        """结束特殊事件"""
        if self.current_event:
            self._push_event(
                level="info",
                category="special_event",
                message=f"特殊事件 '{self.current_event.value}' 已结束",
                meta={"event_type": self.current_event.value}
            )
            self.current_event = None
            self.event_end_time = None

    def _apply_special_event_effect(self, sensor: Sensor, base_value: float) -> float:
        """应用特殊事件效应"""
        if not self.current_event:
            return base_value

        effect = 0.0

        if self.current_event == EventType.WINDOW_OPEN:
            if sensor.type == "co2":
                effect = -random.uniform(100, 300)
            elif sensor.type == "pm25":
                effect = -random.uniform(10, 30)
            elif sensor.type == "temperature":
                effect = random.uniform(-2, 2)  # 受室外温度影响
            elif sensor.type == "humidity":
                effect = random.uniform(-5, 5)  # 影响湿度

        elif self.current_event == EventType.COOKING:
            if sensor.type == "pm25":
                effect = random.uniform(30, 100)
            elif sensor.type == "co2":
                effect = random.uniform(200, 500)
            elif sensor.type == "temperature":
                effect = random.uniform(1, 3)
            elif sensor.type == "humidity":
                effect = random.uniform(5, 15)

        elif self.current_event == EventType.PARTY:
            if sensor.type == "noise":
                effect = random.uniform(10, 30)
            elif sensor.type == "co2":
                effect = random.uniform(100, 300)

        elif self.current_event == EventType.CLEANING:
            if sensor.type == "pm25":
                effect = -random.uniform(5, 20)

        elif self.current_event == EventType.SLEEPING:
            if sensor.type == "noise":
                effect = -random.uniform(5, 15)
            elif sensor.type == "temperature":
                effect = random.uniform(-1, 1)

        return base_value + effect

    def _quality(self, s: Sensor, v: float) -> str:
        span = max(1.0, s.warn_high - s.warn_low)
        if v < s.warn_low - 0.15 * span or v > s.warn_high + 0.15 * span:
            return "alarm"
        if v < s.warn_low or v > s.warn_high:
            return "warn"
        return "ok"

    def _round_value(self, s: Sensor, v: float) -> float:
        if s.type == "temperature":
            return float(f"{v:.1f}")
        if s.type in ("humidity", "co2", "pm25", "light", "noise"):
            return float(int(round(v)))
        return float(f"{v:.2f}")

    def _make_reading(self, s: Sensor, v: float, ts: Optional[str] = None) -> Reading:
        v2 = self._round_value(s, v)
        q = self._quality(s, v2)
        b = int(self._battery[s.id])
        return Reading(sensor_id=s.id, ts=ts or iso_now(), value=v2, battery=b, quality=q)

    def _push_event(
            self,
            level: str,
            category: str,
            message: str,
            sensor_id: Optional[str] = None,
            value: Optional[float] = None,
            meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        ev = Event(
            id=self._event_id,
            ts=iso_now(),
            level=level,
            category=category,
            message=message,
            sensor_id=sensor_id,
            value=value,
            meta=meta or {},
            acked=False,
        )
        self._event_id += 1
        self._events.append(ev)
        asyncio.create_task(self.queue.put({"type": "event", "data": ev.to_dict()}))

    def _should_emit_sensor_event(self, sid: str, new_q: str) -> bool:
        prev = self._last_quality.get(sid, "ok")
        now = datetime.now(timezone.utc)
        last_t = self._last_event_time.get(sid)

        if new_q != prev:
            self._last_event_time[sid] = now
            return True

        if last_t is None or (now - last_t).total_seconds() >= 30:
            self._last_event_time[sid] = now
            return True

        return False

    def _battery_event_check(self, sid: str, battery: int) -> None:
        if battery > 15:
            return
        now = datetime.now(timezone.utc)
        last_t = self._last_batt_event_time.get(sid)
        if last_t is None or (now - last_t).total_seconds() >= 300:
            self._last_batt_event_time[sid] = now
            s = self._sensor_by_id[sid]
            self._push_event(
                level="warn",
                category="battery",
                message=f"{s.room}·{s.name} 电量低：{battery}%",
                sensor_id=sid,
                value=float(battery),
                meta={"battery": battery},
            )

    def _get_gen_range(self, s: Sensor) -> tuple[float, float]:
        """
        保证每个传感器都有一个“正常宽度”的生成范围。

        有时候配置里会把 gen_low 和 gen_high 写成同一个值
        （比如都等于 16 或 20），这样 clamp 之后就完全不动了。
        这里做一个兜底：如果范围太窄，就按一个合理区间来生成。
        """
        lo = float(s.gen_low)
        hi = float(s.gen_high)

        # 范围小于 0.1，认为是“钉死”
        if hi - lo < 0.1:
            if s.type == "temperature":
                lo, hi = 16.0, 30.0       # 你希望的温度范围
            elif s.type == "humidity":
                lo, hi = 20.0, 80.0       # 你希望的湿度范围
            elif s.type == "light":
                lo, hi = 10.0, 1200.0     # 光照
            elif s.type == "noise":
                lo, hi = 20.0, 95.0       # 噪声
            elif s.type == "co2":
                lo, hi = 350.0, 2000.0
            elif s.type == "pm25":
                lo, hi = 0.0, 180.0

        return lo, hi

    # 修改 _init_state 方法，增加初始值的随机范围
    def _init_state(self) -> None:
        for s in self.sensors:
            # 使用安全范围，避免 gen_low == gen_high 时直接钉死
            lo, hi = self._get_gen_range(s)
            self._values[s.id] = random.uniform(lo, hi)
            self._battery[s.id] = random.randint(70, 98)

        now = datetime.now(timezone.utc)
        points = 60
        for s in self.sensors:
            # 为每个传感器生成不同的基础值
            base = random.uniform(s.gen_low, s.gen_high)
            for i in range(points):
                ts = (now - timedelta(seconds=(points - i) * self.interval)).isoformat()
                # 增加波动幅度
                v = clamp(base + (random.random() - 0.5) * s.step * 5, s.gen_low, s.gen_high)
                r = self._make_reading(s, v, ts=ts)
                self._history[s.id].append(r)
                self._last_quality[s.id] = r.quality

    def _apply_actuators(self, s: Sensor, v: float) -> float:
        """应用执行器效应 - 修复极端变化问题"""
        if s.type == "temperature":
            # 目标温度效应，使用更温和的调整
            if self.actuators.target_temp > v:
                v += (self.actuators.target_temp - v) * 0.2
            else:
                v -= (v - self.actuators.target_temp) * 0.05

        elif s.type == "co2":
            # CO₂效应 - 修复极端变化
            if self.actuators.ventilation:
                v -= random.uniform(100, 200)
            else:
                v += random.uniform(2, 8)

        elif s.type == "pm25":
            # PM2.5效应
            if self.actuators.purifier:
                v -= random.uniform(5, 10)
            else:
                v += random.uniform(0.5, 2)

        elif s.type == "light":
            # 光照效应 - 修复灯光效果
            if self.actuators.lights:
                v += random.uniform(200, 300)
            else:
                v = max(10, v - random.uniform(5, 15))  

        elif s.type == "noise":
            # 噪声效应 - 增加随机波动
            v += (random.random() - 0.5) * s.step

        # 确保值在合理范围内
        return clamp(v, s.gen_low, s.gen_high)

    async def _loop(self) -> None:
        while not self._stop.is_set():
            current_interval = float(self.interval)
            # 检查特殊事件
            self._check_special_event()

            for s in self.sensors:
                # 基础随机波动 - 增加变化幅度
                base_change = (random.random() - 0.5) * s.step * 2.5
                v = self._values[s.id] + base_change
                # 应用执行器效应
                v = self._apply_actuators(s, v)
                # 应用时间效应
                v = self._calculate_time_effect(s, v)
                # 应用特殊事件效应
                v = self._apply_special_event_effect(s, v)
                # 确保在范围内
                lo, hi = self._get_gen_range(s)
                v = clamp(v, lo, hi)

                # 电量消耗 - 降低消耗速度
                if random.random() < 0.05:  # 从0.10降低到0.05
                    self._battery[s.id] = max(10, self._battery[s.id] - 1)
                self._values[s.id] = v

                r = self._make_reading(s, v)
                self._history[s.id].append(r)

                # 发送到队列
                await self.queue.put({"type": "reading", "data": r.to_dict()})

                # 电池事件检查
                self._battery_event_check(s.id, r.battery)

                # 传感器警告触发
                if r.quality != "ok" and self._should_emit_sensor_event(s.id, r.quality):
                    level = "alarm" if r.quality == "alarm" else "warn"
                    self._push_event(
                        level=level,
                        category="sensor",
                        message=f"{s.room}·{s.name} 超出阈值：{r.value}{s.unit}",
                        sensor_id=s.id,
                        value=float(r.value),
                        meta={
                            "warn_low": s.warn_low,
                            "warn_high": s.warn_high,
                            "unit": s.unit,
                            "quality": r.quality,
                        },
                    )

                self._last_quality[s.id] = r.quality

            await asyncio.sleep(max(0.2, current_interval))  # 确保最小间隔

    async def start(self) -> None:
                # """
                # 开始后台生成数据（给 main.py 调用）
                # """
                # # 已经在跑就不重复启动
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
                # """
                # 停止后台生成数据
                # """
        if self._task is not None:
            self._stop.set()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:  # 建议加上 finally 确保引用置空
                self._task = None

    # ===== readings =====

    async def get_sensors(self) -> List[Dict[str, Any]]:
        return [s.to_public_dict() for s in self.sensors]

    async def get_latest(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for s in self.sensors:
            h = self._history[s.id]
            out.append((h[-1] if h else self._make_reading(s, self._values[s.id])).to_dict())
        return out

    async def get_history(self, sensor_id: str, minutes: int) -> List[Dict[str, Any]]:
        minutes = max(1, int(minutes))
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        out: List[Dict[str, Any]] = []
        for r in self._history.get(sensor_id, deque()):
            try:
                ts = datetime.fromisoformat(r.ts)
            except Exception:
                continue
            if ts >= cutoff:
                out.append(r.to_dict())
        return out

    async def snapshot(self) -> Dict[str, Any]:
        return {
            "sensors": await self.get_sensors(),
            "latest": await self.get_latest(),
            "actuators": await self.get_actuators(),
            "config": await self.get_config(),
            "events": [e.to_dict() for e in list(self._events)[-50:]],
            "special_event": self.current_event.value if self.current_event else None,
            "season": self.current_season,
        }

    # ===== actuators =====

    async def get_actuators(self) -> Dict[str, Any]:
        return self.actuators.to_dict()

    async def set_actuators(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        before = self.actuators.to_dict()

        if "lights" in patch:
            self.actuators.lights = bool(patch["lights"])
        if "ventilation" in patch:
            self.actuators.ventilation = bool(patch["ventilation"])
        if "purifier" in patch:
            self.actuators.purifier = bool(patch["purifier"])
        if "target_temp" in patch:
            try:
                self.actuators.target_temp = clamp(float(patch["target_temp"]), 16.0, 30.0)
            except Exception:
                pass

        after = self.actuators.to_dict()
        await self.queue.put({"type": "actuators", "data": after})

        changes = {k: {"from": before[k], "to": after[k]} for k in after if before.get(k) != after.get(k)}
        if changes:
            self._push_event("info", "actuator", "执行器状态更新", meta={"changes": changes})

        return after

    # ===== events =====

    async def list_events(self, limit: int = 200, acked: Optional[bool] = None) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 1000))
        events = list(self._events)[-limit:]
        if acked is None:
            return [e.to_dict() for e in reversed(events)]
        return [e.to_dict() for e in reversed(events) if e.acked == acked]

    async def ack_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        for e in self._events:
            if e.id == event_id:
                e.acked = True
                return e.to_dict()
        return None

    async def ack_all(self, levels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        一键确认：把未确认的 events 按 level 批量 ack
        levels=None 表示全确认；推荐 levels=['warn','alarm']
        """
        levels_set = set(levels) if levels else None
        ids: List[int] = []
        for e in self._events:
            if e.acked:
                continue
            if levels_set is not None and e.level not in levels_set:
                continue
            e.acked = True
            ids.append(e.id)

        return {"ok": True, "acked": len(ids), "ids": ids}

    # ===== config =====

    async def get_config(self) -> Dict[str, Any]:
        return {"interval": self.interval, "sensors": [s.to_full_dict() for s in self.sensors]}

    async def set_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        changed: Dict[str, Any] = {}

        if "interval" in patch:
            try:
                new_interval = clamp(float(patch["interval"]), 0.2, 10.0)
                if abs(new_interval - self.interval) > 1e-9:
                    self.interval = new_interval
                    changed["interval"] = new_interval
            except Exception:
                pass

        sensor_updates = patch.get("sensors")
        if isinstance(sensor_updates, list):
            for item in sensor_updates:
                if not isinstance(item, dict):
                    continue
                sid = item.get("id")
                if not sid or sid not in self._sensor_by_id:
                    continue
                s = self._sensor_by_id[sid]
                before = s.to_full_dict()

                for key in ("warn_low", "warn_high", "gen_low", "gen_high", "step"):
                    if key in item:
                        try:
                            setattr(s, key, float(item[key]))
                        except Exception:
                            pass

                if s.gen_low > s.gen_high:
                    s.gen_low, s.gen_high = s.gen_high, s.gen_low
                if s.warn_low > s.warn_high:
                    s.warn_low, s.warn_high = s.warn_high, s.warn_low
                s.step = clamp(s.step, 0.01, 500.0)

                after = s.to_full_dict()
                if after != before:
                    changed.setdefault("sensors", []).append({"id": sid, "from": before, "to": after})

        if changed:
            await self.queue.put({"type": "config", "data": await self.get_config()})
            self._push_event("info", "config", "配置已更新", meta={"changed": changed})

        return await self.get_config()

    # ===== 新增：获取特殊事件信息 =====
    async def get_special_event_info(self) -> Dict[str, Any]:
        """获取当前特殊事件信息"""
        if self.current_event and self.event_end_time:
            remaining = (self.event_end_time - datetime.now(timezone.utc)).total_seconds()
            remaining = max(0, remaining)
            return {
                "event_type": self.current_event.value,
                "end_time": self.event_end_time.isoformat(),
                "remaining_seconds": remaining
            }
        return {"event_type": None, "end_time": None, "remaining_seconds": 0}

    async def start(self) -> None:
        """
        启动数据生成循环
        如果已经在跑就什么都不做
        使用 asyncio.create_task 把 _loop 跑在后台
        """
        # 已经有任务并且还在跑，直接返回
        if self._task is not None and not self._task.done():
            return

        # 确保 stop 事件是清空状态
        try:
            self._stop.clear()
        except AttributeError:
            # 理论上不会走到这里，只是兜底
            self._stop = asyncio.Event()

        # 起后台任务
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """
        停止数据生成循环（在 main.py 的 shutdown 里调用）
        """
        if self._task is None:
            return

        # 通知 _loop 退出
        self._stop.set()

        # 取消任务并吞掉 CancelledError
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None