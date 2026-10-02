from dataclasses import replace

import pytest

from app.media import Attachment, safe_filename
from tests.conftest import make_update


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("../../report.pdf", "report.pdf"),
        ("C:\\photos\\image.jpg", "image.jpg"),
        ("bad:name?.txt", "bad_name_.txt"),
        ("NUL.txt", "_NUL.txt"),
        ("..", "file.bin"),
        (None, "file.bin"),
        ("report.pdf. ", "report.pdf"),
        ("тест.pdf", "тест.pdf"),
    ],
)
def test_safe_names(filename, expected):
    assert safe_filename(filename, "file.bin") == expected


def test_long_unicode_filename_keeps_extension_and_fits_disk_limit():
    name = safe_filename("д" * 400 + ".pdf", "file.bin")
    assert name.endswith(".pdf")
    assert len(name.encode()) <= 180


@pytest.mark.parametrize(
    ("kind", "filename", "file_id"),
    [
        ("photo", "photo.jpg", "large-photo-id"),
        ("video", "clip.mp4", "file-id"),
        ("document", "report.pdf", "file-id"),
    ],
)
def test_attachment_metadata(kind, filename, file_id):
    attachment = Attachment.from_message(make_update(kind).message)
    assert attachment.filename == filename
    assert attachment.file_id == file_id


def test_missing_document_name_uses_mime_extension():
    message = make_update().message
    message = message.model_copy(
        update={"document": message.document.model_copy(update={"file_name": None})}
    )
    assert Attachment.from_message(message).filename == "file.pdf"


def test_photo_with_largest_resolution_is_selected_even_if_sizes_are_unordered():
    message = make_update("photo").message
    message = message.model_copy(update={"photo": list(reversed(message.photo))})
    assert Attachment.from_message(message).file_id == "large-photo-id"


def test_photo_size_breaks_ties_between_equal_resolutions():
    message = make_update("photo").message
    large = message.photo[-1]
    message = message.model_copy(
        update={
            "photo": [
                large.model_copy(update={"file_id": "larger-file", "file_size": 100}),
                large.model_copy(update={"file_id": "smaller-file", "file_size": 50}),
            ]
        }
    )
    assert Attachment.from_message(message).file_id == "larger-file"


def test_destination_is_stable_for_replay_and_distinct_between_messages():
    attachment = Attachment.from_message(make_update().message)
    path = attachment.destination_name(1, 10)
    assert path == attachment.destination_name(1, 10)
    assert path != attachment.destination_name(1, 11)
    assert path != attachment.destination_name(2, 10)
    assert path != replace(attachment, file_unique_id="another-file").destination_name(1, 10)
    assert path.endswith("_report.pdf")
