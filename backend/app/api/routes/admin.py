from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.models.role import Role
from app.models.system_log import SystemLog
from app.schemas.admin import UserOut, UpdateUserRoleRequest
from app.schemas.system import SystemStatusOut, DbStatusOut
from app.db.session import db_ping


router = APIRouter(prefix="/admin", tags=["admin"])

_runtime_status_provider = None


def set_runtime_status_provider(provider):
    global _runtime_status_provider
    _runtime_status_provider = provider

@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_roles("ADMIN"))])
async def list_users(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(User.id, User.email, User.username, Role.name, User.is_active)
        .join(Role, Role.id == User.role_id)
        .order_by(User.id.asc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        UserOut(
            id=r[0],
            email=r[1],
            username=r[2],
            role=r[3],
            is_active=r[4],
        )
        for r in rows
    ]


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_roles("ADMIN"))])
async def update_user_role(user_id: int, req: UpdateUserRoleRequest, db: AsyncSession = Depends(get_db)):
    role_name = req.role.strip().upper()
    row_role = await db.execute(select(Role).where(Role.name == role_name))
    role = row_role.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    row_user = await db.execute(select(User).where(User.id == user_id))
    user = row_user.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role_id = role.id
    await db.commit()
    return {"status": "updated", "user_id": user_id, "role": role_name}


@router.get("/logs", dependencies=[Depends(require_roles("ADMIN"))])
async def list_logs(limit: int = 200, db: AsyncSession = Depends(get_db)):
    stmt = select(SystemLog).order_by(SystemLog.id.desc()).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": l.id,
            "level": l.level,
            "event_type": l.event_type,
            "message": l.message,
            "detail": l.detail,
            "actor_user_id": l.actor_user_id,
            "created_at": l.created_at,
        }
        for l in logs
    ]


@router.get("/system/status", response_model=SystemStatusOut, dependencies=[Depends(require_roles("ADMIN"))])
async def system_status():
    if _runtime_status_provider is None:
        raise HTTPException(status_code=500, detail="Runtime status provider not initialized")
    return await _runtime_status_provider()


@router.get("/db/status", response_model=DbStatusOut, dependencies=[Depends(require_roles("ADMIN"))])
async def db_status(db: AsyncSession = Depends(get_db)):
    connected = await db_ping()
    version = None
    try:
        row = await db.execute(text("SELECT VERSION()"))
        version = row.scalar_one_or_none()
    except Exception:
        version = None

    return DbStatusOut(
        db_connected=connected,
        db_version=version,
        server_time=datetime.now(timezone.utc),
    )
