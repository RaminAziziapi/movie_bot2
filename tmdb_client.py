import httpx

from config import TMDB_API_KEY, TMDB_IMAGE_BASE

TMDB_BASE = "https://api.themoviedb.org/3"


async def search_tmdb(query: str):
    """جستجوی نام در TMDB و برگردوندن اولین نتیجه فیلم/سریال معتبر."""
    if not TMDB_API_KEY:
        raise RuntimeError("متغیر محیطی TMDB_API_KEY تنظیم نشده است.")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{TMDB_BASE}/search/multi",
            params={"api_key": TMDB_API_KEY, "query": query, "language": "en-US"},
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

    for r in results:
        if r.get("media_type") in ("movie", "tv"):
            return r
    return None


async def get_tmdb_details(tmdb_id: int, media_type: str) -> dict:
    """گرفتن اطلاعات کامل + نام فارسی (در صورت وجود) برای یک آیتم."""
    if not TMDB_API_KEY:
        raise RuntimeError("متغیر محیطی TMDB_API_KEY تنظیم نشده است.")

    async with httpx.AsyncClient(timeout=15) as client:
        resp_en = await client.get(
            f"{TMDB_BASE}/{media_type}/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"},
        )
        resp_en.raise_for_status()
        data = resp_en.json()

        title_fa = None
        try:
            resp_fa = await client.get(
                f"{TMDB_BASE}/{media_type}/{tmdb_id}",
                params={"api_key": TMDB_API_KEY, "language": "fa-IR"},
            )
            if resp_fa.status_code == 200:
                fa_data = resp_fa.json()
                fa_title = fa_data.get("title") or fa_data.get("name")
                original = data.get("title") or data.get("name")
                if fa_title and fa_title != original:
                    title_fa = fa_title
        except httpx.HTTPError:
            pass

    return _parse_tmdb_data(data, media_type, title_fa)


def _parse_tmdb_data(data: dict, media_type: str, title_fa) -> dict:
    is_tv = media_type == "tv"
    title = data.get("name") if is_tv else data.get("title")
    original_title = data.get("original_name") if is_tv else data.get("original_title")
    date_field = data.get("first_air_date") if is_tv else data.get("release_date")
    year = (date_field or "")[:4]

    genres = ", ".join(g["name"] for g in data.get("genres", []))
    rating = str(round(data.get("vote_average", 0), 1)) if data.get("vote_average") else ""

    countries = data.get("production_countries") or []
    if countries:
        country = countries[0]["name"]
    else:
        country = ", ".join(data.get("origin_country", []) or [])

    if is_tv:
        runtimes = data.get("episode_run_time") or []
        runtime = f"{runtimes[0]} دقیقه" if runtimes else ""
    else:
        runtime = f"{data.get('runtime')} دقیقه" if data.get("runtime") else ""

    credits = data.get("credits", {}) or {}
    cast = credits.get("cast", [])[:5]
    actors = ", ".join(c.get("name", "") for c in cast)

    director = ""
    if is_tv:
        creators = data.get("created_by", []) or []
        director = ", ".join(c.get("name", "") for c in creators)
    else:
        crew = credits.get("crew", []) or []
        directors = [c.get("name", "") for c in crew if c.get("job") == "Director"]
        director = ", ".join(directors)

    poster_path = data.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None

    return {
        "tmdb_id": data.get("id"),
        "content_type": media_type,
        "title": title,
        "original_title": original_title,
        "title_fa": title_fa,
        "poster_url": poster_url,
        "year": year,
        "genre": genres,
        "rating": rating,
        "country": country,
        "runtime": runtime,
        "actors": actors,
        "director": director,
        "description_raw": data.get("overview", ""),
        "number_of_seasons": data.get("number_of_seasons") if is_tv else None,
        "number_of_episodes": data.get("number_of_episodes") if is_tv else None,
    }