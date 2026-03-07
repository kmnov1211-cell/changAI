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


### B.1) Quick fix when all 3 are `None` (create starter RAG source files)

If all three checks return `None`, run this in **bench console** to generate starter files from shipped assets and upload to `Home/RAG Sources`:

```python
import json
import yaml
import frappe
from pathlib import Path
from frappe.utils.file_manager import save_file
import base64

app_path = Path(frappe.get_app_path("changai"))
assets_dir = app_path / "changai" / "api" / "v2" / "assets"
metaschema_path = assets_dir / "metaschema_clean_v2.json"

with open(metaschema_path, "r", encoding="utf-8") as f:
    metaschema = json.load(f)  # {table_name: [field1, field2, ...]}

# 1) tables.json
all_tables = sorted(list(metaschema.keys()))
tables_json = json.dumps(all_tables, ensure_ascii=False, indent=2)

# 2) schema.yaml
schema = {
    "tables": [
        {
            "table": t,
            "module": "ERPNext",
            "fields": [
                {"name": fld, "description": ""}
                for fld in (metaschema.get(t) or [])
                if isinstance(fld, str) and fld.strip()
            ],
        }
        for t in all_tables
    ]
}
schema_yaml = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True)

# 3) master_data.yaml (starter; replace with your real master entities later)
master_data = {
    "data": [
        {
            "entity_type": "customer",
            "entity_id": "CUST-0001",
            "canonical_name": "Sample Customer",
            "aliases": ["Sample Cust"],
            "description": "Starter customer entity",
        },
        {
            "entity_type": "supplier",
            "entity_id": "SUP-0001",
            "canonical_name": "Sample Supplier",
            "aliases": ["Sample Supp"],
            "description": "Starter supplier entity",
        },
        {
            "entity_type": "item",
            "entity_id": "ITEM-0001",
            "canonical_name": "Sample Item",
            "aliases": ["Sample SKU"],
            "description": "Starter item entity",
        },
    ]
}
master_data_yaml = yaml.safe_dump(master_data, sort_keys=False, allow_unicode=True)

# Save into Home/RAG Sources (compatible with save_file signatures that require dt/dn)
def _upsert_file(file_name: str, content_bytes: bytes):
    existing = frappe.db.get_value(
        "File",
        {"file_name": file_name, "folder": "Home/RAG Sources"},
        "name",
    )
    if existing:
        frappe.delete_doc("File", existing, force=1, ignore_permissions=True)

    # Some Frappe versions require dt and dn positional args
    save_file(file_name, content_bytes, None, None, folder="Home/RAG Sources", is_private=1)

_upsert_file("tables.json", tables_json.encode("utf-8"))
_upsert_file("schema.yaml", schema_yaml.encode("utf-8"))
_upsert_file("master_data.yaml", master_data_yaml.encode("utf-8"))

frappe.db.commit()
print("Uploaded: tables.json, schema.yaml, master_data.yaml to Home/RAG Sources")
```

If you still get `save_file` argument errors, use this fallback (File DocType insert):

```python
import base64

def _upsert_file_doc(file_name: str, text_content: str):
    existing = frappe.db.get_value(
        "File",
        {"file_name": file_name, "folder": "Home/RAG Sources"},
        "name",
    )
    if existing:
        frappe.delete_doc("File", existing, force=1, ignore_permissions=True)

    frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "folder": "Home/RAG Sources",
        "is_private": 1,
        "content": text_content,
        "decode": False,
    }).insert(ignore_permissions=True)

_upsert_file_doc("tables.json", tables_json)
_upsert_file_doc("schema.yaml", schema_yaml)
_upsert_file_doc("master_data.yaml", master_data_yaml)
frappe.db.commit()
```

Now rerun:

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
build_all_fvs()
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


## 3.3) Right bench-console code (copy/paste)

Use this exact code in `bench --site site1.local console` when files are missing and `save_file` signatures differ.
It also auto-creates missing Folder path `Home/RAG Sources` to avoid `LinkValidationError`.

