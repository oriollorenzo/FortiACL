import aiosqlite
from pathlib import Path
from datetime import datetime, timezone

from app.core.config import settings


DB_PATH = Path(settings.DB_PATH)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_auth_tables() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS frozen_ports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT NOT NULL,
                port_name TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(serial_number, port_name)
            )
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS acl_counter_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                campus TEXT,
                serial TEXT,
                switch_name TEXT,
                acl_name TEXT,
                counter_value INTEGER NOT NULL DEFAULT 0,
                severity TEXT NOT NULL DEFAULT 'info'
            )
            """
        )

        await db.commit()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        await cursor.close()
        return int(row[0] if row else 0)


async def count_active_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        row = await cursor.fetchone()
        await cursor.close()
        return int(row[0] if row else 0)


async def create_user(username: str, password_hash: str, is_active: bool = True) -> int:
    now = _utc_now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                1 if is_active else 0,
                now,
                now,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_user_by_username(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                is_active,
                created_at,
                updated_at,
                last_login_at
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def get_user_by_id(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                is_active,
                created_at,
                updated_at,
                last_login_at
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def list_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                id,
                username,
                is_active,
                created_at,
                updated_at,
                last_login_at
            FROM users
            ORDER BY username COLLATE NOCASE
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]


async def update_user_password(user_id: int, password_hash: str) -> None:
    now = _utc_now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET
                password_hash = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (password_hash, now, user_id),
        )
        await db.commit()


async def set_user_active(user_id: int, is_active: bool) -> None:
    now = _utc_now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET
                is_active = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (1 if is_active else 0, now, user_id),
        )
        await db.commit()


async def touch_last_login(user_id: int) -> None:
    now = _utc_now_iso()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE users
            SET
                last_login_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, user_id),
        )
        await db.commit()


async def create_session(
    user_id: int,
    session_token: str,
    expires_at: str | None = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO sessions (
                user_id,
                session_token,
                created_at,
                expires_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                session_token,
                _utc_now_iso(),
                expires_at,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def get_session_with_user_by_token(session_token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                s.id AS session_id,
                s.user_id,
                s.session_token,
                s.created_at AS session_created_at,
                s.expires_at,
                u.id AS user_id,
                u.username,
                u.is_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.session_token = ?
            LIMIT 1
            """,
            (session_token,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        return row


async def delete_session_by_token(session_token: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sessions WHERE session_token = ?",
            (session_token,),
        )
        await db.commit()


async def delete_sessions_by_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def get_all_frozen_by_serial(serial: str) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT port_name FROM frozen_ports WHERE serial_number = ?",
            (serial,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [int(row[0]) for row in rows if str(row[0]).isdigit()]


async def freeze_port_db(serial: str, port: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO frozen_ports (
                    serial_number,
                    port_name,
                    reason
                ) VALUES (?, ?, ?)
                """,
                (serial, str(port), "Congelat des de la Web"),
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error DB freeze_port_db: {e}")
        return False


async def unfreeze_port_db(serial: str, port: int) -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM frozen_ports WHERE serial_number = ? AND port_name = ?",
                (serial, str(port)),
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error DB unfreeze_port_db: {e}")
        return False


async def insert_acl_counter_sample(
    campus: str,
    serial: str,
    switch_name: str,
    acl_name: str,
    counter_value: int,
    severity: str,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO acl_counter_samples (
                created_at,
                campus,
                serial,
                switch_name,
                acl_name,
                counter_value,
                severity
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utc_now_iso(),
                campus,
                serial,
                switch_name,
                acl_name,
                int(counter_value),
                severity,
            ),
        )
        await db.commit()


def _build_acl_samples_where(
    q: str = "",
    campus: str = "",
    severity: str = "",
) -> tuple[str, list]:
    where = []
    params = []

    if q:
        like = f"%{q}%"
        where.append(
            "(campus LIKE ? OR switch_name LIKE ? OR serial LIKE ? OR acl_name LIKE ?)"
        )
        params.extend([like, like, like, like])

    if campus:
        where.append("campus = ?")
        params.append(campus)

    if severity:
        where.append("severity = ?")
        params.append(severity)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    return where_sql, params


async def list_acl_counter_samples_paginated(
    page: int = 1,
    per_page: int = 100,
    q: str = "",
    campus: str = "",
    severity: str = "",
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> dict:
    where_sql, params = _build_acl_samples_where(
        q=q,
        campus=campus,
        severity=severity,
    )
    offset = (page - 1) * per_page

    allowed_sort = {
        "created_at": "created_at",
        "campus": "campus",
        "switch_name": "switch_name",
        "serial": "serial",
        "acl_name": "acl_name",
        "counter_value": "counter_value",
        "severity": "severity",
    }

    order_col = allowed_sort.get(sort_by, "created_at")
    order_dir = "ASC" if (sort_dir or "").lower() == "asc" else "DESC"

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            f"SELECT COUNT(*) AS total FROM acl_counter_samples {where_sql}",
            params,
        )
        total_row = await cursor.fetchone()
        await cursor.close()
        total = int(total_row["total"] if total_row else 0)

        cursor = await db.execute(
            f"""
            SELECT
                id,
                created_at,
                campus,
                serial,
                switch_name,
                acl_name,
                counter_value,
                severity
            FROM acl_counter_samples
            {where_sql}
            ORDER BY {order_col} {order_dir}, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, int(per_page), int(offset)],
        )
        rows = await cursor.fetchall()
        await cursor.close()

    pages = max(1, (total + per_page - 1) // per_page)

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "sort_by": sort_by,
        "sort_dir": order_dir.lower(),
    }

async def list_acl_counter_sample_campuses() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT DISTINCT campus
            FROM acl_counter_samples
            WHERE campus IS NOT NULL AND TRIM(campus) <> ''
            ORDER BY campus COLLATE NOCASE
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()

    return [row[0] for row in rows if row[0]]


async def delete_all_acl_counter_samples() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM acl_counter_samples")
        await db.commit()
        return cursor.rowcount


async def delete_filtered_acl_counter_samples(
    q: str = "",
    campus: str = "",
    severity: str = "",
) -> int:
    where_sql, params = _build_acl_samples_where(
        q=q,
        campus=campus,
        severity=severity,
    )

    if not where_sql:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            f"DELETE FROM acl_counter_samples {where_sql}",
            params,
        )
        await db.commit()
        return cursor.rowcount
