#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
سامانه GHIAS
لایه اتصال به پایگاه داده
=============================================================================

این فایل مسئول موارد زیر است:
    - ساخت اتصال به فایل پایگاه داده SQLite
    - اجرای فایل create_database.sql برای ساخت جداول (در صورت نبودن)
    - فراهم کردن یک کلاس Database ساده برای استفاده در بقیه برنامه

هیچ بخش دیگری از برنامه نباید مستقیماً sqlite3 را وارد کند؛ همه باید از
طریق کلاس Database این فایل با پایگاه داده کار کنند.
=============================================================================
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


# مسیر پوشه‌ی database (همان پوشه‌ای که این فایل در آن قرار دارد)
BASE_DIR: Path = Path(__file__).resolve().parent

# مسیر فایل پایگاه داده اصلی برنامه
DB_PATH: Path = BASE_DIR / "GHIAS_SECURITY_ASSESSMENT.db"

# مسیر فایل اسکیمای پایگاه داده
SCHEMA_PATH: Path = BASE_DIR / "create_database.sql"


class Database:
    """
    کلاس مدیریت اتصال به پایگاه داده SQLite.

    استفاده:
        db = Database()
        db.initialize()          # ساخت جداول در صورت نبودن
        rows = db.query("SELECT * FROM categories")
    """

    def __init__(self, db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self._connection: sqlite3.Connection | None = None

    # ------------------------------------------------------------ اتصال
    def connect(self) -> sqlite3.Connection:
        """
        برقراری اتصال به پایگاه داده (در صورت نبودن اتصال قبلی).
        Row factory طوری تنظیم شده که هر ردیف مثل دیکشنری قابل دسترسی باشد.
        """
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON;")
        return self._connection

    def close(self) -> None:
        """بستن اتصال جاری، در صورت باز بودن."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    # ------------------------------------------------------------ ساخت جداول
    def initialize(self) -> None:
        """
        آماده‌سازی کامل پایگاه داده، شامل دو مرحله:
            ۱) اگر پایگاه داده نسخه قدیمی‌تری داشته باشد (مثلاً جدول hospitals
               به‌جای facilities، یا فاقد لایه حوزه کلان ارزیابی)، خودکار و
               بی‌خطر به آخرین نسخه ساختار مهاجرت داده می‌شود.
            ۲) اجرای فایل create_database.sql برای ساخت جداولی که هنوز
               وجود ندارند.

        این متد کاملاً بی‌خطر است و روی هر پایگاه داده‌ای (تازه، قدیمی،
        یا از قبل به‌روز) می‌تواند اجرا شود؛ در هر کامپیوتری که برنامه اجرا
        شود، پایگاه داده محلی همان کامپیوتر خودش را به‌روزرسانی می‌کند.
        """
        connection = self.connect()
        self._migrate_legacy_schema(connection)

        if not self.schema_path.exists():
            raise FileNotFoundError(
                f"فایل اسکیمای پایگاه داده پیدا نشد:\n{self.schema_path}"
            )

        sql_script = self.schema_path.read_text(encoding="utf-8")
        connection.executescript(sql_script)
        connection.commit()

    # ------------------------------------------------------------ مهاجرت خودکار
    def _table_exists(self, connection: sqlite3.Connection, table_name: str) -> bool:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _column_exists(
        self, connection: sqlite3.Connection, table_name: str, column_name: str
    ) -> bool:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return any(row[1] == column_name for row in rows)

    def _row_count(self, connection: sqlite3.Connection, table_name: str) -> int:
        return connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    def _migrate_legacy_schema(self, connection: sqlite3.Connection) -> None:
        """
        اجرای خودکار تمام مهاجرت‌های لازم برای رساندن یک پایگاه داده قدیمی
        به آخرین نسخه ساختار. هر مرحله مستقل بررسی می‌شود و فقط در صورت
        نیاز واقعی اجرا می‌شود.
        """
        connection.execute("PRAGMA foreign_keys = OFF;")
        self._migrate_v2_facility_types(connection)
        self._migrate_v3_domains(connection)
        connection.execute("PRAGMA foreign_keys = ON;")

    def _migrate_v2_facility_types(self, connection: sqlite3.Connection) -> None:
        """مهاجرت نسخه دوم: تبدیل جدول hospitals به مدل عمومی facilities."""
        hospitals_exists = self._table_exists(connection, "hospitals")
        facilities_exists = self._table_exists(connection, "facilities")

        if not hospitals_exists:
            return  # یا از قبل مهاجرت شده، یا پایگاه داده کاملاً تازه است

        # پاک‌سازی باقیمانده احتمالی یک تلاش قبلی نافرجام
        if facilities_exists:
            if self._row_count(connection, "facilities") == 0:
                connection.execute("DROP TABLE facilities")
            else:
                # حالت نامنتظره: هر دو جدول داده واقعی دارند؛ برای ایمنی دست نمی‌زنیم
                return

        if self._table_exists(connection, "facility_types"):
            if self._row_count(connection, "facility_types") == 0:
                connection.execute("DROP TABLE facility_types")

        connection.execute(
            """
            CREATE TABLE facility_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_key TEXT UNIQUE NOT NULL,
                type_name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "INSERT INTO facility_types (type_key, type_name) VALUES ('hospital', 'بیمارستان')"
        )
        connection.commit()

        hospital_type_id = connection.execute(
            "SELECT id FROM facility_types WHERE type_key = 'hospital'"
        ).fetchone()[0]

        connection.execute("ALTER TABLE hospitals RENAME TO facilities")
        if not self._column_exists(connection, "facilities", "facility_name"):
            connection.execute("ALTER TABLE facilities RENAME COLUMN hospital_name TO facility_name")
        if not self._column_exists(connection, "facilities", "facility_code"):
            connection.execute("ALTER TABLE facilities RENAME COLUMN hospital_code TO facility_code")
        if not self._column_exists(connection, "facilities", "facility_type_id"):
            connection.execute(
                "ALTER TABLE facilities ADD COLUMN facility_type_id INTEGER REFERENCES facility_types(id)"
            )
        connection.execute(
            "UPDATE facilities SET facility_type_id = ? WHERE facility_type_id IS NULL",
            (hospital_type_id,),
        )

        if not self._column_exists(connection, "categories", "facility_type_id"):
            connection.execute(
                "ALTER TABLE categories ADD COLUMN facility_type_id INTEGER REFERENCES facility_types(id)"
            )
        connection.execute(
            "UPDATE categories SET facility_type_id = ? WHERE facility_type_id IS NULL",
            (hospital_type_id,),
        )

        if not self._column_exists(connection, "visits", "facility_id"):
            connection.execute("ALTER TABLE visits RENAME COLUMN hospital_id TO facility_id")

        connection.commit()

    def _migrate_v3_domains(self, connection: sqlite3.Connection) -> None:
        """مهاجرت نسخه سوم: افزودن لایه حوزه کلان ارزیابی."""
        if not self._table_exists(connection, "facilities"):
            return  # هنوز مهاجرت نسخه دوم انجام نشده؛ این مرحله باید بعداً اجرا شود

        already_migrated = (
            self._table_exists(connection, "assessment_domains")
            and self._column_exists(connection, "categories", "domain_id")
            and self._column_exists(connection, "visits", "domain_id")
        )
        if already_migrated:
            return

        if self._table_exists(connection, "assessment_domains"):
            if self._row_count(connection, "assessment_domains") == 0:
                connection.execute("DROP TABLE assessment_domains")

        if not self._table_exists(connection, "assessment_domains"):
            connection.execute(
                """
                CREATE TABLE assessment_domains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_key TEXT UNIQUE NOT NULL,
                    domain_name TEXT NOT NULL,
                    description TEXT,
                    display_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        connection.execute(
            "INSERT OR IGNORE INTO assessment_domains (domain_key, domain_name, display_order) "
            "VALUES ('physical_security', 'حفاظت فیزیکی', 1)"
        )
        connection.commit()

        physical_security_domain_id = connection.execute(
            "SELECT id FROM assessment_domains WHERE domain_key = 'physical_security'"
        ).fetchone()[0]

        if not self._column_exists(connection, "categories", "domain_id"):
            connection.execute(
                "ALTER TABLE categories ADD COLUMN domain_id INTEGER REFERENCES assessment_domains(id)"
            )
        connection.execute(
            "UPDATE categories SET domain_id = ? WHERE domain_id IS NULL",
            (physical_security_domain_id,),
        )

        if not self._column_exists(connection, "visits", "domain_id"):
            connection.execute(
                "ALTER TABLE visits ADD COLUMN domain_id INTEGER REFERENCES assessment_domains(id)"
            )
        connection.execute(
            "UPDATE visits SET domain_id = ? WHERE domain_id IS NULL",
            (physical_security_domain_id,),
        )

        connection.commit()

    # ------------------------------------------------------------ عملیات پایه
    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        """اجرای یک پرس‌وجوی SELECT و بازگرداندن تمام ردیف‌ها."""
        connection = self.connect()
        cursor = connection.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        """اجرای یک پرس‌وجوی SELECT و بازگرداندن فقط اولین ردیف."""
        connection = self.connect()
        cursor = connection.execute(sql, params)
        return cursor.fetchone()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """
        اجرای یک دستور INSERT/UPDATE/DELETE.
        شناسه ردیف تازه درج‌شده (lastrowid) بازگردانده می‌شود.
        """
        connection = self.connect()
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.lastrowid

    # ------------------------------------------------------------ کمکی برای دیباگ
    def table_names(self) -> list[str]:
        """بازگرداندن نام تمام جداول موجود در پایگاه داده (برای بررسی/دیباگ)."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row["name"] for row in rows]


def get_database() -> Database:
    """
    ساخت و آماده‌سازی یک نمونه از کلاس Database.
    این تابع باید در سراسر برنامه برای دسترسی به پایگاه داده استفاده شود.
    """
    db = Database()
    db.initialize()
    return db


# =============================================================================
# اجرای مستقیم این فایل: ساخت اولیه پایگاه داده و نمایش وضعیت آن
# =============================================================================

if __name__ == "__main__":
    database = get_database()
    tables = database.table_names()

    print("پایگاه داده با موفقیت ساخته/بررسی شد.")
    print(f"مسیر فایل: {database.db_path}")
    print(f"تعداد جداول ساخته‌شده: {len(tables)}")
    for table_name in tables:
        print(f"  - {table_name}")

    database.close()
