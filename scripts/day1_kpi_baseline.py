#!/usr/bin/env python3
"""Day-1 baseline checks for ERPNext AI agent build.

Purpose:
- Validate DB connectivity
- Validate the 4 mandatory KPI queries before adding any LLM

Usage:
  export ERP_DB_HOST=127.0.0.1
  export ERP_DB_PORT=3306
  export ERP_DB_USER=readonly_user
  export ERP_DB_PASSWORD='***'
  export ERP_DB_NAME=erpnext_site_db
  python scripts/day1_kpi_baseline.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Iterable

try:
    import pymysql
except ImportError as exc:  # pragma: no cover - user environment setup issue
    raise SystemExit(
        "Missing dependency: pymysql. Install with: pip install pymysql"
    ) from exc


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str

    @staticmethod
    def from_env() -> "DBConfig":
        required = {
            "ERP_DB_HOST": os.getenv("ERP_DB_HOST"),
            "ERP_DB_PORT": os.getenv("ERP_DB_PORT", "3306"),
            "ERP_DB_USER": os.getenv("ERP_DB_USER"),
            "ERP_DB_PASSWORD": os.getenv("ERP_DB_PASSWORD"),
            "ERP_DB_NAME": os.getenv("ERP_DB_NAME"),
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            raise SystemExit(
                f"Missing environment variables: {', '.join(missing)}"
            )

        return DBConfig(
            host=required["ERP_DB_HOST"],
            port=int(required["ERP_DB_PORT"]),
            user=required["ERP_DB_USER"],
            password=required["ERP_DB_PASSWORD"],
            database=required["ERP_DB_NAME"],
        )


QUERIES: list[tuple[str, str]] = [
    (
        "customer_count",
        """
        SELECT COUNT(*) AS customer_count
        FROM `tabCustomer`
        WHERE IFNULL(disabled, 0) = 0;
        """,
    ),
    (
        "employee_count",
        """
        SELECT COUNT(*) AS employee_count
        FROM `tabEmployee`
        WHERE status = 'Active';
        """,
    ),
    (
        "monthly_purchase_last_12m",
        """
        SELECT
            DATE_FORMAT(posting_date, '%Y-%m') AS month,
            ROUND(SUM(base_grand_total), 2) AS purchase_amount
        FROM `tabPurchase Invoice`
        WHERE docstatus = 1
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(posting_date, '%Y-%m')
        ORDER BY month;
        """,
    ),
    (
        "monthly_sales_last_12m",
        """
        SELECT
            DATE_FORMAT(posting_date, '%Y-%m') AS month,
            ROUND(SUM(base_grand_total), 2) AS sales_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(posting_date, '%Y-%m')
        ORDER BY month;
        """,
    ),
]


def run_query(cursor: Any, title: str, sql: str) -> Iterable[dict[str, Any]]:
    cursor.execute(sql)
    rows = cursor.fetchall()

    print(f"\n=== {title} ===")
    if not rows:
        print("No rows returned")
        return rows

    for row in rows:
        print(row)
    return rows


def main() -> int:
    cfg = DBConfig.from_env()

    conn = pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        read_timeout=30,
        write_timeout=30,
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok;")
            print("DB connection check:", cursor.fetchone())

            for title, sql in QUERIES:
                run_query(cursor, title, sql)

        print("\nDay-1 baseline complete: DB + 4 KPI queries validated.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
