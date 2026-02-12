import mimetypes
import os

async def get_file_type_from_path(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    
    # Определяем MIME-тип
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if mime_type:
        if mime_type.startswith('image/'):
            return 'photo'
        elif mime_type.startswith('video/'):
            return 'video'
        else:
            return 'photo'
    else:
        # Если не определили, пробуем по расширению
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.mov', '.avi']:
            return 'video'
        elif ext in ['.jpg', '.png', '.jpeg']:
            return 'photo'
    
    return 'photo'