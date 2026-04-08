from __future__ import annotations

import asyncpg

from app.core.config import get_settings


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self._settings = get_settings()

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._settings.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
                statement_cache_size=0,
            )

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool has not been initialized.")
        return self._pool


database = Database()
