"""
سرویس ارتباط با TMDB.
مسئولیت: فقط دریافت اطلاعات واقعی فیلم/سریال (بدون هیچ پردازش یا ترجمه‌ای).
ترجمه و پردازش متن بر عهده‌ی gemini_service است.

نکته: در کل پروژه، نوع محتوا با مقادیر 'movie' و 'series' نمایش داده
می‌شود (نه 'tv' که TMDB داخلی استفاده می‌کند)؛ تبدیل بین این دو فقط در
همین فایل انجام می‌شود تا بقیه ماژول‌ها درگیر جزئیات TMDB نشوند.
"""
from typing import Any, Optional

import httpx

from config import config

TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w780"

_SUPPORTED_TMDB_TYPES = ("movie", "tv")


def _to_internal_media_type(tmdb_media_type: str) -> str:
    return "series" if tmdb_media_type == "tv" else tmdb_media_type


def _to_tmdb_media_type(internal_media_type: str) -> str:
    return "tv" if internal_media_type == "series" else internal_media_type


async def search_title(query: str) -> list[dict[str, Any]]:
    """
    جستجوی نام فیلم/سریال. ابتدا با زبان فارسی و در صورت نبود نتیجه با انگلیسی.
    خروجی: لیست نتایج با media_type به شکل 'movie' یا 'series'.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        for language in ("fa-IR", "en-US"):
            response = await client.get(
                f"{TMDB_BASE_URL}/search/multi",
                params={
                    "api_key": config.TMDB_API_KEY,
                    "query": query,
                    "language": language,
                    "include_adult": "false",
                },
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            filtered = [r for r in results if r.get("media_type") in _SUPPORTED_TMDB_TYPES]
            if filtered:
                for r in filtered:
                    r["media_type"] = _to_internal_media_type(r["media_type"])
                return filtered
    return []


def _extract_country(data: dict) -> Optional[str]:
    countries = data.get("production_countries")
    if countries:
        return "، ".join(c["name"] for c in countries)
    origin = data.get("origin_country")
    if origin:
        return "، ".join(origin)
    return None


def _extract_persian_translation(data: dict) -> tuple[Optional[str], Optional[str]]:
    """در صورت وجود ترجمه فارسی رسمی در TMDB، عنوان و خلاصه فارسی را برمی‌گرداند."""
    translations = data.get("translations", {}).get("translations", [])
    for t in translations:
        if t.get("iso_639_1") == "fa":
            td = t.get("data", {})
            title = td.get("title") or td.get("name") or None
            overview = td.get("overview") or None
            return title, overview
    return None, None


def _extract_director(media_type: str, data: dict) -> Optional[str]:
    if media_type == "movie":
        for member in data.get("credits", {}).get("crew", []):
            if member.get("job") == "Director":
                return member.get("name")
        return None
    creators = data.get("created_by", [])
    if creators:
        return "، ".join(c["name"] for c in creators)
    return None


async def get_details(tmdb_id: int, media_type: str) -> dict[str, Any]:
    """
    دریافت اطلاعات کامل یک فیلم یا سریال از TMDB.
    media_type ورودی/خروجی همیشه 'movie' یا 'series' است.
    """
    if media_type not in ("movie", "series"):
        raise ValueError(f"نوع رسانه پشتیبانی نمی‌شود: {media_type}")

    tmdb_type = _to_tmdb_media_type(media_type)

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{TMDB_BASE_URL}/{tmdb_type}/{tmdb_id}",
            params={
                "api_key": config.TMDB_API_KEY,
                "language": "en-US",
                "append_to_response": "credits,translations",
            },
        )
        response.raise_for_status()
        data = response.json()

    persian_title, persian_overview = _extract_persian_translation(data)

    cast = data.get("credits", {}).get("cast", [])[:6]
    actors = "، ".join(member["name"] for member in cast) if cast else None

    genres = "، ".join(g["name"] for g in data.get("genres", [])) or None

    title = data.get("title") or data.get("name")
    original_title = data.get("original_title") or data.get("original_name")

    date_raw = data.get("release_date") or data.get("first_air_date") or ""
    year = int(date_raw[:4]) if date_raw[:4].isdigit() else None

    poster_path = data.get("poster_path")
    poster_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else None

    runtime = data.get("runtime")
    if runtime is None:
        episode_runtimes = data.get("episode_run_time") or []
        runtime = episode_runtimes[0] if episode_runtimes else None

    result: dict[str, Any] = {
        "tmdb_id": tmdb_id,
        "media_type": media_type,
        "title": title,
        "original_title": original_title,
        "persian_title": persian_title,
        "poster_url": poster_url,
        "year": year,
        # فیلد transient: فقط برای ورودی Gemini/fallback استفاده می‌شود، مستقیم ذخیره نمی‌شود
        "genres": genres,
        "rating": data.get("vote_average"),
        "country": _extract_country(data),
        "runtime": runtime,
        "actors": actors,
        "director": _extract_director(media_type, data),
        "description_en": data.get("overview"),
        # فیلد transient: فقط ورودی خام برای Gemini است و مستقیم ذخیره نمی‌شود
        "description_fa_raw": persian_overview,
    }

    if media_type == "series":
        result["number_of_seasons"] = data.get("number_of_seasons")
        result["number_of_episodes"] = data.get("number_of_episodes")

    return result