```python
import json
import yaml
import frappe
from pathlib import Path

# Build starter content from shipped asset
app_path = Path(frappe.get_app_path("changai"))
metaschema_path = app_path / "changai" / "api" / "v2" / "assets" / "metaschema_clean_v2.json"
with open(metaschema_path, "r", encoding="utf-8") as f:
    metaschema = json.load(f)  # {table_name: [field1, field2, ...]}

all_tables = sorted(metaschema.keys())

tables_json = json.dumps(all_tables, ensure_ascii=False, indent=2)

schema = {
    "tables": [
        {
            "table": t,
            "module": "ERPNext",
            "fields": [
                {"name": fld, "description": ""}
                for fld in (metaschema.get(t) or [])
                if isinstance(fld, str) and fld.strip()
            ],
        }
        for t in all_tables
    ]
}
schema_yaml = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True)

master_data = {
    "data": [
        {"entity_type": "customer", "entity_id": "CUST-0001", "canonical_name": "Sample Customer", "aliases": ["Sample Cust"], "description": "Starter customer entity"},
        {"entity_type": "supplier", "entity_id": "SUP-0001", "canonical_name": "Sample Supplier", "aliases": ["Sample Supp"], "description": "Starter supplier entity"},
        {"entity_type": "item", "entity_id": "ITEM-0001", "canonical_name": "Sample Item", "aliases": ["Sample SKU"], "description": "Starter item entity"},
    ]
}
master_data_yaml = yaml.safe_dump(master_data, sort_keys=False, allow_unicode=True)

# Ensure folder path exists: Home/RAG Sources
def ensure_folder_path(path: str = "Home/RAG Sources"):
    parts = path.split("/")
    current = parts[0]  # Home
    for part in parts[1:]:
        next_path = f"{current}/{part}"
        exists = frappe.db.exists("File", {"file_name": part, "folder": current, "is_folder": 1})
        if not exists:
            frappe.get_doc({
                "doctype": "File",
                "file_name": part,
                "is_folder": 1,
                "folder": current,
            }).insert(ignore_permissions=True)
        current = next_path

ensure_folder_path("Home/RAG Sources")

# Version-safe upload using save_file signature that may require dt/dn
from frappe.utils.file_manager import save_file

def upsert_rag_file(file_name: str, content: str):
    existing = frappe.db.get_value(
        "File",
        {"file_name": file_name, "folder": "Home/RAG Sources"},
        "name",
    )
    if existing:
        frappe.delete_doc("File", existing, force=1, ignore_permissions=True)

    save_file(
        file_name,
        content.encode("utf-8"),
        None,
        None,
        folder="Home/RAG Sources",
        is_private=1,
    )

upsert_rag_file("tables.json", tables_json)
upsert_rag_file("schema.yaml", schema_yaml)
upsert_rag_file("master_data.yaml", master_data_yaml)
frappe.db.commit()

for fn in ["tables.json", "schema.yaml", "master_data.yaml"]:
    print(fn, "=>", frappe.db.get_value("File", {"file_name": fn, "folder": "Home/RAG Sources"}, ["name", "file_url"], as_dict=True))

from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
print(build_all_fvs())
```

Then in terminal run:

```bash
cd ~/frappe-bench
bench worker --queue long
```



## 3.4) Fix `safetensors header too large` / SentenceTransformer version mismatch

If worker logs show errors like:
- `safetensors_rust.SafetensorError: Error while deserializing header: header too large`
- `model was created with Sentence Transformers 5.2.3, but you are using 5.1.2`

then your local embedding model files are usually corrupted/incomplete (often Git LFS pointers instead of real weights) or your Python packages are older than the model metadata.


> Important: `changai` pins `sentence-transformers==5.1.2` in `pyproject.toml`.
> Upgrading only sentence-transformers/transformers can create resolver conflicts and runtime import errors.

### A) Stop worker and update python packages in bench env

