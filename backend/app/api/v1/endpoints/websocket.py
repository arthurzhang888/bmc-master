import logging
from typing import Dict, List
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast(self, message: dict):
        """Broadcast to all connected clients with error handling."""
        disconnected = []
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to client {client_id}: {e}")
                    disconnected.append((client_id, connection))

        # Clean up disconnected clients
        for client_id, connection in disconnected:
            self.disconnect(connection, client_id)

    async def send_to_client(self, client_id: str, message: dict):
        """Send message to specific client with error handling."""
        if client_id not in self.active_connections:
            return

        disconnected = []
        for connection in self.active_connections[client_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to client {client_id}: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, client_id)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    client_id = f"client_{id(websocket)}"
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different message types
            message_type = data.get("type")

            if message_type == "subscribe":
                # Client subscribing to updates
                topics = data.get("topics", [])
                await websocket.send_json({
                    "type": "subscribed",
                    "topics": topics
                })

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)


# Function to broadcast sensor updates (called from monitoring tasks)
async def broadcast_sensor_update(server_id: str, sensor_data: dict):
    """Broadcast sensor update to all connected clients"""
    await manager.broadcast({
        "type": "sensor_update",
        "server_id": server_id,
        "data": sensor_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_server_status(server_id: str, status: str):
    """Broadcast server status change"""
    await manager.broadcast({
        "type": "server_status",
        "server_id": server_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    })
