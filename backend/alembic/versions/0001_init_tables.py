"""init tables + seed roles/users

Revision ID: 0001_init_tables
Revises:
Create Date: 2026-01-11
"""

from alembic import op
import sqlalchemy as sa

from passlib.context import CryptContext

revision = "0001_init_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=32), nullable=False, unique=True),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("detail", sa.String(length=2048), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed roles
    op.execute("INSERT INTO roles (name) VALUES ('ADMIN'), ('USER'), ('VIEWER')")

    # Seed users (Password: Password123!)
    # NOTE:
    # - Hash is a bcrypt hash of "Password123!" for demonstration purposes.
    # bcrypt_hash = "$2b$12$S93CZTCCO0DFLzDnHLW4/e6rV0WXFDxK/UIxxCAkOrZu4spGQrgya"
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    bcrypt_hash = pwd.hash("Password123!")


    op.execute(
        "INSERT INTO users (email, username, password_hash, role_id, is_active) "
        "VALUES "
        f"('admin@example.com','admin','{bcrypt_hash}', (SELECT id FROM roles WHERE name='ADMIN'), 1),"
        f"('user@example.com','user','{bcrypt_hash}', (SELECT id FROM roles WHERE name='USER'), 1),"
        f"('viewer@example.com','viewer','{bcrypt_hash}', (SELECT id FROM roles WHERE name='VIEWER'), 1),"
        f"('system@example.com','system','{bcrypt_hash}', (SELECT id FROM roles WHERE name='ADMIN'), 1)"
    )


def downgrade():
    op.drop_table("system_logs")
    op.drop_table("data_records")
    op.drop_table("users")
    op.drop_table("roles")