```bash
cd ~/frappe-bench
# Stop running worker with Ctrl+C first
./env/bin/pip install -e apps/changai  # reinstall app-pinned dependencies
```

### A.1) Ensure Git LFS is installed (required for model weights)

```bash
cd ~/frappe-bench
git lfs version
# if command is missing, install Git LFS then run:
git lfs install
```

### B) Remove local cached embedding model folder

```bash
cd ~/frappe-bench
rm -rf apps/changai/changai/changai/model
```

### C) Re-download model from bench console

```bash
bench --site site1.local console
```

```python
from changai.changai.api.v2.text2sql_pipeline_v2 import download_model_from_ui
print(download_model_from_ui())
```

Expected:

```python
{'status': 'success', 'message': 'Embedding model downloaded successfully.'}
```

If download succeeds but load still fails, run manual LFS pull using the actual resolved model path:

```bash
cd ~/trackerr
MODEL_PATH=$(./env/bin/python - <<'PY2'
import os
import frappe
frappe.init(site='site1.local')
frappe.connect()
print(frappe.get_app_path('changai', 'changai', 'changai', 'model'))
frappe.destroy()
PY2
)
echo "$MODEL_PATH"
cd "$MODEL_PATH"
git lfs pull
```

> Note: if your terminal shows weird prefixes like `[200~`, bracketed paste mode injected extra characters.
> Re-type commands manually (or paste with Ctrl+Shift+V in a clean prompt).

### D) Validate embedding loads before enqueueing jobs

```python
from changai.changai.api.v2.text2sql_pipeline_v2 import get_embedding_engine
emb = get_embedding_engine()
print(type(emb))
```

If this works, your worker should no longer fail at model load step.

### E) Start long worker and enqueue again

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
print(build_all_fvs())
```

### F) Re-verify generated indexes

```bash
cd ~/frappe-bench
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/table_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/schema_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/masterdata_fvs/
```

Each folder should contain `index.faiss` and `index.pkl`.

---


## 3.5) Fix `ImportError` from `sentence_transformers` / `transformers` (Python 3.14 env)

If you see errors like:
- `ImportError: cannot import name 'is_flash_attention_requested' from transformers.utils.generic`
- `ImportError: Could not import sentence_transformers python package`

this is typically a **mixed/incompatible package set** in bench env (often after partial upgrades), and can be worse on Python 3.14.

### A) Check current versions in bench env

```bash
cd ~/frappe-bench
./env/bin/python -V
./env/bin/pip show sentence-transformers transformers langchain-huggingface safetensors tokenizers | sed -n '1,120p'
```

### B) Re-sync to app-pinned dependency set (recommended)

```bash
cd ~/frappe-bench
./env/bin/pip uninstall -y sentence-transformers transformers tokenizers safetensors huggingface-hub
./env/bin/pip install -e apps/changai

# optional: if pip resolver keeps stale packages
./env/bin/pip install --upgrade --force-reinstall -e apps/changai
```

### C) Sanity import test before running worker jobs

```bash
cd ~/frappe-bench
./env/bin/python - <<'PY2'
import sentence_transformers, transformers, safetensors
print('sentence-transformers', sentence_transformers.__version__)
print('transformers', transformers.__version__)
print('safetensors', safetensors.__version__)

# should match app constraints (pyproject): sentence-transformers==5.1.2
PY2
```

### D) Recreate embedding model directory and test in bench console

```bash
cd ~/frappe-bench
rm -rf apps/changai/changai/changai/model
bench --site site1.local console
```

```python
from changai.changai.api.v2.text2sql_pipeline_v2 import download_model_from_ui, get_embedding_engine
print(download_model_from_ui())
emb = get_embedding_engine()
print(type(emb))
```

### E) Re-run FAISS build jobs

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
print(build_all_fvs())
```

And in another terminal:

```bash
cd ~/frappe-bench
bench worker --queue long
```

### F) If still broken on Python 3.14

