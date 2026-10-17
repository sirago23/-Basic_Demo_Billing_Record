"""Delete all transactions. Usage: python tools/reset_db.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import db  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
db.init_db()
db.delete_all()
print("ล้างรายการทั้งหมดแล้ว")
