# Зависимость: pip install --upgrade nbtlib

#!/usr/bin/env python3
import gzip, json, logging, os, struct, zlib
from datetime import datetime
from pathlib import Path
import nbtlib
from io import BytesIO

# Папки
WORLD_DIR   = Path(__file__).with_name("HardcoreMap")
OUTPUT_DIR  = Path(__file__).with_name("exported_books")
LOG_FILE    = Path(__file__).with_name("world_fixed.log")

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"),
                              logging.StreamHandler()])
log = logging.getLogger("wf")

# Это важно
books_total = 0
regions_done = 0
chunks_te   = 0

def sanitize(n: str) -> str:
    return n.replace("<", "_").replace(">", "_").replace(":", "_").replace("?", "_")[:100]

def save_book(b: dict, idx: int):
    (OUTPUT_DIR / "books_json").mkdir(parents=True, exist_ok=True)
    fname = OUTPUT_DIR / "books_json" / f"book_{idx:05d}_{sanitize(b['title'])}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=1)

def is_book(item) -> bool:
    if not item: return False
    raw = item.get("id")
    id_ = str(int(raw)) if isinstance(raw, (int, nbtlib.tag.Short, nbtlib.tag.Int)) else str(raw)
    return id_ in ("387", "minecraft:written_book", "written_book") and "tag" in item and "pages" in item["tag"] #todo: writable_book но хз какая там структура

def extract_book(item, loc: str):
    tag = item["tag"]
    pages = [str(p) for p in tag.get("pages", [])]
    return {
        "title": str(tag.get("title", "Без названия")),
        "author": str(tag.get("author", "Неизвестен")),
        "pages": pages,
        "location": loc,
        "count": int(item.get("Count", 1)),
        "found_at": datetime.now().isoformat(timespec="seconds")
    }

def find_itemstacks(tag):
    """Рекурсивно ищет все ItemStack в NBT-теге"""
    try:
        if isinstance(tag, nbtlib.tag.Compound):
            # Проверяем, является ли тег ItemStack
            if 'id' in tag and 'Count' in tag:
                yield tag
            # Рекурсивно обходим вложенные теги
            for key, subtag in tag.items():
                yield from find_itemstacks(subtag)
        elif isinstance(tag, nbtlib.tag.List):
            for subtag in tag:
                yield from find_itemstacks(subtag)
    except Exception as e:
        log.warning(f"Ошибка при поиске ItemStack: {e}")

def get_root_tag(nbt_file):
    """Универсально получает корневой тег для разных версий nbtlib"""
    if hasattr(nbt_file, 'root'):
        return nbt_file.root
    return nbt_file

def load_nbt_file(filepath):
    """Загружает NBT с автоматическим определением сжатия"""
    try:
        # Сначала пробуем открыть как обычный файл
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Пробуем распаковать как gzip
        try:
            decompressed = gzip.decompress(data)
            file_obj = BytesIO(decompressed)
        except:
            # Если не gzip, используем исходные данные
            file_obj = BytesIO(data)
            
        nbt_file = nbtlib.File.parse(file_obj)
        return get_root_tag(nbt_file)
    except Exception as e:
        log.error(f"Ошибка при загрузке NBT из {filepath}: {e}")
        raise

def scan_level_dat(world_dir: Path):
    global books_total  # Это важно
    level_dat_file = world_dir / "level.dat"
    if not level_dat_file.exists():
        return
    try:
        root_tag = load_nbt_file(level_dat_file)
        world_name = world_dir.name
        loc = f"{world_name}: level.dat"
        for item in find_itemstacks(root_tag):
            if is_book(item):
                b = extract_book(item, loc)
                books_total += 1
                save_book(b, books_total)
                log.info('КНИГА #%d  "%s" (%s)  –  %s', books_total, b["title"], b["author"], loc)
    except Exception as e:
        log.error(f"Ошибка при обработке {level_dat_file}: {e}")

def scan_players(world_dir: Path):
    global books_total  # Это важно
    playerdata_dir = world_dir / "playerdata"
    if not playerdata_dir.exists():
        return
    for dat in playerdata_dir.glob("*.dat"):
        try:
            root_tag = load_nbt_file(dat)
            uuid = dat.stem
            world_name = world_dir.name
            loc = f"{world_name}: player:{uuid}"
            for item in find_itemstacks(root_tag):
                if is_book(item):
                    b = extract_book(item, loc)
                    books_total += 1
                    save_book(b, books_total)
                    log.info('КНИГА #%d  "%s" (%s)  –  %s', books_total, b["title"], b["author"], loc)
        except Exception as e:
            log.error(f"Ошибка при обработке файла игрока {dat}: {e}")

