"""SQLite storage for transactions."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "billing.db"

COLUMNS = ("type", "amount", "category", "date", "description", "source")


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('income','expense')),
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('slip','manual')),
                created_at TEXT NOT NULL
            )"""
        )


def _month_clause(month):
    return ("WHERE substr(date,1,7) = ?", [month]) if month else ("", [])


def list_transactions(month=None):
    where, params = _month_clause(month)
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM transactions {where} ORDER BY date DESC, id DESC", params
        ).fetchall()
    return [dict(r) for r in rows]


def get(id_):
    with _conn() as c:
        row = c.execute("SELECT * FROM transactions WHERE id = ?", (id_,)).fetchone()
    return dict(row) if row else None


def create(data):
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO transactions (type, amount, category, date, description, source, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (data["type"], data["amount"], data["category"], data["date"],
             data.get("description", ""), data.get("source", "manual"),
             datetime.now().isoformat(timespec="seconds")),
        )
        new_id = cur.lastrowid
    return get(new_id)


def update(id_, data):
    with _conn() as c:
        cur = c.execute(
            """UPDATE transactions SET type=?, amount=?, category=?, date=?, description=?
               WHERE id=?""",
            (data["type"], data["amount"], data["category"], data["date"],
             data.get("description", ""), id_),
        )
        if cur.rowcount == 0:
            return None
    return get(id_)


def delete(id_):
    with _conn() as c:
        return c.execute("DELETE FROM transactions WHERE id = ?", (id_,)).rowcount > 0


def delete_all():
    with _conn() as c:
        c.execute("DELETE FROM transactions")


def summary(month=None):
    where, params = _month_clause(month)
    with _conn() as c:
        totals = {r["type"]: r["t"] for r in c.execute(
            f"SELECT type, SUM(amount) t FROM transactions {where} GROUP BY type", params)}
        by_cat = {"income": [], "expense": []}
        for r in c.execute(
            f"""SELECT type, category, SUM(amount) t FROM transactions {where}
                GROUP BY type, category ORDER BY t DESC""", params):
            by_cat[r["type"]].append({"category": r["category"], "total": r["t"]})
        months = [r["m"] for r in c.execute(
            "SELECT DISTINCT substr(date,1,7) m FROM transactions ORDER BY m DESC")]
    income = totals.get("income", 0) or 0
    expense = totals.get("expense", 0) or 0
    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
        "by_category": by_cat,
        "months": months,
    }
