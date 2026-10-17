"""Insert ~30 demo transactions covering this month and last month.

Usage: python tools/seed_demo.py [--reset]
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import db  # noqa: E402

# (type, category, amount, description, month_offset, day)
ROWS = [
    ("income", "เงินเดือน", 45000, "เงินเดือน บริษัท", 0, 1),
    ("income", "งานฟรีแลนซ์", 12000, "ออกแบบโลโก้", 0, 8),
    ("income", "รับโอน", 1500, "เพื่อนโอนคืนค่าข้าว", 0, 12),
    ("income", "ขายของ", 2300, "ขายของมือสอง", 0, 15),
    ("income", "อื่นๆ", 500, "ดอกเบี้ยเงินฝาก", 0, 20),
    ("expense", "อาหาร/เครื่องดื่ม", 185, "ร้านกาแฟ", 0, 2),
    ("expense", "อาหาร/เครื่องดื่ม", 320, "ข้าวมื้อเย็น", 0, 5),
    ("expense", "เดินทาง", 120, "รถไฟฟ้า", 0, 3),
    ("expense", "เดินทาง", 450, "แท็กซี่", 0, 9),
    ("expense", "ช้อปปิ้ง", 1290, "เสื้อผ้า", 0, 6),
    ("expense", "บิล/สาธารณูปโภค", 890, "ค่าไฟ", 0, 10),
    ("expense", "ที่พัก", 8500, "ค่าเช่าห้อง", 0, 1),
    ("expense", "สุขภาพ", 650, "ค่ายา", 0, 14),
    ("expense", "บันเทิง", 419, "Netflix + เกม", 0, 11),
    ("expense", "โอนเงิน", 3000, "โอนให้ครอบครัว", 0, 4),
    ("expense", "อื่นๆ", 250, "ของใช้จิปาถะ", 0, 13),
    ("income", "เงินเดือน", 45000, "เงินเดือน บริษัท", -1, 1),
    ("income", "งานฟรีแลนซ์", 8000, "เขียนบทความ", -1, 18),
    ("income", "รับโอน", 2000, "ญาติโอนให้", -1, 22),
    ("income", "ขายของ", 1800, "ขายของออนไลน์", -1, 25),
    ("expense", "อาหาร/เครื่องดื่ม", 540, "บุฟเฟ่ต์", -1, 7),
    ("expense", "อาหาร/เครื่องดื่ม", 150, "ก๋วยเตี๋ยว", -1, 16),
    ("expense", "เดินทาง", 800, "น้ำมันรถ", -1, 8),
    ("expense", "ช้อปปิ้ง", 2400, "รองเท้า", -1, 12),
    ("expense", "บิล/สาธารณูปโภค", 1100, "ค่าอินเทอร์เน็ต + มือถือ", -1, 5),
    ("expense", "ที่พัก", 8500, "ค่าเช่าห้อง", -1, 1),
    ("expense", "สุขภาพ", 1200, "ตรวจสุขภาพ", -1, 20),
    ("expense", "บันเทิง", 700, "ดูหนัง", -1, 23),
    ("expense", "โอนเงิน", 2500, "โอนให้เพื่อน", -1, 10),
    ("expense", "อื่นๆ", 300, "ค่าธรรมเนียม", -1, 27),
]


def month_date(offset, day):
    today = date.today()
    idx = today.year * 12 + today.month - 1 + offset
    if offset == 0:
        day = min(day, today.day)  # no future-dated rows this month
    return date(idx // 12, idx % 12 + 1, day).isoformat()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    db.init_db()
    if "--reset" in sys.argv:
        db.delete_all()
    for type_, cat, amount, desc, off, day in ROWS:
        db.create({"type": type_, "amount": amount, "category": cat,
                   "date": month_date(off, day), "description": desc, "source": "manual"})
    print(f"เพิ่มข้อมูลตัวอย่าง {len(ROWS)} รายการแล้ว")


if __name__ == "__main__":
    main()
