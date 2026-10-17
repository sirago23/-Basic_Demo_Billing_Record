# แผน: Webapp บันทึกรายรับ-รายจ่าย (สำหรับเดโมสด)

## Context
ต้องการ webapp สำหรับบันทึกรายรับ/รายจ่าย ใช้คนเดียว รันบนเครื่องตัวเอง (Windows, Python 3.14) สำหรับโชว์ในเดโมสด ตั้งเป้าสร้างให้เสร็จใน 2-3 ชม.
- อัปโหลดสลิปธนาคาร/ใบเสร็จ (JPG/PNG) → Claude API อ่านค่าและจัดหมวดหมู่ → แสดงฟอร์มให้ตรวจ/แก้ก่อนกดบันทึก
- กรอกรายการเองได้
- สรุปด้วยแผนภูมิวงกลม 2 วง (รายจ่ายตามหมวด, รายรับตามหมวด) + การ์ด รายรับรวม/รายจ่ายรวม/คงเหลือ เลือกดูรายเดือนหรือทั้งหมดได้
- ตารางรายการที่แก้ไขและลบได้
- โฟลเดอร์โปรเจกต์ตอนนี้ยังว่าง ไม่มีโค้ดเดิมให้ใช้ต่อ

## สิ่งที่ตกลงกันแล้ว
| เรื่อง | ที่เลือก |
|---|---|
| AI | Claude API (`claude-sonnet-5-5`, vision + tool use เพื่อให้ได้ JSON ตาม schema) |
| Stack | Python FastAPI + HTML/JS ล้วน + Chart.js (CDN) ไม่มีขั้นตอน build |
| ที่เก็บข้อมูล | SQLite (`data/billing.db`) |
| หลังอ่านสลิป | ใส่ค่าลงฟอร์มให้ตรวจก่อน แล้วค่อยบันทึก |
| หมวดหมู่ | รายการตายตัว AI ต้องเลือกจากรายการนี้เท่านั้น |
| เงินเข้า/ออก | เทียบกับ `OWNER_NAME` ใน `.env`: ถ้าเราเป็นผู้รับ = รายรับ, ถ้าเราเป็นผู้โอน = รายจ่าย, ใบเสร็จร้านค้า = รายจ่าย |
| UI | ภาษาไทย หน้าเดียว ตัวอักษรใหญ่ เหมาะกับฉายโปรเจกเตอร์ |
| ข้อมูลตัวอย่าง | สคริปต์ seed (~30 รายการ 2 เดือน) + สคริปต์ล้างข้อมูล |
| ไม่ทำ | อัปโหลดหลายรูปพร้อมกัน, PDF, เก็บรูปสลิป (รูปใช้อ่านแล้วทิ้ง) |

**หมวดหมู่ตายตัว**
- รายจ่าย: อาหาร/เครื่องดื่ม, เดินทาง, ช้อปปิ้ง, บิล/สาธารณูปโภค, ที่พัก, สุขภาพ, บันเทิง, โอนเงิน, อื่นๆ
- รายรับ: เงินเดือน, งานฟรีแลนซ์, รับโอน, ขายของ, อื่นๆ

## โครงสร้างไฟล์ (ตามแบบ WAT)
```
Basic Demo Billing record/
├─ app.py                  # FastAPI: API routes + เสิร์ฟ static/
├─ tools/
│  ├─ db.py                # SQLite: init, CRUD, summary queries
│  ├─ categories.py        # รายการหมวดหมู่ (ใช้ร่วมกันทั้ง backend, prompt, frontend)
│  ├─ extract_receipt.py   # เรียก Claude vision → dict ที่ผ่านการตรวจแล้ว (รันจาก CLI ได้: python tools/extract_receipt.py slip.jpg)
│  ├─ seed_demo.py         # ใส่ข้อมูลตัวอย่าง
│  └─ reset_db.py          # ล้างข้อมูล
├─ static/
│  ├─ index.html
│  ├─ app.js
│  └─ style.css
├─ workflows/
│  └─ run_billing_demo.md  # SOP: ติดตั้ง, รัน, seed/reset, ขั้นตอนเดโม, วิธีแก้ปัญหา
├─ data/                   # billing.db (gitignored)
├─ requirements.txt        # fastapi, uvicorn[standard], anthropic, python-dotenv, python-multipart
├─ .env.example            # ANTHROPIC_API_KEY=, OWNER_NAME=
└─ .gitignore
```

## รายละเอียดการทำงาน

### ฐานข้อมูล (`tools/db.py`)
ตาราง `transactions`: `id INTEGER PK, type TEXT ('income'|'expense'), amount REAL, category TEXT, date TEXT (YYYY-MM-DD), description TEXT, source TEXT ('slip'|'manual'), created_at TEXT`
ฟังก์ชัน: `init_db()`, `list_transactions(month=None)`, `create()`, `update()`, `delete()`, `summary(month=None)` ซึ่งคืนค่ายอดรวมรายรับ/รายจ่าย/คงเหลือ, ยอดรวมแยกตามหมวดของแต่ละประเภท และรายการเดือนที่มีข้อมูล

### API (`app.py`)
- `GET /api/categories`
- `GET /api/transactions?month=YYYY-MM` (ไม่ส่ง month = ทั้งหมด)
- `POST /api/transactions` · `PUT /api/transactions/{id}` · `DELETE /api/transactions/{id}`
- `GET /api/summary?month=YYYY-MM`
- `POST /api/extract` (multipart รับรูป) → คืนค่า `{type, amount, category, date, description}` **แต่ยังไม่บันทึก**
- ตรวจข้อมูลด้วย Pydantic: amount > 0, category ต้องอยู่ในรายการของ type นั้น
- `/` เสิร์ฟ `static/index.html`

