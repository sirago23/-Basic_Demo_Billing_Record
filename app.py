from datetime import date as date_cls
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from tools import db
from tools.categories import CATEGORIES
from tools.extract_receipt import ExtractError, extract

BASE = Path(__file__).resolve().parent
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"

app = FastAPI(title="Billing record")
db.init_db()


class TransactionIn(BaseModel):
    type: str
    amount: float = Field(gt=0)
    category: str
    date: str
    description: str = ""
    source: str = "manual"

    @field_validator("type")
    @classmethod
    def _type(cls, v):
        if v not in CATEGORIES:
            raise ValueError("type ต้องเป็น income หรือ expense")
        return v

    @field_validator("date")
    @classmethod
    def _date(cls, v):
        date_cls.fromisoformat(v)
        return v

    @field_validator("source")
    @classmethod
    def _source(cls, v):
        if v not in ("slip", "manual"):
            raise ValueError("source ต้องเป็น slip หรือ manual")
        return v

    @model_validator(mode="after")
    def _category(self):
        if self.category not in CATEGORIES[self.type]:
            raise ValueError("หมวดหมู่ไม่ตรงกับประเภทรายการ")
        return self


@app.get("/api/categories")
def categories():
    return CATEGORIES


@app.get("/api/transactions")
def list_transactions(month: Optional[str] = Query(None, pattern=MONTH_PATTERN)):
    return db.list_transactions(month)


@app.post("/api/transactions", status_code=201)
def create_transaction(t: TransactionIn):
    return db.create(t.model_dump())


@app.put("/api/transactions/{id}")
def update_transaction(id: int, t: TransactionIn):
    row = db.update(id, t.model_dump())
    if row is None:
        raise HTTPException(404, "ไม่พบรายการ")
    return row


@app.delete("/api/transactions/{id}")
def delete_transaction(id: int):
    if not db.delete(id):
        raise HTTPException(404, "ไม่พบรายการ")
    return {"ok": True}


@app.get("/api/summary")
def summary(month: Optional[str] = Query(None, pattern=MONTH_PATTERN)):
    return db.summary(month)


@app.post("/api/extract")
async def extract_slip(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return extract(data, file.content_type or "")
    except ExtractError as e:
        return JSONResponse({"detail": str(e)}, status_code=e.status)


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
