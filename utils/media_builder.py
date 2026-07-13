from aiogram.types import (
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument
)

def build_album(chunk, caption):

    album = []

    for index, item in enumerate(chunk):

        if not isinstance(item, dict):
            continue

        fid = item.get("file_id")
        ftype = (item.get("type") or "document").lower()

        if not fid:
            continue

        cap = caption if index == 0 else None

        if ftype in ("photo", "image"):
            album.append(InputMediaPhoto(media=fid, caption=cap))

        elif ftype == "video":
            album.append(InputMediaVideo(media=fid, caption=cap))

        else:
            album.append(InputMediaDocument(media=fid, caption=cap))

    return album
