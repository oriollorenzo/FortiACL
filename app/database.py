import aiosqlite
import os
from app.core.config import settings

DB_PATH = str(settings.DB_PATH)


async def check_port_frozen(serial: str, port_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM frozen_ports WHERE serial_number = ? AND port_name = ?",
            (serial, port_name)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def add_frozen_port(serial: str, port_name: str, reason: str = "Congelat per Oriol"):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO frozen_ports (serial_number, port_name, reason) VALUES (?, ?, ?)",
                (serial, port_name, reason)
            )
            await db.commit()
            return True
        except Exception:
            return False

async def get_all_frozen_by_serial(serial: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT port_name FROM frozen_ports WHERE serial_number = ?", (serial,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def remove_frozen_port(serial: str, port_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM frozen_ports WHERE serial_number = ? AND port_name = ?",
            (serial, port_name)
        )
        await db.commit()
        return cursor.rowcount > 0

