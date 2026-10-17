"""Fixed category lists shared by backend, AI prompt and frontend."""

CATEGORIES = {
    "expense": [
        "อาหาร/เครื่องดื่ม", "เดินทาง", "ช้อปปิ้ง", "บิล/สาธารณูปโภค",
        "ที่พัก", "สุขภาพ", "บันเทิง", "โอนเงิน", "อื่นๆ",
    ],
    "income": ["เงินเดือน", "งานฟรีแลนซ์", "รับโอน", "ขายของ", "อื่นๆ"],
}

FALLBACK = "อื่นๆ"


def all_categories():
    seen = []
    for cats in CATEGORIES.values():
        for c in cats:
            if c not in seen:
                seen.append(c)
    return seen


def is_valid(type_, category):
    return category in CATEGORIES.get(type_, [])
