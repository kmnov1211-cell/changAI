# Setup Guide: Run Day‑1 KPI Baseline on your Bench (`site1.local`)

This guide is for your local VS Code bench where site name is `site1.local`.

---

## 1) Go to your bench folder

```bash
cd ~/frappe-bench
```

If your bench folder is different, use that path.

---

## 2) Make sure app is present and installed on your site

```bash
bench --site site1.local list-apps
```

If `changai` is not installed:

```bash
bench get-app changai https://github.com/erpgulf/changai
bench --site site1.local install-app changai
bench --site site1.local migrate
```

---

## 3) Open a bench console and read DB details

```bash
bench --site site1.local console
```

Inside python console, run:

```python
import frappe
print(frappe.conf.db_name)
print(frappe.conf.db_host)
print(frappe.conf.db_port)
print(frappe.conf.db_user)
```

Save these values, then exit console with:

```python
exit()
```

---


## 3.1) Build FAISS indexes with the correct module

In bench console:

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
build_all_fvs()
```

> This queues background jobs. Monitor worker logs to confirm completion:

```bash
bench worker --queue long
```

Required files in **Home/RAG Sources**:
- `tables.json`
- `schema.yaml`
- `master_data.yaml`

### What to do next after `build_all_fvs()` returns `{"status": "enqueued"}`

1) Keep long worker running in a separate terminal:

```bash
cd ~/frappe-bench
bench worker --queue long
```

2) Watch logs for progress/failures:

```bash
cd ~/frappe-bench
bench --site site1.local logs --web
bench --site site1.local show-pending-jobs
```

3) Check Error Log in Desk (if anything fails):

- Go to **Awesome Bar → Error Log**
- Filter by titles:
  - `Build Table FVS Failed`
  - `Build Schema FVS Failed`
  - `Build Master Data FVS Failed`

4) Verify index folders were created on disk:

```bash
cd ~/frappe-bench
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/table_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/schema_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/masterdata_fvs/
```

Expected each folder to contain `index.faiss` and `index.pkl`.

5) Optional quick verification from bench console:

```bash
bench --site site1.local console
```

```python
import os
base = 'sites/site1.local/private/changai/fvs_stores/erpnext'
for d in ['table_fvs', 'schema_fvs', 'masterdata_fvs']:
    p = os.path.join(base, d)
    print(d, os.path.exists(p), os.listdir(p) if os.path.exists(p) else [])
```

---


## 3.2) If pending jobs are empty and index folders are missing

If you see:
- `-----Pending Jobs-----` (empty)
- and no `table_fvs/`, `schema_fvs/`, `masterdata_fvs/`

then jobs were likely dequeued and failed quickly.

Run these checks in order.

### A) Confirm required File records exist in Desk

Open **Awesome Bar → File List** and verify under folder `Home/RAG Sources`:
- `tables.json`
- `schema.yaml`
- `master_data.yaml`

If any file is missing, upload it first, then run `build_all_fvs()` again.

### B) Verify file presence from bench console

```bash
bench --site site1.local console
```

```python
import frappe
for fn in ["tables.json", "schema.yaml", "master_data.yaml"]:
    doc = frappe.db.get_value(
        "File",
        {"file_name": fn, "folder": "Home/RAG Sources"},
        ["name", "file_url"],
        as_dict=True,
    )
    print(fn, "=>", doc)
```

### C) Check Error Log for exact failure reason

In Desk **Error Log**, filter for:
- `Build Table FVS Failed`
- `Build Schema FVS Failed`
- `Build Master Data FVS Failed`

### D) Make sure long worker is running while enqueueing

Terminal 1:

```bash
cd ~/frappe-bench
bench worker --queue long
```

Terminal 2:

```bash
cd ~/frappe-bench
bench --site site1.local console
```

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
build_all_fvs()
```

### E) Debug by running each job function directly (synchronous)

Use this only for debugging in console:

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import (
    build_table_fvs_job,
    build_schema_fvs_job,
    build_master_data_fvs_job,
)

build_table_fvs_job()
build_schema_fvs_job()
build_master_data_fvs_job()
```

If one fails, you will immediately see the traceback in console.

### F) Final verification

```bash
cd ~/frappe-bench
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/table_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/schema_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/masterdata_fvs/
```

Each store folder should contain:
- `index.faiss`
- `index.pkl`

---

## 4) Create a read-only DB user (recommended)

Use MariaDB root/admin account:

```bash
mysql -u root -p
```

Then run SQL (replace `<DB_NAME>` and password):

```sql
CREATE USER IF NOT EXISTS 'erp_readonly'@'localhost' IDENTIFIED BY 'StrongPassword@123';
GRANT SELECT ON `<DB_NAME>`.* TO 'erp_readonly'@'localhost';
FLUSH PRIVILEGES;
```

Exit MySQL:

```sql
exit;
```

---

## 5) Install dependency for Day‑1 script

From your app repo root (`/workspace/changAI`) or where script exists:

```bash
pip install pymysql
```

If using bench env explicitly:

```bash
~/frappe-bench/env/bin/pip install pymysql
```

---

## 6) Export env vars and run Day‑1 KPI baseline

From this repo root (where `scripts/day1_kpi_baseline.py` exists):

```bash
export ERP_DB_HOST=127.0.0.1
export ERP_DB_PORT=3306
export ERP_DB_USER=erp_readonly
export ERP_DB_PASSWORD='StrongPassword@123'
export ERP_DB_NAME='<DB_NAME>'
python scripts/day1_kpi_baseline.py
```

Expected output sections:

- `DB connection check: {'ok': 1}`
- `customer_count`
- `employee_count`
- `monthly_purchase_last_12m`
- `monthly_sales_last_12m`

---

## 7) If you want to run using bench python directly

```bash
~/frappe-bench/env/bin/python scripts/day1_kpi_baseline.py
```

---

## 8) Troubleshooting

### Error: `Missing dependency: pymysql`

Install with:

```bash
~/frappe-bench/env/bin/pip install pymysql
```

### Error: `Access denied for user`

- Check username/password.
- Ensure user has `SELECT` privilege on the exact DB.

### Error: table not found

Run in DB:

```sql
SHOW TABLES LIKE 'tabCustomer';
SHOW TABLES LIKE 'tabEmployee';
SHOW TABLES LIKE 'tabPurchase Invoice';
SHOW TABLES LIKE 'tabSales Invoice';
```

If table names differ in your ERPNext version/customization, update the SQL in `scripts/day1_kpi_baseline.py`.

---

## 9) Quick command block (copy/paste)

```bash
cd /workspace/changAI
~/frappe-bench/env/bin/pip install pymysql
export ERP_DB_HOST=127.0.0.1
export ERP_DB_PORT=3306
export ERP_DB_USER=erp_readonly
export ERP_DB_PASSWORD='StrongPassword@123'
export ERP_DB_NAME='<DB_NAME>'
~/frappe-bench/env/bin/python scripts/day1_kpi_baseline.py
```
