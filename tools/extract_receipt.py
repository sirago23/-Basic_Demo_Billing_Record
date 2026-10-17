"""Read a bank slip / receipt image with Claude vision and return a validated dict.

CLI: python tools/extract_receipt.py slip.jpg
"""
import base64
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

try:
    from tools.categories import CATEGORIES, FALLBACK, all_categories, is_valid
except ImportError:  # run as a script from tools/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from categories import CATEGORIES, FALLBACK, all_categories, is_valid

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL = "claude-sonnet-5-5"
MAX_BYTES = 5 * 1024 * 1024
MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


class ExtractError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _tool():
    return {
        "name": "record_transaction",
        "description": "บันทึกรายการรายรับหรือรายจ่ายที่อ่านได้จากสลิป/ใบเสร็จ",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["income", "expense"]},
                "amount": {"type": "number", "description": "จำนวนเงินเป็นบาท"},
                "category": {"type": "string", "enum": all_categories()},
                "date": {"type": "string", "description": "YYYY-MM-DD (ค.ศ.)"},
                "description": {"type": "string", "description": "ชื่อร้าน/ผู้รับ/ผู้โอน"},
            },
            "required": ["type", "amount", "category", "date", "description"],
        },
    }


def _system_prompt():
    owner = os.getenv("OWNER_NAME", "").strip() or "(ไม่ได้ระบุ)"
    return (
        "คุณอ่านสลิปโอนเงินธนาคารและใบเสร็จร้านค้าของไทย แล้วเรียก tool record_transaction เสมอ\n"
        f"เจ้าของบัญชีชื่อ: {owner}\n"
        "- ชื่อข้างต้นอาจมีหลายรูปแบบ (ไทย/อังกฤษ/ตัวย่อ) แต่เป็นบุคคลเดียวกัน "
        "สลิปแต่ละธนาคารแสดงชื่อต่างกัน อาจมีหรือไม่มีคำนำหน้า เป็นภาษาไทยหรืออังกฤษ ถูกตัดหรือย่อ "
        "หรือปิดบางตัวอักษรด้วย x/* ให้จับคู่แบบยืดหยุ่นโดยไม่ต้องตรงทุกตัวอักษร\n"
        "- ถ้าเจ้าของบัญชีเป็นผู้รับเงิน = income; ถ้าเป็นผู้โอน = expense; ใบเสร็จร้านค้า = expense\n"
        "- ปีในสลิปไทยมักเป็น พ.ศ. ให้แปลงเป็น ค.ศ. (ลบ 543) และตอบวันที่เป็น YYYY-MM-DD\n"
        "- description คือชื่อร้าน ผู้รับ หรือผู้โอน\n"
        f"- หมวดรายจ่าย: {', '.join(CATEGORIES['expense'])}\n"
        f"- หมวดรายรับ: {', '.join(CATEGORIES['income'])}\n"
        "- เลือกหมวดจากรายการนี้เท่านั้น และต้องตรงกับประเภท"
    )


def _normalize(raw):
    type_ = raw.get("type")
    if type_ not in ("income", "expense"):
        raise ExtractError("อ่านประเภทรายการจากรูปไม่ได้ กรุณากรอกเอง", 422)
    try:
        amount = float(raw.get("amount"))
    except (TypeError, ValueError):
        raise ExtractError("อ่านจำนวนเงินจากรูปไม่ได้ กรุณากรอกเอง", 422)
    if amount <= 0:
        raise ExtractError("อ่านจำนวนเงินจากรูปไม่ได้ กรุณากรอกเอง", 422)
    category = raw.get("category")
    if not is_valid(type_, category):
        category = FALLBACK
    try:
        d = date.fromisoformat(str(raw.get("date")))
    except ValueError:
        d = date.today()
    return {
        "type": type_,
        "amount": amount,
        "category": category,
        "date": d.isoformat(),
        "description": str(raw.get("description") or "").strip(),
    }


def _sniff(image_bytes, fallback):
    """Trust the file's magic bytes over the declared type/extension."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return fallback


def extract(image_bytes, media_type):
    media_type = _sniff(image_bytes, media_type)
    if media_type not in MEDIA_TYPES.values():
        raise ExtractError("รองรับเฉพาะไฟล์รูป JPG, PNG หรือ WEBP", 415)
    if len(image_bytes) > MAX_BYTES:
        raise ExtractError("ไฟล์ใหญ่เกิน 5MB", 413)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ExtractError("ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY ในไฟล์ .env กรุณากรอกรายการเอง", 503)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_system_prompt(),
            tools=[_tool()],
            tool_choice={"type": "auto"},  # this model rejects forced tool_choice; the prompt tells it to always call the tool
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode()}},
                    {"type": "text", "text": "อ่านสลิป/ใบเสร็จนี้และบันทึกรายการ"},
                ],
            }],
        )
    except anthropic.AuthenticationError:
        raise ExtractError("API key ไม่ถูกต้อง กรุณาตรวจสอบไฟล์ .env หรือกรอกรายการเอง", 401)
    except anthropic.BadRequestError as e:
        print(f"[extract_receipt] BadRequest: {e.message}", file=sys.stderr)
        raise ExtractError("อ่านรูปนี้ไม่ได้ กรุณาลองรูปอื่นหรือกรอกเอง", 422)
    except anthropic.APIError:
        raise ExtractError("เชื่อมต่อ AI ไม่ได้ในขณะนี้ กรุณาลองใหม่หรือกรอกเอง", 502)

    block = next((b for b in resp.content if b.type == "tool_use"), None)
    if block is None:
        raise ExtractError("AI อ่านรูปนี้ไม่ได้ อาจไม่ใช่สลิปหรือใบเสร็จ กรุณากรอกเอง", 422)
    return _normalize(block.input)


def extract_file(path):
    p = Path(path)
    media_type = MEDIA_TYPES.get(p.suffix.lower())
    if not media_type:
        raise ExtractError("รองรับเฉพาะไฟล์รูป JPG, PNG หรือ WEBP", 415)
    return extract(p.read_bytes(), media_type)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/extract_receipt.py <image>")
    try:
        print(json.dumps(extract_file(sys.argv[1]), ensure_ascii=False, indent=2))
    except ExtractError as e:
        sys.exit(f"[{e.status}] {e}")
