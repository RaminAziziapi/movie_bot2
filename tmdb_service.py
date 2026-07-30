import os
import requests


TMDB_API_KEY = os.environ.get("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"


def search_movie(query: str):
    """
    جستجوی فیلم در TMDB
    """

    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY تنظیم نشده است.")

    url = f"{TMDB_BASE_URL}/search/multi"

    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "fa-IR",
        "include_adult": False
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        raise Exception(
            f"خطا از TMDB: {response.status_code}"
        )

    data = response.json()

    results = data.get("results", [])

    if not results:
        return None

    item = results[0]

    tmdb_id = item.get("id")

    media_type = item.get("media_type")

    if media_type not in ["movie", "tv"]:
        return None

    details = get_details(tmdb_id, media_type)

    return details


def get_details(tmdb_id, media_type):
    """
    دریافت جزئیات کامل فیلم یا سریال
    """

    url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}"

    params = {
        "api_key": TMDB_API_KEY,
        "language": "fa-IR",
        "append_to_response": "credits"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    data = response.json()


    title = (
        data.get("title")
        or data.get("name")
    )

    original_title = (
        data.get("original_title")
        or data.get("original_name")
    )


    year = None

    date = (
        data.get("release_date")
        or data.get("first_air_date")
    )

    if date:
        year = date[:4]


    genres = [
        g["name"]
        for g in data.get("genres", [])
    ]


    countries = [
        c["name"]
        for c in data.get("production_countries", [])
    ]


    poster = None

    if data.get("poster_path"):
        poster = (
            "https://image.tmdb.org/t/p/w500"
            + data["poster_path"]
        )


    actors = []

    credits = data.get("credits", {})

    for actor in credits.get("cast", [])[:5]:
        actors.append(actor.get("name"))


    director = None

    for person in credits.get("crew", []):
        if person.get("job") == "Director":
            director = person.get("name")
            break


    runtime = None

    if media_type == "movie":
        runtime = data.get("runtime")

    else:
        runtime = data.get("episode_run_time", [None])[0]


    return {
        "title": title,
        "original_title": original_title,
        "tmdb_id": tmdb_id,
        "poster": poster,
        "year": year,
        "genre": ", ".join(genres),
        "rating": data.get("vote_average"),
        "description": data.get("overview"),
        "country": ", ".join(countries),
        "actors": ", ".join(actors),
        "director": director,
        "runtime": runtime,
        "type": media_type
    }