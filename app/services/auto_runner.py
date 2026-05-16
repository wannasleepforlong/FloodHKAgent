from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from app.models.schemas import FloodAlertOutput, RunMode
from app.services.utils import add_minutes, utc_now
from app.settings import Settings


class HorizonAutoRunService:
    def __init__(
        self,
        *,
        settings: Settings,
        run_callback: Callable[[RunMode], Awaitable[FloodAlertOutput]],
    ):
        self.settings = settings
        self._run_callback = run_callback
        self._enabled = False
        self._next_run_at: datetime | None = None
        self._task: asyncio.Task[Any] | None = None
        self._signal = asyncio.Event()
        self._run_lock = asyncio.Lock()

    async def run_manual(self, mode: RunMode = RunMode.LIVE) -> FloodAlertOutput:
        output = await self._run_once(mode=mode)
        self._arm_from_output(output)
        return output

    def get_status(self) -> dict[str, Any]:
        return {
            "active": self._enabled,
            "horizon_minutes": self.settings.prediction_horizon_minutes,
            "next_run_at": self._next_run_at.isoformat() if self._next_run_at is not None else None,
        }

    async def aclose(self) -> None:
        task = self._task
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_once(self, *, mode: RunMode) -> FloodAlertOutput:
        async with self._run_lock:
            return await self._run_callback(mode)

    def _arm_from_output(self, output: FloodAlertOutput) -> None:
        self._enabled = True
        self._next_run_at = add_minutes(
            output.generated_at,
            self.settings.prediction_horizon_minutes,
        )
        self._ensure_task()
        self._signal.set()
        print(
            "[scheduler] armed auto-run "
            f"every {self.settings.prediction_horizon_minutes} minutes "
            f"next={self._next_run_at.isoformat()}"
        )

    def _ensure_task(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="flood-horizon-auto-runner")

    async def _loop(self) -> None:
        while True:
            if not self._enabled or self._next_run_at is None:
                self._signal.clear()
                await self._signal.wait()
                continue

            due_at = self._next_run_at
            delay_seconds = max(0.0, (due_at - utc_now()).total_seconds())
            self._signal.clear()
            try:
                await asyncio.wait_for(self._signal.wait(), timeout=delay_seconds)
                continue
            except TimeoutError:
                pass

            async with self._run_lock:
                if not self._enabled or self._next_run_at != due_at:
                    continue
                now = utc_now()
                if self._next_run_at is None or now < self._next_run_at:
                    continue
                try:
                    output = await self._run_callback(RunMode.LIVE)
                except Exception as exc:
                    self._next_run_at = add_minutes(now, self.settings.prediction_horizon_minutes)
                    self._signal.set()
                    print(
                        "[scheduler] auto-run failed; rearming from current time "
                        f"next={self._next_run_at.isoformat()} error={exc}"
                    )
                    continue
                self._next_run_at = add_minutes(
                    output.generated_at,
                    self.settings.prediction_horizon_minutes,
                )
                print(
                    "[scheduler] auto-run completed "
                    f"run={output.run_id} next={self._next_run_at.isoformat()}"
                )
