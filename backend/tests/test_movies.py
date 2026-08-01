def test_search_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/movies/search", params={"q": "matrix"})
    assert response.status_code == 401


def test_search_returns_results(client):
    response = client.get("/api/movies/search", params={"q": "matrix"})
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["title"] == "Search Result"


def test_popular_does_not_require_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/movies/popular")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 2
    assert movies[0]["tmdb_id"] == 1
    assert movies[0]["poster_url"].startswith("https://")


def test_now_playing_does_not_require_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/movies/now-playing")
    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 1
    assert movies[0]["title"] == "New Release 1"


def test_get_movie_caches_locally(client):
    response = client.get("/api/movies/603")
    assert response.status_code == 200
    body = response.json()
    assert body["tmdb_id"] == 603
    assert body["title"] == "Test Movie 603"

    # second fetch should return the same cached row, not create a duplicate
    response_again = client.get("/api/movies/603")
    assert response_again.status_code == 200
    assert response_again.json()["id"] == body["id"]


def test_reviews_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/movies/603/reviews")
    assert response.status_code == 401


def test_reviews_are_visible_across_users(client, db_session):
    from datetime import date

    from app.models.diary_entry import DiaryEntry
    from app.models.user import User

    log_response = client.post(
        "/api/library/diary",
        json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5, "review_text": "Great movie."},
    )
    assert log_response.status_code == 201
    movie_id = log_response.json()["movie"]["id"]

    other_user = User(email="other@example.com", display_name="Other User")
    db_session.add(other_user)
    db_session.add(
        DiaryEntry(
            user_email="other@example.com",
            movie_id=movie_id,
            watched_date=date(2026, 6, 1),
            rating=3.0,
            review_text="It was fine.",
            liked=False,
        )
    )
    db_session.commit()

    # an entry with no review_text shouldn't show up as a "review"
    client.post("/api/library/diary", json={"tmdb_id": 604, "watched_date": "2026-07-02"})

    response = client.get("/api/movies/603/reviews")
    assert response.status_code == 200
    reviews = response.json()
    assert len(reviews) == 2
    assert {review["reviewer_name"] for review in reviews} == {"Test User", "Other User"}
