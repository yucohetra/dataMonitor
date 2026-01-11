from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: str
    is_active: bool


class UpdateUserRoleRequest(BaseModel):
    role: str  # ADMIN/USER/VIEWER
