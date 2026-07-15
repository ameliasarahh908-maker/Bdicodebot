import json
from config import STORAGE_CHANNEL_ID

async def send_all(bot, chat_id, code, file):
    media = file["media"]

    if isinstance(media, str):
        try:
            media = json.loads(media)
        except:
            return False

    if not media:
        return False

    share_media = file["share_media"]
    if share_media is None:
        share_media = True

    protect = not share_media
    total = len(media)

    status = await bot.send_message(
        chat_id,
        f"📤 Mengirim {total} media..."
    )

    success = 0

    for index, item in enumerate(media, start=1):
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=item["message_id"],
                protect_content=protect
            )

            success += 1

            if index % 10 == 0:
                try:
                    await status.edit_text(
                        f"📤 Mengirim media...\n\n{success}/{total}"
                    )
                except:
                    pass

        except Exception as e:
            print("SEND ALL ERROR:", e)

    try:
        await status.edit_text(
            f"✅ {success} Media Terkirim"
        )
    except:
        pass

    return True