Create a fresh bench on Python **3.11 or 3.12** and install apps there; current ML stack is generally better tested on those versions.

---


## 3.6) If you see warnings but job status is `Job OK`

If worker output shows:
- `Successfully completed ... Job OK`
- plus warnings like:
  - `model was created with Sentence Transformers 5.2.3, but you're using 5.1.2`
  - `resource_tracker: leaked semaphore objects`

then treat it as:
- ✅ **Index build succeeded** for that job.
- ⚠️ You still should clean up package mismatch to avoid future instability.

### A) First verify files are really generated

```bash
cd ~/trackerr
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/table_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/schema_fvs/
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/masterdata_fvs/
```

Each folder should contain `index.faiss` and `index.pkl`.

### B) Keep app-pinned versions (recommended for stability)

```bash
cd ~/trackerr
./env/bin/pip install -e apps/changai  # reinstall app-pinned dependencies
```

Then restart worker:

```bash
cd ~/trackerr
bench restart
bench worker --queue long
```

### C) About leaked semaphore warnings

`resource_tracker` warnings are usually from multiprocessing cleanup on shutdown.
If jobs are finishing with `Job OK`, you can proceed. Restarting worker often clears them.

---


## 3.7) Partial success: `table_fvs` + `masterdata_fvs` exist but `schema_fvs` is empty

If you see:
- `table_fvs/index.faiss` + `index.pkl` present
- `masterdata_fvs/index.faiss` + `index.pkl` present
- `schema_fvs/` exists but has no index files

then only schema job failed or produced 0 docs.

### A) Run schema job directly to get immediate traceback

```bash
cd ~/trackerr
bench --site site1.local console
```

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_schema_fvs_job
build_schema_fvs_job()
```

### B) Validate `schema.yaml` exists and has `tables:` with fields

```python
import frappe, yaml
name = frappe.db.get_value("File", {"file_name": "schema.yaml", "folder": "Home/RAG Sources"}, "name")
print("file doc:", name)
content = frappe.get_doc("File", name).get_content()
obj = yaml.safe_load(content)
print("has tables:", isinstance(obj, dict) and 'tables' in obj)
print("tables count:", len(obj.get('tables', [])) if isinstance(obj, dict) else 0)
if isinstance(obj, dict) and obj.get('tables'):
    print("sample:", obj['tables'][0])
```

`schema.yaml` must be shaped like:

```yaml
tables:
  - table: tabSales Invoice
    module: Selling
    fields:
      - name: posting_date
        description: Posting date
```

### C) Re-enqueue all jobs after fixing schema

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
print(build_all_fvs())
```

Run worker:

```bash
cd ~/trackerr
bench worker --queue long
```

### D) Final check

```bash
cd ~/trackerr
ls -lah sites/site1.local/private/changai/fvs_stores/erpnext/schema_fvs/
```

Expected files:
- `index.faiss`
- `index.pkl`

---


## 3.8) `Connection refused` to Redis while calling `build_all_fvs()`

If console shows errors like:
- `ConnectionError: Error 111 connecting to 127.0.0.1:11006` (or `13006`)
- stack trace from `frappe.enqueue` / `redis` / `rq`

this means background job queue backend (Redis) is down or unreachable.
This is **not related to Ollama URL**.

### A) Check Redis/bench services

```bash
cd ~/trackerr
bench doctor
```

If Redis/queue workers are not healthy, restart bench services:

```bash
cd ~/trackerr
bench restart
```

### B) Validate configured Redis URLs

```bash
cd ~/trackerr
./env/bin/python - <<'PY2'
import json
from pathlib import Path
cfg = json.loads(Path('sites/common_site_config.json').read_text())
for k in ['redis_queue','redis_cache','redis_socketio']:
    print(k, '=>', cfg.get(k))
PY2
```

Expected queue URL host/port must match your running Redis instance.

### C) Verify Redis port is listening

```bash
cd ~/trackerr
ss -ltnp | grep -E '11006|13006|redis'
# if grep is unavailable, use: ss -ltnp
```

