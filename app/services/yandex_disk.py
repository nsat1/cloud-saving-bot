import yadisk

from app.config import YANDEX_TOKEN


yadisk_instance = yadisk.YaDisk(token=YANDEX_TOKEN)

def upload_photo(file_stream, file_id):
    try:
        yadisk_instance.upload(file_stream, f"/bot_uploads/{file_id}", overwrite=True)
        return True

    except Exception as e:
        print(f"Ошибка загрузки. {e}")
        return False
