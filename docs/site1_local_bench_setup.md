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
