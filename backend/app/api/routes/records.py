import io
import csv
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_roles
from app.schemas.record import RecordCreate, RecordUpdate, RecordOut, PaginatedRecords
from app.services.record_service import RecordService
from app.services.log_service import LogService
from app.models.user import User

import openpyxl


router = APIRouter(prefix="/records", tags=["records"])


@router.post("", response_model=RecordOut, dependencies=[Depends(require_roles("ADMIN", "USER"))])
async def create_record(req: RecordCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    record = await RecordService.create(db, user.id, req.title, req.value, req.category, req.timestamp)
    await LogService.write(db, "INFO", "SYSTEM", "Record created", actor_user_id=user.id)
    return RecordOut(**record.__dict__)


@router.get("", response_model=PaginatedRecords)
async def list_records(
    page: int = 1,
    size: int = 50,
    category: str | None = None,
    is_anomaly: bool | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    items, total = await RecordService.list_records(
        db, page, size, category, is_anomaly, start_time, end_time, sort_by, order, created_by=None
    )
    return PaginatedRecords(
        items=[RecordOut(**i.__dict__) for i in items],
        page=page,
        size=size,
        total=total,
    )


@router.put("/{record_id}", response_model=RecordOut)
async def update_record(
    record_id: int,
    req: RecordUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = await RecordService.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    if user.role.name != "ADMIN" and record.created_by != user.id:
        await LogService.write(db, "WARN", "SYSTEM", "Update forbidden", actor_user_id=user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = await RecordService.update(
        db,
        record,
        title=req.title,
        value=req.value,
        category=req.category,
        timestamp=req.timestamp,
    )
    return RecordOut(**updated.__dict__)


@router.delete("/{record_id}")
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = await RecordService.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    if user.role.name != "ADMIN" and record.created_by != user.id:
        await LogService.write(db, "WARN", "SYSTEM", "Delete forbidden", actor_user_id=user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    await RecordService.delete(db, record)
    return {"status": "deleted"}


@router.post("/import", dependencies=[Depends(require_roles("ADMIN", "USER"))])
async def import_records(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    file: UploadFile | None = File(default=None),
):
    if file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is required")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    rows_ok = []
    errors = []
    now = datetime.now(timezone.utc)

    for idx, row in enumerate(reader, start=2):
        try:
            title = row.get("title", "").strip()
            category = row.get("category", "").strip()
            value = float(row.get("value", ""))

            ts_raw = (row.get("timestamp") or "").strip()
            ts = datetime.fromisoformat(ts_raw) if ts_raw else now

            if not title or not category:
                raise ValueError("title/category required")

            rows_ok.append({"title": title, "value": value, "category": category, "timestamp": ts})
        except Exception as e:
            errors.append({"row": idx, "reason": str(e)})

    inserted = 0
    if rows_ok:
        inserted = await RecordService.batch_insert(db, user.id, rows_ok)

    await LogService.write(
        db,
        "INFO",
        "DATA_IMPORT",
        "CSV import completed",
        detail=f"inserted={inserted}, errors={len(errors)}",
        actor_user_id=user.id,
    )

    return {"inserted": inserted, "errors": errors}


@router.get("/export")
async def export_records(
    page: int = 1,
    size: int = 5000,
    category: str | None = None,
    is_anomaly: bool | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    sort_by: str = "timestamp",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    items, _ = await RecordService.list_records(
        db, page, size, category, is_anomaly, start_time, end_time, sort_by, order, created_by=None
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "records"
    ws.append(["id", "title", "value", "category", "timestamp", "is_anomaly", "created_by"])

    for r in items:
        ws.append([r.id, r.title, r.value, r.category, r.timestamp.isoformat(), r.is_anomaly, r.created_by])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    filename = "records_export.xlsx"
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
