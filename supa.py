"""Supabase helper - passages + step cache storage"""
import json
from urllib.parse import quote

import httpx
from postgrest import AsyncPostgrestClient

from app.config import get_settings
from app.log.events import log_io_start, log_io_success, log_io_failure

SUPABASE_URL = get_settings().supabase_url
SUPABASE_KEY = get_settings().supabase_key.get_secret_value()


def _enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _client() -> AsyncPostgrestClient:
    return AsyncPostgrestClient(
        base_url=f"{SUPABASE_URL}/rest/v1",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )


# ========================
# Passages (wb_passages) — postgrest
# ========================
async def get_all_passages():
    if not _enabled():
        return []
    try:
        log_io_start("passages 전체 조회")
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .select("*")
                .order("unit")
                .order("lesson")
                .execute()
            )
            log_io_success("passages 전체 조회 완료", count=len(result.data or []))
            return result.data if result.data else []
    except Exception as e:
        log_io_failure("passages 전체 조회 실패", error=str(e))
        raise


async def get_passage(book_name, unit, lesson):
    if not _enabled():
        return None
    try:
        log_io_start("passage 단건 조회", book_name=book_name, unit=unit, lesson=lesson)
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .select("*")
                .eq("book_name", book_name)
                .eq("unit", unit)
                .eq("lesson", lesson)
                .execute()
            )
            if result.data:
                log_io_success("passage 단건 조회 완료")
                return result.data[0]
            return None
    except Exception as e:
        log_io_failure("passage 단건 조회 실패", error=str(e))
        raise


async def upsert_passage(book_name, unit, lesson, english_text, korean_translation=""):
    if not _enabled():
        return None
    try:
        log_io_start("passage upsert", book_name=book_name, unit=unit, lesson=lesson)
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .upsert({
                    "book_name": book_name,
                    "unit": unit,
                    "lesson": lesson,
                    "english_text": english_text,
                    "korean_translation": korean_translation,
                }, on_conflict="book_name,unit,lesson")
                .execute()
            )
            log_io_success("passage upsert 완료")
            return result.data
    except Exception as e:
        log_io_failure("passage upsert 실패", error=str(e))
        raise


async def upsert_passages_bulk(rows):
    """Bulk upsert: [{book_name, unit, lesson, english_text, korean_translation}, ...]"""
    if not rows or not _enabled():
        return None
    try:
        log_io_start("passages bulk upsert", count=len(rows))
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .upsert(rows, on_conflict="book_name,unit,lesson")
                .execute()
            )
            log_io_success("passages bulk upsert 완료", count=len(result.data or []))
            return result.data
    except Exception as e:
        log_io_failure("passages bulk upsert 실패", error=str(e))
        raise


async def delete_passage(book_name, unit, lesson):
    """Delete a single passage"""
    if not _enabled():
        return None
    try:
        log_io_start("passage 삭제", book_name=book_name, unit=unit, lesson=lesson)
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .delete()
                .eq("book_name", book_name)
                .eq("unit", unit)
                .eq("lesson", lesson)
                .execute()
            )
            log_io_success("passage 삭제 완료")
            return result.data
    except Exception as e:
        log_io_failure("passage 삭제 실패", error=str(e))
        raise


async def delete_book(book_name):
    """Delete all passages of a book"""
    if not _enabled():
        return None
    try:
        log_io_start("교재 전체 삭제", book_name=book_name)
        async with _client() as client:
            result = await (
                client.table("wb_passages")
                .delete()
                .eq("book_name", book_name)
                .execute()
            )
            log_io_success("교재 전체 삭제 완료", book_name=book_name)
            return result.data
    except Exception as e:
        log_io_failure("교재 전체 삭제 실패", error=str(e))
        raise


# ========================
# Step Cache (table: step_cache) — httpx (원본 유지)
# ========================
def _headers(extra: dict | None = None) -> dict:
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if extra:
        h.update(extra)
    return h

async def _request(method: str, endpoint: str, body=None, extra_headers: dict | None = None):
    """Async HTTP call to Supabase REST API - fresh client each time to avoid Event loop closed"""
    if not _enabled():
        return None
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = _headers(extra_headers)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.request(
                method,
                url,
                headers=headers,
                content=json.dumps(body, ensure_ascii=False) if body is not None else None,
            )
        raw = resp.text.strip()
        if not raw:
            print(f"[supa] empty response for {method} {endpoint} (status={resp.status_code})")
            return None
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "message" in parsed:
            print(f"[supa] API error: {parsed.get('message','')[:200]}")
        return parsed
    except Exception as e:
        print(f"[supa] request exception: {str(e)[:200]}")
        return None

async def get_step(cache_key, step_name):
    q = (
        "step_cache?"
        f"cache_key=eq.{quote(cache_key, safe='')}&"
        f"step_name=eq.{quote(step_name, safe='')}&select=data"
    )
    result = await _request("GET", q)
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("data")
    return None

async def save_step_supa(cache_key, step_name, data):
    body = {"cache_key": cache_key, "step_name": step_name, "data": data}
    return await _request(
        "POST",
        "step_cache?on_conflict=cache_key,step_name",
        body=body,
        extra_headers={"Prefer": "resolution=merge-duplicates, return=representation"},
    )

async def count_steps(cache_key):
    q = f"step_cache?cache_key=eq.{quote(cache_key, safe='')}&select=step_name"
    result = await _request("GET", q)
    if isinstance(result, list):
        return len(result)
    return 0

async def delete_steps_by_cache_key(cache_key):
    """Delete all cached steps for a cache_key from step_cache"""
    q = f"step_cache?cache_key=eq.{quote(cache_key, safe='')}"
    return await _request("DELETE", q)
