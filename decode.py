# Скрипт для фикса битой кодировки + удаления дубликатов
# В моём случае в мире было около 2 тыс файлов, которые были ужаты до 130.
# Запуск не требует сторонник либ
# Хоть он и работает с другой папкой - но бэкапы святое

import os
import json
import hashlib
from pathlib import Path

def is_mixed_encoding(text):
    """Определяет, есть ли в тексте смешанная кодировка"""
    # Проверяем наличие типичных символов cp1251 в UTF-8 тексте
    cp1251_indicators = ['Ñ', 'Ð', 'Î', 'Â', 'à', 'á', 'â', 'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é', 'ê', 'ë']
    utf8_cyrillic = any('А' <= c <= 'я' for c in text)
    cp1251_chars = any(indicator in text for indicator in cp1251_indicators)
    
    return utf8_cyrillic and cp1251_chars

def fix_mixed_encoding(text):
    """Исправляет смешанную кодировку в тексте"""
    if not is_mixed_encoding(text):
        return text
    
    try:
        # Разбиваем текст на части и обрабатываем каждую часть отдельно
        result = []
        current_part = []
        current_encoding = None
        
        for char in text:
            # Определяем кодировку текущего символа
            char_encoding = 'utf8' if ('А' <= char <= 'я' or char in 'Ёё') else 'cp1251'
            
            if current_encoding is None:
                current_encoding = char_encoding
                current_part.append(char)
            elif current_encoding == char_encoding:
                current_part.append(char)
            else:
                # Смена кодировки - обрабатываем накопленную часть
                part_text = ''.join(current_part)
                if current_encoding == 'cp1251':
                    try:
                        part_text = part_text.encode('latin1').decode('cp1251')
                    except:
                        pass
                result.append(part_text)
                
                # Начинаем новую часть
                current_part = [char]
                current_encoding = char_encoding
        
        # Обрабатываем последнюю часть
        if current_part:
            part_text = ''.join(current_part)
            if current_encoding == 'cp1251':
                try:
                    part_text = part_text.encode('latin1').decode('cp1251')
                except:
                    pass
            result.append(part_text)
        
        return ''.join(result)
        
    except Exception as e:
        print(f"Ошибка при исправлении смешанной кодировки: {e}")
        return text

def fix_encoding(text):
    """Исправляет кодировку текста (назовём u-mode)"""
    # Сначала проверяем на смешанную кодировку
    if is_mixed_encoding(text):
        return fix_mixed_encoding(text)
    
    # Пробуем стандартное исправление cp1251
    try:
        return text.encode('latin1').decode('cp1251')
    except:
        return text

def fix_filename(filename):
    """Исправляет кодировку в имени файла"""
    try:
        # Пробуем исправить кодировку имени файла
        name, ext = os.path.splitext(filename)
        fixed_name = fix_encoding(name)
        return fixed_name + ext
    except:
        return filename

def calculate_book_hash(book_data):
    """Вычисляет хеш книги для сравнения содержимого"""
    content_parts = []
    
    if 'title' in book_data:
        content_parts.append(book_data['title'])
    if 'author' in book_data:
        content_parts.append(book_data['author'])
    if 'pages' in book_data:
        content_parts.extend(book_data['pages'])
    
    content_string = '|'.join(content_parts)
    return hashlib.md5(content_string.encode('utf-8')).hexdigest()

