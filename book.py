#!/usr/bin/env python3
import gzip, json, logging, os, struct, tempfile, zlib
from datetime import datetime
from pathlib import Path
import nbtlib

WORLD_DIR   = Path(__file__).with_name("HardcoreMap")
OUTPUT_DIR  = Path(__file__).with_name("exported_books")
LOG_FILE    = Path(__file__).with_name("world_fixed.log")

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"),
                              logging.StreamHandler()])
log = logging.getLogger("wf")

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
    return id_ in ("387", "minecraft:written_book", "written_book") and "pages" in item.get("tag", {})

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

def scan_items(items, loc: str):
    global books_total
    for it in items:
        if is_book(it):
            b = extract_book(it, loc)
            books_total += 1
            save_book(b, books_total)
            log.info('КНИГА #%d  "%s" (%s)  –  %s', books_total, b["title"], b["author"], loc)

# ---------- регионы ----------
def scan_world_regions():
    global regions_done, chunks_te
    for rfile in sorted((WORLD_DIR / "region").glob("*.mca")):
        log.info("Сканирую регион %s", rfile.name)
        with open(rfile, "rb") as f:
            locs = f.read(4096)
            for idx in range(1024):
                off = idx*4
                entry = locs[off:off+4]
                if entry == b"\x00\x00\x00\x00": continue
                sector_offset = ((entry[0]<<16)|(entry[1]<<8)|entry[2]) & 0xFFFFFF
                sector_count  = entry[3]&0xFF
                if sector_offset==0 or sector_count==0: continue
                f.seek(sector_offset*4096)
                head = f.read(5)
                if len(head)<5: continue
                length, comp = struct.unpack(">IB", head)
                data = f.read(length-1)
                try:
                    raw = {2: zlib.decompress, 1: gzip.decompress}[comp](data)
                except Exception:
                    continue
                # Расчёт координат чанка. В душе не ипу как работает, но работает!
                region_x = int(rfile.stem.split('.')[1])
                region_z = int(rfile.stem.split('.')[2])
                cx = (idx % 32) + region_x * 32
                cz = (idx // 32) + region_z * 32
                cnt = scan_chunk_region(raw, cx, cz, rfile.name)
                if cnt:
                    chunks_te += 1
        regions_done += 1

def scan_chunk_region(raw: bytes, cx: int, cz: int, rname: str) -> int:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as tmp:
        tmp.write(raw)
        tmp_name = tmp.name
    try:
        import nbtlib
        lvl = nbtlib.load(tmp_name).get("Level", {})
        containers = 0
        # TileEntities
        for te in lvl.get("TileEntities", []):
            tid = te.get("id", "")
			#Да, ОПы плагинами пихали книги в маяк и стойку для варки зелий. Они тютю, но зато книги никто спереть не мог.
            if tid in {"Chest", "TrappedChest", "Dropper", "Dispenser", "Hopper", "Furnace", "BrewingStand", "Beacon"} and "Items" in te:
                x, y, z = te.get("x", 0), te.get("y", 0), te.get("z", 0)
                scan_items(te["Items"], f"{tid}:{rname}[{x},{y},{z}]")
                containers += 1
            if tid == "ItemFrame" and "Item" in te:
                it = te["Item"]
                if is_book(it):
                    x, y, z = te.get("x", 0), te.get("y", 0), te.get("z", 0)
                    b = extract_book(it, f"item_frame:{rname}[{x},{y},{z}]")
                    global books_total
                    books_total += 1
                    save_book(b, books_total)
                    log.info('КНИГА #%d  "%s" (%s)  –  item_frame:%s[%d,%d,%d]', books_total, b["title"], b["author"], rname, x, y, z)
        # Entities (Item, ItemFrame, ArmorStand)
        for ent in lvl.get("Entities", []):
            eid = ent.get("id", "")
            if eid in ("Item", "ItemFrame") and "Item" in ent:
                pos = ent.get("Pos", [0, 0, 0])
                it = ent["Item"]
                if is_book(it):
                    b = extract_book(it, f"entity:{rname}[{pos[0]:.1f},{pos[1]:.1f},{pos[2]:.1f}]")
                    books_total += 1
                    save_book(b, books_total)
                    log.info('КНИГА #%d  "%s" (%s)  –  entity:%s', books_total, b["title"], b["author"], rname)
            if eid == "ArmorStand":
                if "Equipment" in ent:
                    scan_items(ent["Equipment"], f"armor_stand:{rname}")
                if "HandItems" in ent:
                    scan_items(ent["HandItems"], f"armor_stand_hand:{rname}")
        return containers
    except Exception:
        return 0
    finally:
        os.unlink(tmp_name)

# ---------- Игроки. На некоторых мирах ловит exception из-за инвертарей модифицируемых модами. Я не знаю почему, поэтому в версии 2.0 буду разбираться. А пока так. ----------
def scan_players():
    for dat in (WORLD_DIR / "playerdata").glob("*.dat"):
        try:
            nbt = nbtlib.load(dat)
            uuid = dat.stem
            scan_items(nbt.root.get("Inventory", []), f"player:{uuid}")
            scan_items(nbt.root.get("EnderItems", []), f"ender_chest:{uuid}")
        except Exception:
            pass

# ---------- main ----------
def main():
    print("Мировой сканер 1.7.10 – старт")
    scan_world_regions()
    scan_players()
    print("Готово!")
    print(f"Регионов обработано: {regions_done}")
    print(f"Чанков с контейнерами: {chunks_te}")
    print(f"Всего найдено written_book: {books_total}")
    if books_total:
        print("Файлы сохранены в:", OUTPUT_DIR / "books_json")

if __name__ == "__main__":
    main()