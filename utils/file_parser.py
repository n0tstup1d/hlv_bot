"""
Парсер файлов Excel, TXT, JSON для вывода данных в сообщение.
"""
import json
import io
from typing import Optional


def parse_txt(content: bytes, encoding: str = "utf-8") -> str:
    """Парсинг TXT-файла."""
    try:
        return content.decode(encoding)
    except UnicodeDecodeError:
        return content.decode("utf-8", errors="replace")


def parse_json(content: bytes, encoding: str = "utf-8") -> str:
    """Парсинг JSON-файла с форматированием."""
    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="replace")
    
    data = json.loads(text)
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_excel(content: bytes) -> str:
    """
    Парсинг Excel-файла (.xlsx).
    - Первая строка считается заголовком.
    - Последующие строки выводятся как 'заголовок: значение'.
    - Если заголовков нет (только одна строка) — выводится как список значений.
    """
    try:
        import openpyxl
    except ImportError:
        return "❌ Для работы с Excel установите: pip install openpyxl"

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    result_lines = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        result_lines.append(f"📋 Лист: {sheet_name}")
        result_lines.append("-" * 40)

        # Получаем итератор строк
        row_iter = sheet.iter_rows(values_only=True)

        # Читаем первую строку (потенциальные заголовки)
        try:
            headers_row = next(row_iter)
        except StopIteration:
            # Лист пуст
            result_lines.append("(пустой лист)")
            result_lines.append("")
            continue

        # Преобразуем заголовки в строки, заменяем None на пустую строку
        headers = [str(cell) if cell is not None else "" for cell in headers_row]

        # Убираем конечные пустые заголовки, чтобы не плодить колонки с пустыми именами
        while headers and headers[-1] == "":
            headers.pop()

        # Если нет заголовков (все пустые) — выводим просто значения
        if not any(headers):
            # Первая строка не является заголовком — выводим её как есть
            non_empty = any(str(c) if c is not None else "" for c in headers_row)
            if non_empty:
                for val in headers_row:
                    result_lines.append(str(val) if val is not None else "")
            # И продолжаем выводить остальные строки в старом формате
            for row in row_iter:
                row_values = [str(cell) if cell is not None else "" for cell in row]
                if any(row_values):
                    for val in row_values:
                        result_lines.append(val)
            result_lines.append("")
            continue

        # --- Есть заголовки ---
        record_num = 0
        # Выводим строки данных
        for row in row_iter:
            row_values = [cell if cell is not None else "" for cell in row]
            if not any(row_values):
                continue  # полностью пустая строка
            record_num += 1
            # Если записей больше одной — разделяем пустой строкой
            if record_num > 1:
                result_lines.append("")
            # Добавляем номер записи (если записей >1)
            if sheet.max_row > 2:  # грубая оценка, можно использовать record_num
                result_lines.append(f"#{record_num}")

            # Для каждой пары (заголовок, значение) в пределах имеющихся
            for idx, header in enumerate(headers):
                if idx >= len(row_values):
                    value = ""
                else:
                    value = row_values[idx]
                # Пропускаем, если заголовок пустой
                if header == "":
                    continue
                result_lines.append(f"{header}: {value}")

        # Если не было ни одной записи — выводим только заголовки как список
        if record_num == 0:
            for header in headers:
                result_lines.append(header)

        result_lines.append("")  # разделитель между листами

    wb.close()
    return "\n".join(result_lines).strip() or "Файл пуст"


def parse_file(content: bytes, filename: str) -> tuple[bool, str]:
    """
    Парсит файл по расширению.
    Возвращает (успех, текст результата или сообщение об ошибке).
    """
    ext = (filename or "").lower().split(".")[-1]
    
    if ext == "txt":
        return True, parse_txt(content)
    elif ext == "json":
        try:
            return True, parse_json(content)
        except json.JSONDecodeError as e:
            return False, f"❌ Ошибка JSON: {e}"
    elif ext == "xlsx":
        try:
            return True, parse_excel(content)
        except Exception as e:
            return False, f"❌ Ошибка чтения Excel: {e}"
    elif ext == "xls":
        return False, "❌ Старый формат .xls не поддерживается. Сохраните файл как .xlsx"
    else:
        return False, f"❌ Неподдерживаемый формат: .{ext}. Используйте .txt, .json или .xlsx"
