"""Passage repository - Supabase 기반 passages 데이터 접근 레이어"""
import supa
from app.log.events import log_io_start, log_io_success, log_io_failure


def _check_enabled():
    if not supa._enabled():
        raise RuntimeError("Supabase 미활성: URL 또는 KEY 누락")


async def get_all() -> dict:
    """전체 passages를 중첩 dict 구조로 반환"""
    _check_enabled()
    try:
        rows = await supa.get_all_passages()
        if isinstance(rows, list) and rows:
            db = {"books": {}}
            for r in rows:
                bk = r.get("book_name", "")
                unit = r.get("unit", "")
                lesson = r.get("lesson", "")
                if not (bk and unit and lesson):
                    continue
                db["books"].setdefault(bk, {"units": {}})
                db["books"][bk]["units"].setdefault(unit, {"passages": {}})
                db["books"][bk]["units"][unit]["passages"][lesson] = {
                    "text": r.get("english_text", ""),
                    "korean_translation": r.get("korean_translation", ""),
                }
            return db
        return {"books": {}}
    except Exception as e:
        log_io_failure("passages 전체 조회 실패", error=str(e))
        raise


async def save_all(d: dict) -> None:
    """중첩 dict 구조를 flat row로 변환하여 Supabase에 저장"""
    _check_enabled()
    try:
        rows = []
        for bk, bd in d.get("books", {}).items():
            for unit, ud in bd.get("units", {}).items():
                for lesson, pi in ud.get("passages", {}).items():
                    rows.append({
                        "book_name": bk,
                        "unit": unit,
                        "lesson": lesson,
                        "english_text": pi.get("text", ""),
                        "korean_translation": pi.get("korean_translation", ""),
                    })

        if not rows:
            return

        batch_size = 50
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            log_io_start("passages batch upsert", batch_num=start//batch_size + 1, count=len(batch))
            await supa.upsert_passages_bulk(batch)

        log_io_success("passages 전체 저장 완료", count=len(rows))
    except Exception as e:
        log_io_failure("passages 저장 실패", error=str(e))
        raise


async def delete_passage(book_name: str, unit: str, lesson: str) -> None:
    """Supabase에서 개별 passage 삭제"""
    _check_enabled()
    try:
        await supa.delete_passage(book_name, unit, lesson)
    except Exception as e:
        log_io_failure("passage 삭제 실패", error=str(e))
        raise


async def delete_book(book_name: str) -> None:
    """Supabase에서 교재 전체 삭제"""
    _check_enabled()
    try:
        await supa.delete_book(book_name)
    except Exception as e:
        log_io_failure("교재 삭제 실패", error=str(e))
        raise
