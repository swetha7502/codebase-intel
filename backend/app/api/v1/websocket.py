"""
WebSocket endpoint: streams real-time ingestion progress to the frontend.
Subscribes to Redis pub/sub channel for the given repository.
"""
import json
import redis.asyncio as aioredis

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ingestion/{repo_id}")
async def ingestion_progress(websocket: WebSocket, repo_id: str):
    await websocket.accept()

    r = aioredis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"ingestion:{repo_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Close connection once ingestion is done or failed
                if data.get("stage") in ("complete", "failed"):
                    break

    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"ingestion:{repo_id}")
        await r.aclose()
