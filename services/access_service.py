async def check_access(pool, user_id, file):

    # FREE FILE
    if not file["is_paid"]:
        return True

    # OWNER
    if user_id == file["owner_id"]:
        return True

    # VIP
    vip = await pool.fetchval(
        """
        SELECT 1
        FROM users
        WHERE telegram_id=$1
        AND vip=TRUE
        AND vip_until > NOW()
        """,
        user_id
    )

    if vip:
        return True

    # PURCHASED
    bought = await pool.fetchval(
        """
        SELECT 1
        FROM file_purchases
        WHERE user_id=$1
        AND file_code=$2
        AND status='paid'
        LIMIT 1
        """,
        user_id,
        file["code"]
    )

    return bool(bought)