If nothing is listening on the configured queue port, start/restart services:

```bash
cd ~/trackerr
bench restart
# then keep worker running
bench worker --queue long
```


If `bench restart` is not managing processes in your setup, run dev stack directly in a separate terminal:

```bash
cd ~/trackerr
bench start
```

Then retry `bench doctor` and enqueue.

### D) Retry enqueue after Redis is healthy

```bash
cd ~/trackerr
bench --site site1.local console
```

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
print(build_all_fvs())
```

If Redis is temporarily down and you need a one-time local run, use synchronous fallback in console:

```python
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs
from changai.changai.api.v2.build_cards_faiss_index_v2 import build_all_fvs_sync
print(build_all_fvs_sync())
```


If you get `TypeError: build_all_fvs() got an unexpected keyword argument 'run_sync_if_queue_down'`,
your bench is still on older changai code. Update app code and migrate, then retry.

```bash
cd ~/trackerr
bench update --apps changai
bench --site site1.local migrate
bench restart
```

### E) Important note about Ollama URL

`http://localhost:11434` in ChangAI Settings is for LLM calls.
FAISS build jobs (`build_all_fvs`) are queued via Redis/RQ and do not depend on Ollama availability.

---


## 3.9) Ollama memory error (`model requires more system memory`)

If you get:

- `model requires more system memory (4.3 GiB) than is available (2.0 GiB)`

this is an LLM RAM limitation on your machine, not a FAISS/index issue.

### A) Use a smaller model in ChangAI Settings

In **ChangAI Settings** for local mode, set `local_llm` to a lighter model such as:
- `qwen2.5:1.5b`
- `qwen2.5:0.5b`
- `tinyllama:1.1b`

### B) Pull and test small model directly in Ollama

```bash
ollama pull qwen2.5:1.5b
curl http://localhost:11434/api/generate -d '{
  "model":"qwen2.5:1.5b",
  "prompt":"Write SQL to count customers in ERPNext",
  "stream":false
}'
```

### C) Keep only one model loaded (free RAM)

```bash
ollama ps
# stop running model session by restarting ollama service/process if needed
```

### D) Optional quality/performance path

If results are weak on very small models, keep FAISS local but move SQL generation to a stronger remote model later (Phase 2).

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

From your app repo root (for many bench installs: `~/trackerr/apps/changai`) or wherever this repository is cloned:

```bash
pip install pymysql
```

If using bench env explicitly:

```bash
~/trackerr/env/bin/pip install pymysql
```

---

## 6) Export env vars and run Day‑1 KPI baseline

From this repo root (where `scripts/day1_kpi_baseline.py` exists).
Typical local bench path is `~/trackerr/apps/changai`:

```bash
export ERP_DB_HOST=127.0.0.1
export ERP_DB_PORT=3306
export ERP_DB_USER=erp_readonly
export ERP_DB_PASSWORD='StrongPassword@123'
export ERP_DB_NAME='<DB_NAME>'
~/trackerr/env/bin/python scripts/day1_kpi_baseline.py
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
~/trackerr/env/bin/python scripts/day1_kpi_baseline.py
```

---

## 8) Troubleshooting

### Error: `Missing dependency: pymysql`

Install with:

```bash
~/trackerr/env/bin/pip install pymysql
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

If you are not sure where changai repo is on disk, locate it first:

```bash
cd ~/trackerr
find apps -maxdepth 2 -type d -name changai
```

Use the returned directory as your repo root for running the script.

## 9) Quick command block (copy/paste)

```bash
cd ~/trackerr/apps/changai
~/trackerr/env/bin/pip install pymysql
export ERP_DB_HOST=127.0.0.1
export ERP_DB_PORT=3306
export ERP_DB_USER=erp_readonly
export ERP_DB_PASSWORD='StrongPassword@123'
export ERP_DB_NAME='<DB_NAME>'
~/trackerr/env/bin/python scripts/day1_kpi_baseline.py
```
