"""
EcoSight — Connection Watchdog

Monitors phone↔server connectivity and triggers a guardian SMS
if the client cannot reconnect after repeated failures.

Lifecycle:
    1. Client connects  → watchdog.register(ws)
    2. Client sends ping / location_update → watchdog.heartbeat(ws, ...)
    3. Client disconnects → watchdog.on_disconnect(ws)
         • Starts a reconnect-window timer.
         • If the SAME client reconnects within the window → counter resets.
         • If the window expires → increment fail count.
         • After MAX failures → fire guardian SMS with last known location.
    4. Client reconnects  → watchdog.register(ws)  (resets counters)
"""

import asyncio
import time
from dataclasses import dataclass, field

import config
from guardian_alert import send_guardian_alert


@dataclass
class ClientRecord:
    """Per-client tracking state."""
    addr: str  # "ip:port" identifier
    last_heartbeat: float = field(default_factory=time.time)
    latitude: float | None = None
    longitude: float | None = None
    consecutive_failures: int = 0
    alert_sent: bool = False
    _watchdog_task: asyncio.Task | None = field(default=None, repr=False)


class ConnectionWatchdog:
    """
    Tracks connected clients and fires guardian alerts on
    sustained disconnection.
    """

    def __init__(self):
        # keyed by client address string "ip:port"
        self._clients: dict[str, ClientRecord] = {}

    # ── public API called from ws_handler ─────────────────────────

    def register(self, ws) -> None:
        """Called when a client connects (or re-connects)."""
        addr = self._addr(ws)
        existing = self._clients.get(addr)

        if existing and existing._watchdog_task and not existing._watchdog_task.done():
            existing._watchdog_task.cancel()
            print(f"[Watchdog] Client {addr} reconnected — cancelled watchdog timer")

        self._clients[addr] = ClientRecord(addr=addr)
        print(f"[Watchdog] Registered client {addr}")

    def heartbeat(
        self,
        ws,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> None:
        """Called on every ping or location_update from the client."""
        addr = self._addr(ws)
        rec = self._clients.get(addr)
        if rec is None:
            rec = ClientRecord(addr=addr)
            self._clients[addr] = rec

        rec.last_heartbeat = time.time()
        if latitude is not None:
            rec.latitude = latitude
        if longitude is not None:
            rec.longitude = longitude

    def on_disconnect(self, ws) -> None:
        """Called when the WebSocket stream closes."""
        addr = self._addr(ws)
        rec = self._clients.get(addr)
        if rec is None:
            return

        print(f"[Watchdog] Client {addr} disconnected — "
              f"starting reconnect window ({config.WATCHDOG_RECONNECT_WINDOW_SEC}s)")

        # Launch an async task that waits for the reconnect window
        rec._watchdog_task = asyncio.ensure_future(
            self._reconnect_window(addr)
        )

    # ── internal ──────────────────────────────────────────────────

    async def _reconnect_window(self, addr: str) -> None:
        """Wait for the reconnect window; if client doesn't come back,
        count it as a failure and possibly alert the guardian."""
        try:
            await asyncio.sleep(config.WATCHDOG_RECONNECT_WINDOW_SEC)
        except asyncio.CancelledError:
            # Client reconnected before the window expired
            return

        rec = self._clients.get(addr)
        if rec is None:
            return

        rec.consecutive_failures += 1
        print(
            f"[Watchdog] Client {addr} did NOT reconnect — "
            f"failure {rec.consecutive_failures}/{config.WATCHDOG_MAX_RECONNECT_ATTEMPTS}"
        )

        if rec.consecutive_failures >= config.WATCHDOG_MAX_RECONNECT_ATTEMPTS:
            if not rec.alert_sent:
                rec.alert_sent = True
                print(f"[Watchdog] ⚠️  Max retries exceeded — sending guardian alert!")
                send_guardian_alert(
                    latitude=rec.latitude,
                    longitude=rec.longitude,
                )
        else:
            # Not yet at max — wait for next window
            rec._watchdog_task = asyncio.ensure_future(
                self._reconnect_window(addr)
            )

    @staticmethod
    def _addr(ws) -> str:
        """Stable identifier for a WebSocket client."""
        host, port = ws.remote_address[:2]
        return f"{host}:{port}"
