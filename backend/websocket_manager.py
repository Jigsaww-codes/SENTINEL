import json
from typing import List
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event_type: str, data: dict):
        msg = json.dumps({"type": event_type, "data": data}, default=str)
        for ws in list(self.active):
            try:
                await ws.send_text(msg)
            except Exception:
                self.disconnect(ws)


manager = WebSocketManager()