### การอ่านสลิป (`tools/extract_receipt.py`)
- อ่านรูปแล้วแปลงเป็น base64 (รับ jpeg/png/webp ไม่เกิน 5MB) ส่งให้ Claude โดยบังคับให้เรียก tool `record_transaction` ซึ่งมี input schema ดังนี้: `type` enum, `amount` number, `category` enum (รวมหมวดทั้งหมด), `date` (YYYY-MM-DD), `description` (ชื่อร้าน/ผู้รับ/ผู้โอน)
- system prompt ระบุชื่อ `OWNER_NAME`, กฎเงินเข้า/ออก, การแปลงปี พ.ศ. → ค.ศ. (สลิปไทยมักใช้ปี พ.ศ.) และรายการหมวด
- ตรวจผลลัพธ์อีกรอบ: ถ้าหมวดไม่ตรงกับ type ให้ใช้ "อื่นๆ", ถ้าไม่มีวันที่ให้ใช้วันนี้
- ถ้าเกิดข้อผิดพลาด (ไม่มี key, API ล่ม, รูปอ่านไม่ออก) ให้คืน 4xx/5xx พร้อมข้อความภาษาไทย ส่วน frontend ยังให้กรอกเองได้

### หน้าเว็บ (`static/`)
หน้าเดียว แบ่งเป็น 3 ส่วน:
1. **เพิ่มรายการ**: โซนลากวาง/เลือกรูปพร้อมพรีวิว + สถานะ "กำลังอ่านสลิป..." และฟอร์ม (สลับ รายรับ/รายจ่าย, จำนวนเงิน, หมวด (dropdown เปลี่ยนตาม type), วันที่, รายละเอียด) ฟอร์มเดียวกันนี้ใช้ทั้งกรอกเองและรับค่าจาก AI โดยช่องที่ AI กรอกให้จะถูกไฮไลต์
2. **สรุป**: dropdown เดือน ("ทั้งหมด" + เดือนที่มีข้อมูล), การ์ด 3 ใบ, แผนภูมิวงกลม Chart.js 2 วง (มี legend และ tooltip แสดงยอดบาทและ %)
3. **ตารางรายการ**: กรองตามเดือนเดียวกับส่วนสรุป มีปุ่มแก้ไข (โหลดค่าลงฟอร์ม ปุ่มเปลี่ยนเป็น "อัปเดต") และปุ่มลบ (มี confirm) ทุกครั้งที่บันทึก/แก้/ลบ ให้รีเฟรชส่วนสรุปและตาราง
- จัดรูปเงินแบบ `฿1,234.00` (`Intl.NumberFormat('th-TH')`) ใช้ฟอนต์ Sarabun/Noto Sans Thai จาก Google Fonts

### สคริปต์ seed/reset
- `seed_demo.py`: ~30 รายการ ครอบคลุมเดือนนี้และเดือนก่อน ทุกหมวดมีข้อมูล (มีตัวเลือก `--reset` ให้ล้างก่อน seed)
- `reset_db.py`: ลบรายการทั้งหมด

### Workflow
`workflows/run_billing_demo.md`: วิธีติดตั้ง (venv + `pip install -r requirements.txt`), ตั้งค่า `.env`, รันด้วย `uvicorn app:app --reload` แล้วเปิด http://localhost:8000, คำสั่ง seed/reset, ลำดับขั้นตอนเดโมที่แนะนำ และปัญหาที่พบบ่อย

## ลำดับการสร้าง (~2-2.5 ชม.)
1. โครงโปรเจกต์ + requirements + `.env.example` + `categories.py` + `db.py` (20 นาที)
2. `app.py` CRUD + summary แล้วทดสอบด้วย `/docs` (20 นาที)
3. `extract_receipt.py` ทดสอบผ่าน CLI ด้วยสลิปจริง 1-2 ใบ (30 นาที)
4. Frontend: ฟอร์ม + ตาราง + แผนภูมิ (50 นาที)
5. seed/reset + workflow + ขัดเกลา (20 นาที)

## การตรวจสอบ
1. `pip install -r requirements.txt` แล้วรัน `python tools/seed_demo.py --reset` และ `uvicorn app:app` → หน้าเว็บแสดงการ์ด แผนภูมิ 2 วง และตารางครบ
2. สลับเดือนใน dropdown แล้วตัวเลขในการ์ด แผนภูมิ และตารางต้องเปลี่ยนตาม และรวมกันได้เท่ากับยอด "ทั้งหมด"
3. ทดสอบกรอกเอง เพิ่ม แก้ และลบรายการ ส่วนสรุปต้องอัปเดตทันที
4. รัน `python tools/extract_receipt.py <สลิป>` ด้วยสลิปโอนออก, สลิปรับโอน และใบเสร็จร้านค้า แต่ละใบต้องได้ type, ยอดเงิน, วันที่ (ค.ศ.) และหมวดที่ถูกต้อง (ใช้ API จริง ค่าใช้จ่ายราว 1 บาทต่อใบ)
5. อัปโหลดสลิปผ่าน UI แล้วค่าต้องขึ้นในฟอร์มโดยยังไม่บันทึก จากนั้นกดบันทึกแล้วรายการต้องปรากฏในตาราง
6. ทดสอบกรณีผิดพลาด: เอา API key ออก หรืออัปโหลดรูปที่ไม่ใช่สลิป ต้องมีข้อความภาษาไทยแจ้ง และแอปต้องไม่พัง
7. เปิดด้วย Playwright เพื่อถ่ายภาพหน้าจอดูความเรียบร้อยที่ความกว้าง 1920px
