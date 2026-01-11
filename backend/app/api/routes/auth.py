from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import AuthService
from app.services.log_service import LogService
from app.models.user import User  # Used for re-query with eager load.

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService.register(db, req.email, req.username, req.password)

        # Avoid async lazy-loading that can raise MissingGreenlet.
        row = await db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == user.id)
        )
        user = row.scalar_one()

        await LogService.write(db, "INFO", "AUTH", "User registered", actor_user_id=user.id)
        return {"id": user.id, "email": user.email, "username": user.username, "role": user.role.name}

    except ValueError as e:
        await LogService.write(db, "WARN", "AUTH", "Registration failed", detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token, expire_minutes, role = await AuthService.login(db, req.email, req.password)
        await LogService.write(db, "INFO", "AUTH", "Login success")
        return TokenResponse(access_token=token, role=role, expires_in_minutes=expire_minutes)
    except ValueError as e:
        await LogService.write(db, "WARN", "AUTH", "Login failed", detail=str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
