# Run the billing demo

## Objective
Run the income/expense web app locally and present it in a live demo.

## Setup (once)
1. `python -m venv .venv` then `.venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`, then fill in:
   - `ANTHROPIC_API_KEY` — key for the Claude API (needed only for slip reading)
   - `OWNER_NAME` — your name exactly as it appears on slips; used to decide income vs expense

## Run
- `uvicorn app:app --reload`, then open http://localhost:8000
- API docs for testing: http://localhost:8000/docs

## Demo data
- Load sample data (~30 rows, this month and last): `python tools/seed_demo.py --reset`
- Clear everything: `python tools/reset_db.py`

## Suggested demo order
1. Show the summary: cards, two pie charts, switch month in the dropdown.
2. Upload a transfer-out slip → highlighted fields appear in the form (not saved yet) → fix if needed → Save.
3. Upload an incoming-transfer slip and a shop receipt.
4. Add a row by hand; edit one (button becomes "อัปเดต"); delete one.

## Test the slip reader alone
`python tools/extract_receipt.py <slip.jpg>` — costs about 1 baht per slip (real API call).

## Troubleshooting
- "ยังไม่ได้ตั้งค่า ANTHROPIC_API_KEY": `.env` missing or key empty. Manual entry still works.
- Wrong income/expense: check `OWNER_NAME` matches the name on the slip.
- Charts blank: Chart.js loads from a CDN, so the machine needs internet.
- Accepted images: JPG, PNG, WEBP up to 5MB. No PDF, no multi-upload; the image is not stored.
