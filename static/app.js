const fmt = new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB', minimumFractionDigits: 2 });
const $ = (id) => document.getElementById(id);
const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6', '#0891b2', '#db2777', '#65a30d', '#64748b'];

let categories = { expense: [], income: [] };
let currentType = 'expense';
let editingId = null;
const store = {
  get() { try { return sessionStorage.getItem('month') || ''; } catch (_) { return ''; } },
  set(v) { try { sessionStorage.setItem('month', v); } catch (_) {} },
};
let month = store.get();
const onAdd = !!$('form'), onSummary = !!$('c-income'), onList = !!$('tbody');
const charts = {};

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = 'เกิดข้อผิดพลาด';
    try {
      const body = await res.json();
      msg = typeof body.detail === 'string' ? body.detail : 'ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบอีกครั้ง';
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function setStatus(text, cls = '') {
  const s = $('status');
  s.textContent = text;
  s.className = cls;
}

/* ---------- form ---------- */
function setType(type, keepCategory) {
  currentType = type;
  document.querySelectorAll('#type-toggle button').forEach((b) => b.classList.toggle('active', b.dataset.type === type));
  const prev = $('category').value;
  const sel = $('category');
  sel.replaceChildren(...categories[type].map((c) => new Option(c, c)));
  if (keepCategory && categories[type].includes(prev)) sel.value = prev;
}

function clearHighlights() {
  document.querySelectorAll('.ai-filled').forEach((e) => e.classList.remove('ai-filled'));
}

function resetForm() {
  editingId = null;
  usedSlip = false;
  $('form').reset();
  $('date').value = todayStr();
  setType('expense');
  $('form-title').textContent = 'เพิ่มรายการ';
  $('submit').textContent = 'บันทึก';
  $('cancel').hidden = true;
  clearHighlights();
  clearPreview();
}

function clearPreview() {
  $('preview').hidden = true;
  $('preview').removeAttribute('src');
  $('drop-text').hidden = false;
  $('file').value = '';
}

if (onAdd) {
document.querySelectorAll('#type-toggle button').forEach((b) =>
  b.addEventListener('click', () => setType(b.dataset.type)));

$('cancel').addEventListener('click', () => { resetForm(); setStatus(''); });

$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const wasEditing = !!editingId;
  const payload = {
    type: currentType,
    amount: parseFloat($('amount').value),
    category: $('category').value,
    date: $('date').value,
    description: $('description').value.trim(),
    source: usedSlip ? 'slip' : 'manual',
  };
  try {
    if (editingId) {
      await api(`/api/transactions/${editingId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    } else {
      await api('/api/transactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    }
    usedSlip = false;
    if (wasEditing) { location.href = '/list'; return; }
    resetForm();
    setStatus('บันทึกแล้ว', 'ok');
  } catch (err) {
    setStatus(err.message, 'error');
  }
});
}

let usedSlip = false;

/* ---------- slip upload ---------- */

async function handleFile(file) {
  if (!file) return;
  clearHighlights();
  const url = URL.createObjectURL(file);
  $('preview').src = url;
  $('preview').hidden = false;
  $('drop-text').hidden = true;
  setStatus('กำลังอ่านสลิป...');
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await api('/api/extract', { method: 'POST', body: fd });
    editingId = null;
    $('form-title').textContent = 'เพิ่มรายการ';
    $('submit').textContent = 'บันทึก';
    $('cancel').hidden = true;
    setType(r.type);
    $('category').value = r.category;
    $('amount').value = r.amount;
    $('date').value = r.date;
    $('description').value = r.description;
    ['amount', 'category', 'date', 'description'].forEach((id) => $(id).classList.add('ai-filled'));
    document.querySelector(`#type-toggle button[data-type=${r.type}]`).classList.add('ai-filled');
    usedSlip = true;
    setStatus('อ่านสลิปแล้ว กรุณาตรวจสอบก่อนกดบันทึก', 'ok');
  } catch (err) {
    setStatus(err.message.includes('กรอก') ? err.message : err.message + ' (กรอกรายการเองได้)', 'error');
  }
}

if (onAdd) {
const drop = $('drop');
$('file').addEventListener('change', (e) => handleFile(e.target.files[0]));
drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('file').click(); } });
['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', (e) => handleFile(e.dataTransfer.files[0]));
}


