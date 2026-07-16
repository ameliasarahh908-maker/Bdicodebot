from datetime import datetime, timedelta
import pytz


async def check_referral_reward(pool, user_id: int):

    data = await pool.fetchrow(
        """
        SELECT referral_count, vip, vvip, vip_until, vvip_until
        FROM users
        WHERE telegram_id=$1
        """,
        user_id
    )

    if not data:
        return None

    total = data["referral_count"] or 0

    wib = pytz.timezone("Asia/Jakarta")
    now = datetime.now(wib)

    reward_text = None

    # =========================
    # 10 REF → VIP 1 HARI
    # =========================
    if total == 10:
        vip_until = now + timedelta(days=1)

        await pool.execute(
            """
            UPDATE users
            SET vip=TRUE, vip_until=$1,
                paid_quota = COALESCE(paid_quota,0) + 1
            WHERE telegram_id=$2
            """,
            vip_until,
            user_id
        )

        reward_text = "🎉 VIP 1 hari + 1 quota"

    # =========================
    # 20 REF → VIP 2 HARI
    # =========================
    elif total == 20:
        vip_until = now + timedelta(days=2)

        await pool.execute(
            """
            UPDATE users
            SET vip=TRUE, vip_until=$1,
                paid_quota = COALESCE(paid_quota,0) + 3
            WHERE telegram_id=$2
            """,
            vip_until,
            user_id
        )

        reward_text = "🔥 VIP 2 hari + 3 quota"

    # =========================
    # 50 REF → VVIP 7 HARI
    # =========================
    elif total == 50:
        vvip_until = now + timedelta(days=7)

        await pool.execute(
            """
            UPDATE users
            SET vvip=TRUE, vvip_until=$1
            WHERE telegram_id=$2
            """,
            vvip_until,
            user_id
        )

        reward_text = "👑 VVIP 7 hari"

    return reward_text
