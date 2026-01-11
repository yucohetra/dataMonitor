from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.services.realtime_service import WebSocketBroadcaster


router = APIRouter(tags=["websocket"])


def set_broadcaster(b: WebSocketBroadcaster):
    router.broadcaster = b


@router.websocket("/ws/realtime")
async def ws_realtime(websocket: WebSocket):
    # NOTE:
    # - Token is provided via query string to ensure compatibility with minimal clients.
    # - For production, prefer Authorization header or secure cookies to reduce token exposure in logs.
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        claims = decode_token(token)
        user_id = int(claims["sub"])
    except Exception:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        row = await session.execute(select(User).where(User.id == user_id))
        user = row.scalar_one_or_none()
        if user is None or not user.is_active:
            await websocket.close(code=1008)
            return

    await websocket.accept()
    await router.broadcaster.add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await router.broadcaster.remove(websocket)
    except Exception:
        await router.broadcaster.remove(websocket)
        await websocket.close()