def scan_world_regions(world_dir: Path):
    global books_total, regions_done, chunks_te  # Это важно
    region_dir = world_dir / "region"
    if not region_dir.exists():
        return
    for rfile in sorted(region_dir.glob("*.mca")):
        log.info("Сканирую регион %s в мире %s", rfile.name, world_dir.name)
        with open(rfile, "rb") as f:
            locs = f.read(4096)
            for idx in range(1024):
                off = idx*4
                entry = locs[off:off+4]
                if entry == b"\x00\x00\x00\x00": 
                    continue
                sector_offset = ((entry[0]<<16)|(entry[1]<<8)|entry[2]) & 0xFFFFFF
                sector_count  = entry[3]&0xFF
                if sector_offset==0 or sector_count==0: 
                    continue
                f.seek(sector_offset*4096)
                head = f.read(5)
                if len(head) < 5: 
                    continue
                length, comp = struct.unpack(">IB", head)
                if length < 1: 
                    continue
                data = f.read(length-1)
                try:
                    if comp == 2:
                        raw = zlib.decompress(data)
                    elif comp == 1:
                        raw = gzip.decompress(data)
                    else:
                        log.warning(f"Неизвестная компрессия {comp} в регионе {rfile}, чанк {idx}")
                        continue
                except Exception as e:
                    log.warning(f"Ошибка распаковки чанка {idx} в регионе {rfile}: {e}")
                    continue

                # Расчет координат чанка
                region_x = int(rfile.stem.split('.')[1])
                region_z = int(rfile.stem.split('.')[2])
                cx = (idx % 32) + region_x * 32
                cz = (idx // 32) + region_z * 32

                try:
                    # Проверяем, что данные не пустые
                    if not raw:
                        log.warning(f"Пустые данные чанка ({cx},{cz}) в регионе {rfile}")
                        continue
                        
                    # Создаем файловый объект из байтов
                    file_obj = BytesIO(raw)
                    nbt_file = nbtlib.File.parse(file_obj)
                    root_tag = get_root_tag(nbt_file)
                    lvl = root_tag.get("Level", {})
                    containers = 0
                    
                    # Обработка TileEntities
                    for te in lvl.get("TileEntities", []):
                        te_id = str(te.get("id", "unknown"))
                        x = te.get("x", 0)
                        y = te.get("y", 0)
                        z = te.get("z", 0)
                        world_name = world_dir.name
                        loc = f"{world_name}: {te_id} at ({x},{y},{z})"
                        
                        for item in find_itemstacks(te):
                            if is_book(item):
                                b = extract_book(item, loc)
                                books_total += 1
                                save_book(b, books_total)
                                log.info('КНИГА #%d  "%s" (%s)  –  %s', books_total, b["title"], b["author"], loc)
                        containers += 1

                    # Обработка Entities
                    for ent in lvl.get("Entities", []):
                        ent_id = str(ent.get("id", "unknown"))
                        pos = ent.get("Pos", [0.0, 0.0, 0.0])
                        world_name = world_dir.name
                        loc = f"{world_name}: {ent_id} at ({pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f})"
                        
                        for item in find_itemstacks(ent):
                            if is_book(item):
                                b = extract_book(item, loc)
                                books_total += 1
                                save_book(b, books_total)
                                log.info('КНИГА #%d  "%s" (%s)  –  %s', books_total, b["title"], b["author"], loc)

                    if containers:
                        chunks_te += 1
                except Exception as e:
                    log.error(f"Ошибка при обработке чанка ({cx},{cz}) в регионе {rfile}: {e}")
        regions_done += 1

def find_worlds(root_dir: Path):
    """Скрипт рекурсивно жрёт папки"""
    worlds = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        current_dir = Path(dirpath)
        if "region" in dirnames or "playerdata" in dirnames or "level.dat" in filenames:
            worlds.append(current_dir)
    return worlds

def main():
    global books_total, regions_done, chunks_te  # Это важно
    print("Мировой сканер 1.7.10 – старт")
    world_dirs = find_worlds(WORLD_DIR)
    if not world_dirs:
        print("Миры не найдены в", WORLD_DIR)
        return
    for world_dir in world_dirs:
        log.info(f"Сканирую мир: {world_dir}")
        scan_level_dat(world_dir)
        scan_players(world_dir)
        scan_world_regions(world_dir)
    print("Готово!")
    print(f"Регионов обработано: {regions_done}")
    print(f"Чанков с контейнерами: {chunks_te}")
    print(f"Всего найдено written_book: {books_total}")
    if books_total:
        print("Файлы сохранены в:", OUTPUT_DIR / "books_json")

if __name__ == "__main__":
    main()