import asyncio
import logging
import asyncpg

from config import DATABASE_URL

_pool = None
_lock = asyncio.Lock()


# ========================
# CONNECTION
# ========================
async def get_pool():
    global _pool

    if _pool is not None:
        return _pool

    async with _lock:
        if _pool is not None:
            return _pool

        while True:
            try:
                logging.info("🔌 Connecting to PostgreSQL...")

                _pool = await asyncpg.create_pool(
                    dsn=DATABASE_URL,
                    min_size=1,
                    max_size=10,
                    command_timeout=60,
                    max_inactive_connection_lifetime=300,
                    statement_cache_size=0  # 🔥 WAJIB buat Supabase
                )

                logging.info("✅ PostgreSQL connected")
                break

            except Exception:
                logging.exception(
                    "❌ Failed connecting to DB. Retrying in 3 seconds..."
                )
                await asyncio.sleep(3)

    return _pool


async def close_db():
    global _pool

    if _pool:
        await _pool.close()
        _pool = None
        logging.info("🔌 Database closed")


# ========================
# INTERNAL SAFE EXECUTOR
# ========================
async def _run(method, query, args, retry):
    global _pool

    for attempt in range(retry + 1):
        try:
            pool = await get_pool()

            async with pool.acquire() as conn:
                return await method(conn, query, *args)

        except asyncpg.PostgresError:
            # ❗ Query error (SQL salah, kolom gak ada, dll)
            raise

        except Exception:
            logging.exception("⚠️ DB connection error")

            # reset pool kalau rusak
            if _pool:
                await _pool.close()
                _pool = None

            if attempt >= retry:
                raise

            await asyncio.sleep(1)


# ========================
# QUERY HELPERS
# ========================
async def execute(query, *args, retry=1):
    return await _run(
        lambda conn, q, *a: conn.execute(q, *a),
        query,
        args,
        retry
    )


async def fetch(query, *args, retry=1):
    return await _run(
        lambda conn, q, *a: conn.fetch(q, *a),
        query,
        args,
        retry
    )


async def fetchrow(query, *args, retry=1):
    return await _run(
        lambda conn, q, *a: conn.fetchrow(q, *a),
        query,
        args,
        retry
    )


async def fetchval(query, *args, retry=1):
    return await _run(
        lambda conn, q, *a: conn.fetchval(q, *a),
        query,
        args,
        retry
    )


# ========================
# TRANSACTION
# ========================
async def transaction(queries: list):
    global _pool

    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            results = []

            for q in queries:
                query = q[0]
                args = q[1:]

                results.append(
                    await conn.execute(query, *args)
                )

            return results
