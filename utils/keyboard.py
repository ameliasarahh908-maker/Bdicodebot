from aiogram.types import InlineKeyboardButton

def build_page_buttons(code: str, page: int, total: int):

    row = []

    # PREV
    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"page:{code}:{page-1}"
            )
        )

    # NOMOR HALAMAN
    start = max(1, page - 2)
    end = min(total, page + 2)

    for i in range(start, end + 1):

        emoji = "🔲" if i == page else (
            "▫️" if i < page else "▪️"
        )

        row.append(
            InlineKeyboardButton(
                text=f"{i}{emoji}",
                callback_data=f"page:{code}:{i}"
            )
        )

    # NEXT / END
    if page < total:
        row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"page:{code}:{page+1}"
            )
        )
    else:
        row.append(
            InlineKeyboardButton(
                text="✅ END",
                callback_data="end_page"
            )
        )

    return row
