"""Passage repository - Supabase 기반 passages 데이터 접근 레이어"""
import supa


async def get_all() -> dict:
    """전체 passages를 중첩 dict 구조로 반환"""
    try:
        if supa._enabled():
            rows = await supa.get_all_passages()
            if isinstance(rows, list) and rows:
                db = {"books": {}}
                for r in rows:
                    bk = r.get("book", "")
                    unit = r.get("unit", "")
                    pid = r.get("pid", "")
                    if not (bk and unit and pid):
                        continue
                    db["books"].setdefault(bk, {"units": {}})
                    db["books"][bk]["units"].setdefault(unit, {"passages": {}})
                    db["books"][bk]["units"][unit]["passages"][pid] = {
                        "title": r.get("title", pid),
                        "text": r.get("passage_text", ""),
                    }
                return db
    except Exception as e:
        print(f"[passage_repo] load error: {e}")

    return {"books": {}}


async def save_all(d: dict) -> None:
    """중첩 dict 구조를 flat row로 변환하여 Supabase에 저장"""
    try:
        if not supa._enabled():
            print("[passage_repo] Supabase not enabled")
            return

        rows = []
        for bk, bd in d.get("books", {}).items():
            for unit, ud in bd.get("units", {}).items():
                for pid, pi in ud.get("passages", {}).items():
                    rows.append({
                        "book": bk,
                        "unit": unit,
                        "pid": pid,
                        "title": pi.get("title", pid),
                        "passage_text": pi.get("text", ""),
                    })

        if not rows:
            return

        batch_size = 50
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            print(f"[passage_repo] Supabase upsert batch {start//batch_size + 1} ({len(batch)} rows)")
            await supa.upsert_passages_bulk(batch)

        print(f"[passage_repo] Supabase sync done: {len(rows)} rows total")
    except Exception as e:
        print(f"[passage_repo] save error: {e}")


async def delete_passage(book: str, unit: str, pid: str) -> None:
    """Supabase에서 개별 passage 삭제"""
    try:
        if supa._enabled():
            await supa.delete_passage(book, unit, pid)
    except Exception as e:
        print(f"[passage_repo] delete passage error: {e}")


async def delete_book(book: str) -> None:
    """Supabase에서 교재 전체 삭제"""
    try:
        if supa._enabled():
            await supa.delete_book(book)
    except Exception as e:
        print(f"[passage_repo] delete book error: {e}")