/* ---------- summary ---------- */
function renderChart(id, rows) {
  const canvas = $(id);
  const empty = canvas.parentElement.querySelector('.empty');
  if (charts[id]) charts[id].destroy();
  canvas.hidden = rows.length === 0;
  empty.hidden = rows.length > 0;
  if (!rows.length) return;
  const total = rows.reduce((s, r) => s + r.total, 0);
  charts[id] = new Chart(canvas, {
    type: 'pie',
    data: {
      labels: rows.map((r) => r.category),
      datasets: [{ data: rows.map((r) => r.total), backgroundColor: rows.map((_, i) => COLORS[i % COLORS.length]) }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { font: { size: 16, family: 'Sarabun' } } },
        tooltip: {
          bodyFont: { size: 16, family: 'Sarabun' },
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${fmt.format(ctx.parsed)} (${((ctx.parsed / total) * 100).toFixed(1)}%)`,
          },
        },
      },
    },
  });
}

async function loadSummary() {
  const q = month ? `?month=${month}` : '';
  const s = await api(`/api/summary${q}`);
  if (onSummary) {
    $('c-income').textContent = fmt.format(s.income);
    $('c-expense').textContent = fmt.format(s.expense);
    $('c-balance').textContent = fmt.format(s.balance);
    renderChart('chart-expense', s.by_category.expense);
    renderChart('chart-income', s.by_category.income);
  }
  const sel = $('month');
  const options = [new Option('ทั้งหมด', '')].concat(s.months.map((m) => new Option(monthLabel(m), m)));
  if (month && !s.months.includes(month)) month = '';
  sel.replaceChildren(...options);
  sel.value = month;
}

function monthLabel(m) {
  const [y, mo] = m.split('-').map(Number);
  return new Date(y, mo - 1, 1).toLocaleDateString('th-TH-u-ca-gregory', { year: 'numeric', month: 'long' });
}

if ($('month')) $('month').addEventListener('change', (e) => { month = e.target.value; store.set(month); refresh(); });

/* ---------- table ---------- */
function cell(text, cls) {
  const td = document.createElement('td');
  td.textContent = text;
  if (cls) td.className = cls;
  return td;
}

async function loadTable() {
  const q = month ? `?month=${month}` : '';
  const rows = await api(`/api/transactions${q}`);
  $('table-empty').hidden = rows.length > 0;
  $('tbody').replaceChildren(...rows.map((r) => {
    const tr = document.createElement('tr');
    const sign = r.type === 'income' ? '+' : '−';
    tr.append(
      cell(r.date),
      cell(r.type === 'income' ? 'รายรับ' : 'รายจ่าย', r.type),
      cell(r.category),
      cell(r.description),
      cell(`${sign}${fmt.format(r.amount)}`, `num ${r.type}`),
    );
    const act = document.createElement('td');
    const edit = document.createElement('button');
    edit.className = 'small'; edit.textContent = 'แก้ไข';
    edit.addEventListener('click', () => startEdit(r));
    const del = document.createElement('button');
    del.className = 'small del'; del.textContent = 'ลบ';
    del.addEventListener('click', () => remove(r));
    act.append(edit, del);
    tr.append(act);
    return tr;
  }));
}

function startEdit(r) {
  location.href = `/add?id=${r.id}`;
}

function loadEdit(r) {
  clearHighlights();
  clearPreview();
  usedSlip = false;
  editingId = r.id;
  setType(r.type);
  $('category').value = r.category;
  $('amount').value = r.amount;
  $('date').value = r.date;
  $('description').value = r.description;
  $('form-title').textContent = 'แก้ไขรายการ';
  $('submit').textContent = 'อัปเดต';
  $('cancel').hidden = false;
  setStatus('');
}

async function remove(r) {
  if (!confirm(`ลบรายการ "${r.description || r.category}" จำนวน ${fmt.format(r.amount)} ใช่หรือไม่?`)) return;
  try {
    await api(`/api/transactions/${r.id}`, { method: 'DELETE' });
    await refresh();
  } catch (err) {
    alert(err.message);
  }
}

async function refresh() {
  if (onSummary || onList) await loadSummary();
  if (onList) await loadTable();
}

(async function init() {
  if (onAdd) {
    categories = await api('/api/categories');
    resetForm();
    const id = Number(new URLSearchParams(location.search).get('id'));
    if (id) {
      const row = (await api('/api/transactions')).find((r) => r.id === id);
      if (row) loadEdit(row); else setStatus('ไม่พบรายการที่ต้องการแก้ไข', 'error');
    }
  }
  await refresh();
})();
