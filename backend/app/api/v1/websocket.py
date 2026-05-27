"""WebSocket real-time communication API for task updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_subscriptions: Dict[str, set] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        for subs in self.task_subscriptions.values():
            subs.discard(client_id)

    def subscribe_task(self, client_id: str, task_id: str):
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(client_id)

    async def send_message(self, message: dict, client_id: str):
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, message: dict):
        for client_id in list(self.active_connections.keys()):
            await self.send_message(message, client_id)

    async def send_task_update(self, task_id: str, data: dict):
        subs = self.task_subscriptions.get(task_id, set())
        if not subs:
            return
        message = {
            "type": "agent_step",
            "task_id": task_id,
            "data": data,
        }
        for client_id in list(subs):
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    self.disconnect(client_id)

    async def send_device_status(self, device_id: str, status: str):
        message = {"type": "device_status", "device_id": device_id, "status": status}
        await self.broadcast(message)


manager = ConnectionManager()


@router.websocket("/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "subscribe":
                task_id = data.get("task_id")
                if task_id:
                    manager.subscribe_task(client_id, task_id)
                    await manager.send_message(
                        {"type": "subscribed", "task_id": task_id}, client_id
                    )
            elif msg_type == "ping":
                await manager.send_message({"type": "pong"}, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        manager.disconnect(client_id)
