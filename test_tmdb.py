from tmdb_service import search_movie


result = search_movie("Interstellar")


if result:
    print("اتصال موفق بود:")
    print(result)
else:
    print("چیزی پیدا نشد")