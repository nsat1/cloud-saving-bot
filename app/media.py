"""Метаданные вложений и безопасные, воспроизводимые имена файлов."""

import hashlib
import mimetypes
import re
import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath

from aiogram.types import Message

_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_RESERVED_NAME = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$", re.IGNORECASE)


def safe_filename(name: str | None, fallback: str) -> str:
    # Учитываем оба разделителя пути, в том числе для документов из Windows.
    basename = re.split(r"[/\\]", unicodedata.normalize("NFC", name or ""))[-1]
    basename = _INVALID_NAME.sub("_", basename).strip(" .")
    if not basename:
        basename = fallback
    stem, suffix = PurePosixPath(basename).stem, PurePosixPath(basename).suffix
    if _RESERVED_NAME.fullmatch(stem):
        stem = "_" + stem
    suffix = suffix.encode("utf-8")[:32].decode("utf-8", errors="ignore")
    budget = 180 - len(suffix.encode("utf-8"))
    stem = stem.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
    return (stem or "file") + suffix


@dataclass(frozen=True, slots=True)
class Attachment:
    file_id: str
    file_unique_id: str
    file_size: int | None
    filename: str
    label: str

    @classmethod
    def from_message(cls, message: Message) -> "Attachment":
        if message.photo:
            photo = max(
                message.photo, key=lambda item: (item.width * item.height, item.file_size or 0)
            )
            return cls(photo.file_id, photo.file_unique_id, photo.file_size, "photo.jpg", "Фото")
        media = message.document or message.video
        if media is None:
            raise ValueError("Message does not contain supported media")
        label = "Документ" if message.document else "Видео"
        suffix = mimetypes.guess_extension(media.mime_type or "") or (
            ".mp4" if message.video else ".bin"
        )
        filename = safe_filename(media.file_name, "file" + suffix)
        return cls(media.file_id, media.file_unique_id, media.file_size, filename, label)

    def destination_name(self, chat_id: int, message_id: int) -> str:
        # Повторная обработка сообщения использует тот же путь; разные сообщения — разные пути.
        digest = hashlib.sha256(self.file_unique_id.encode()).hexdigest()[:12]
        return f"{chat_id}_{message_id}_{digest}_{self.filename}"