def process_json_file(input_path, output_dir):
    """Обрабатывает один JSON файл и возвращает информацию о книге"""
    try:
        # Читаем исходный файл
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим JSON
        data = json.loads(content)
        
        # Рекурсивно исправляем кодировку
        def fix_encoding_recursive(obj):
            if isinstance(obj, dict):
                return {key: fix_encoding_recursive(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [fix_encoding_recursive(item) for item in obj]
            elif isinstance(obj, str):
                fixed_text = fix_encoding(obj)
                # Логируем исправления для отладки
                if fixed_text != obj and is_mixed_encoding(obj):
                    print(f"  Исправлена смешанная кодировка в тексте длиной {len(obj)} символов")
                return fixed_text
            else:
                return obj
        
        fixed_data = fix_encoding_recursive(data)
        
        # Исправляем имя файла на основе исправленного title
        original_filename = input_path.name
        if 'title' in fixed_data and fixed_data['title']:
            # Создаем новое имя файла на основе заголовка
            title = fixed_data['title']
            # Заменяем недопустимые символы в имени файла
            safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
            safe_title = safe_title.strip().replace(' ', '_')[:50]  # Ограничиваем длину
            new_filename = f"book_{safe_title}.json"
        else:
            # Если заголовка нет, исправляем кодировку исходного имени
            new_filename = fix_filename(original_filename)
        
        # Создаем полный путь для выходного файла
        output_path = Path(output_dir) / new_filename
        
        # Если файл с таким именем уже существует, добавляем номер
        counter = 1
        original_output_path = output_path
        while output_path.exists():
            name, ext = os.path.splitext(original_output_path.name)
            output_path = Path(output_dir) / f"{name}_{counter:02d}{ext}"
            counter += 1
        
        # Сохраняем исправленный файл
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, ensure_ascii=False, indent=2, separators=(',', ': '))
        
        # Возвращаем информацию о книге для дедупликации
        book_info = {
            'original_path': input_path,
            'new_path': output_path,
            'data': fixed_data,
            'hash': calculate_book_hash(fixed_data),
            'title': fixed_data.get('title', ''),
            'author': fixed_data.get('author', '')
        }
        
        print(f"Исправлен: {original_filename} -> {output_path.name}")
        return book_info
        
    except Exception as e:
        print(f"Ошибка в {input_path.name}: {e}")
        return None

def remove_duplicate_books(books_info):
    """Удаляет дубликаты книг и возвращает список уникальных"""
    seen_hashes = set()
    unique_books = []
    duplicates = []
    
    for book in books_info:
        if book and book['hash'] not in seen_hashes:
            seen_hashes.add(book['hash'])
            unique_books.append(book)
        elif book:
            duplicates.append(book)
    
    return unique_books, duplicates

def analyze_encoding_problems(input_dir):
    """Анализирует файлы на наличие проблем с кодировкой"""
    print("Анализ проблем с кодировкой...")
    json_files = list(Path(input_dir).glob("*.json"))
    
    mixed_encoding_count = 0
    total_files = len(json_files)
    
    for file_path in json_files[:5]:  # Проверяем первые 5 файлов для примера
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            data = json.loads(content)
            
            # Проверяем поля на смешанную кодировку
            def check_mixed(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        check_mixed(value, f"{path}.{key}")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_mixed(item, f"{path}[{i}]")
                elif isinstance(obj, str) and is_mixed_encoding(obj):
                    nonlocal mixed_encoding_count
                    mixed_encoding_count += 1
                    print(f" Найден файл со смешанной кодировкой: {file_path.name}")
                    return
            
            check_mixed(data)
            
        except Exception as e:
            continue
    
    if mixed_encoding_count > 0:
        print(f"Найдено файлов со смешанной кодировкой: {mixed_encoding_count}")
    else:
        print("Файлов со смешанной кодировкой не обнаружено")

def main():
    input_dir = "exported_books/books_json"
    output_dir = "exported_books/books_fixed"
    
    if not os.path.exists(input_dir):
        print(f"Исходная директория {input_dir} не найдена!")
        return
    
    # Анализируем проблемы с кодировкой
    analyze_encoding_problems(input_dir)
    
    # Создаем выходную директорию
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Находим все JSON файлы
    json_files = list(Path(input_dir).glob("*.json"))
    
    if not json_files:
        print("JSON файлы не найдены!")
        return
    
    print(f"\nНайдено {len(json_files)} файлов для обработки...")
    print(f"Исходная папка: {input_dir}")
    print(f"Выходная папка: {output_dir}")
    print("-" * 50)
    
    # Обрабатываем все файлы и собираем информацию
    all_books_info = []
    for input_path in json_files:
        book_info = process_json_file(input_path, output_dir)
        all_books_info.append(book_info)
    
    # Удаляем None (файлы с ошибками)
    successful_books = [book for book in all_books_info if book is not None]
    
    # Удаляем дубликаты
    unique_books, duplicates = remove_duplicate_books(successful_books)
    
    # Удаляем файлы-дубликаты
    for duplicate in duplicates:
        try:
            os.remove(duplicate['new_path'])
            print(f"Удален дубликат: {duplicate['new_path'].name}")
        except Exception as e:
            print(f"Не удалось удалить дубликат {duplicate['new_path'].name}: {e}")
    
    print("-" * 50)
    print("СТАТИСТИКА:")
    print(f"Всего обработано файлов: {len(json_files)}")
    print(f"Успешно обработано: {len(successful_books)}")
    print(f"Найдено дубликатов: {len(duplicates)}")
    print(f"Уникальных книг: {len(unique_books)}")
    print(f"Ошибок обработки: {len(all_books_info) - len(successful_books)}")
    print(f"Исправленные файлы сохранены в: {output_dir}")
    
    # Выводим информацию о дубликатах
    if duplicates:
        print("\nУДАЛЕННЫЕ ДУБЛИКАТЫ:")
        for dup in duplicates:
            print(f"  - {dup['new_path'].name} (автор: {dup['author']})")

if __name__ == "__main__":
    main()