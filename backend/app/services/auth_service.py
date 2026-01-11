from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.role import Role
from app.core.rbac import RoleName


class AuthService:
    """
    Handles user registration and login.

    Design considerations:
    - Uses strong password hashing (bcrypt).
    - Assigns a default role on registration to ensure deterministic access control.
    """

    @staticmethod
    async def register(session: AsyncSession, email: str, username: str, password: str) -> User:
        existing = await session.execute(
            select(User).where((User.email == email) | (User.username == username))
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError("Email or username already exists")

        role_row = await session.execute(select(Role).where(Role.name == RoleName.USER.value))
        default_role = role_row.scalar_one()

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role_id=default_role.id,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def login(session: AsyncSession, email: str, password: str) -> tuple[str, int, str]:

        stmt = (
            select(User)
            .options(joinedload(User.role))
            .where(User.email == email)
        )

        result = await session.execute(stmt)
        user = result.unique().scalar_one_or_none()

        # row = await session.execute(select(User).where(User.email == email))
        # user = row.scalar_one_or_none()
        if user is None or not user.is_active:
            raise ValueError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")

        role_name = user.role.name
        token, expire_minutes = create_access_token(subject=str(user.id), role=role_name)
        return token, expire_minutes, role_name

