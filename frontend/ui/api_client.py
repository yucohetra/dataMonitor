import os
import httpx


def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def build_headers(token: str | None) -> dict:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


async def post_json(path: str, json: dict, token: str | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.post(
            f"{get_api_base_url()}{path}",
            json=json,
            headers=build_headers(token),
        )


async def get(path: str, token: str | None = None, params: dict | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.get(
            f"{get_api_base_url()}{path}",
            headers=build_headers(token),
            params=params,
        )


async def patch_json(path: str, json: dict, token: str | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.patch(
            f"{get_api_base_url()}{path}",
            json=json,
            headers=build_headers(token),
        )


async def put_json(path: str, json: dict, token: str | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.put(
            f"{get_api_base_url()}{path}",
            json=json,
            headers=build_headers(token),
        )


async def delete(path: str, token: str | None = None):
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await client.delete(
            f"{get_api_base_url()}{path}",
            headers=build_headers(token),
        )


async def upload_csv(path: str, file_bytes: bytes, filename: str, token: str | None = None):
    """
    Upload CSV as multipart/form-data to match FastAPI UploadFile.
    """
    files = {"file": (filename, file_bytes, "text/csv")}
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await client.post(
            f"{get_api_base_url()}{path}",
            files=files,
            headers=build_headers(token),
        )


async def download(path: str, token: str | None = None, params: dict | None = None) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{get_api_base_url()}{path}",
            headers=build_headers(token),
            params=params,
        )
        resp.raise_for_status()
        return resp.content
