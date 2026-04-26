from __future__ import annotations

from collections import deque
from typing import Any

from textual.widget import Widget
from textual.widgets import Sparkline, Static

_MAX_HISTORY = 60


class RealtimeMetrics(Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._cpu_history: deque[float] = deque(maxlen=_MAX_HISTORY)
        self._mem_history: deque[float] = deque(maxlen=_MAX_HISTORY)

    def update_data(self, realtime: dict[str, Any]) -> None:
        cpu_pct = self._extract_cpu(realtime)
        mem_pct = self._extract_mem(realtime)
        if cpu_pct is not None:
            self._cpu_history.append(cpu_pct)
        if mem_pct is not None:
            self._mem_history.append(mem_pct)
        self._render_children()

    def _extract_cpu(self, rt: dict[str, Any]) -> float | None:
        for key in ("aggregations", "cpu", "cpu_usage"):
            obj = rt.get(key)
            if not isinstance(obj, dict):
                continue
            if key == "aggregations":
                cpu = obj.get("cpu", {})
                if isinstance(cpu, dict):
                    for k in ("avg", "usage", "percent", "cpu_usage"):
                        v = cpu.get(k)
                        if isinstance(v, (int, float)):
                            return float(v) if v <= 1.0 else float(v)
                        if isinstance(v, dict):
                            usage = v.get("usage")
                            if isinstance(usage, (int, float)):
                                return float(usage)
            elif key == "cpu":
                for core, metrics in obj.items():
                    if isinstance(metrics, dict):
                        for k in ("usage", "percent", "cpu_usage"):
                            v = metrics.get(k)
                            if isinstance(v, (int, float)):
                                return float(v) if v <= 1.0 else float(v)
            elif key == "cpu_usage":
                if isinstance(obj, dict):
                    v = obj.get("percent") or obj.get("usage")
                    if isinstance(v, (int, float)):
                        return float(v) if v <= 1.0 else float(v)

        if isinstance(rt.get("cpu"), (int, float)):
            return float(rt["cpu"])
        for k in ("cpu_percent", "cpu_usage", "cpu_usage_percent"):
            v = rt.get(k)
            if isinstance(v, (int, float)):
                return float(v) if v <= 1.0 else float(v)
        return None

    def _extract_mem(self, rt: dict[str, Any]) -> float | None:
        for key in ("aggregations", "memory"):
            obj = rt.get(key)
            if not isinstance(obj, dict):
                continue
            if key == "aggregations":
                mem = obj.get("memory", {})
                if isinstance(mem, dict):
                    for k in ("used_pct", "percent", "usage", "memory_usage"):
                        v = mem.get(k)
                        if isinstance(v, (int, float)):
                            return float(v)
            elif key == "memory":
                for k in ("used_pct", "percent", "usage", "memory_usage"):
                    v = obj.get(k)
                    if isinstance(v, (int, float)):
                        return float(v)
                used = obj.get("used")
                total = obj.get("total")
                if (
                    isinstance(used, (int, float))
                    and isinstance(total, (int, float))
                    and total > 0
                ):
                    return (used / total) * 100.0

        for k in ("memory_percent", "memory_usage", "mem_percent", "mem_used_pct"):
            v = rt.get(k)
            if isinstance(v, (int, float)):
                return float(v)
        return None

    def on_mount(self) -> None:
        self._render_children()

    def _render_children(self) -> None:
        for child in list(self.children):
            child.remove()

        self.mount(Static("Realtime", classes="card-title"))

        self.mount(Static("CPU Usage", classes="metric-label"))
        if self._cpu_history:
            self.mount(Sparkline(list(self._cpu_history), classes="metric-spark"))
        else:
            self.mount(Static("  waiting for data...", classes="metric-label"))

        self.mount(Static("Memory Usage", classes="metric-label"))
        if self._mem_history:
            self.mount(Sparkline(list(self._mem_history), classes="metric-spark"))
        else:
            self.mount(Static("  waiting for data...", classes="metric-label"))
