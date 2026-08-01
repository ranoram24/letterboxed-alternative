from datetime import datetime, timedelta

from app.models.recommendation_cache import RecommendationCache
from app.services.recommendations import RecommendationsLLM, RecommendedPick


def test_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/movies/recommendations")
    assert response.status_code == 401


def test_new_user_gets_no_recommendations_and_claude_is_not_called(client, mock_discover, monkeypatch):
    from app.services import recommendations as recommendations_module

    def fail_if_called(system_prompt):
        raise AssertionError("Claude should not be called with no rated diary entries")

    monkeypatch.setattr(recommendations_module, "_call_claude", fail_if_called)

    response = client.get("/api/movies/recommendations")
    assert response.status_code == 200
    assert response.json() == []


def test_happy_path_returns_ranked_claude_picks(client, mock_discover, recommendation_responses):
    log_response = client.post(
        "/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5}
    )
    assert log_response.status_code == 201

    recommendation_responses.append(
        RecommendationsLLM(
            recommendations=[
                RecommendedPick(movie_id=502, reason="Matches your drama taste."),
                RecommendedPick(movie_id=501, reason="Also fits your taste."),
            ]
        )
    )

    response = client.get("/api/movies/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert [item["movie"]["tmdb_id"] for item in body] == [502, 501]
    assert body[0]["movie"]["title"] == "Discover Movie 2"
    assert body[0]["reason"] == "Matches your drama taste."


def test_excludes_movies_already_in_diary_or_watchlist(client, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})
    # 501 is one of the mock discover candidates — logging it should keep it out of results.
    client.post("/api/library/diary", json={"tmdb_id": 501, "watched_date": "2026-07-02", "rating": 3.0})

    recommendation_responses.append(
        RecommendationsLLM(
            recommendations=[
                RecommendedPick(movie_id=501, reason="hallucinated — shouldn't have been a candidate"),
                RecommendedPick(movie_id=502, reason="Matches your drama taste."),
            ]
        )
    )

    response = client.get("/api/movies/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert [item["movie"]["tmdb_id"] for item in body] == [502]


def test_claude_error_returns_empty_list_gracefully(client, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})

    # No responses queued — fake_call_claude returns None, simulating an API failure.
    response = client.get("/api/movies/recommendations")
    assert response.status_code == 200
    assert response.json() == []


def test_second_request_within_a_day_is_served_from_cache(client, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})

    # Only one response queued — if the second request recomputed instead of hitting the
    # cache, _call_claude would return None (empty queue) and this would fail.
    recommendation_responses.append(
        RecommendationsLLM(recommendations=[RecommendedPick(movie_id=501, reason="Matches your drama taste.")])
    )

    first = client.get("/api/movies/recommendations")
    second = client.get("/api/movies/recommendations")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert second.json() == [{"movie": {"tmdb_id": 501, "title": "Discover Movie 1", "year": 2022, "poster_url": "https://image.tmdb.org/t/p/w500/501.jpg"}, "reason": "Matches your drama taste."}]


def test_stale_cache_is_recomputed(client, db_session, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})

    recommendation_responses.append(
        RecommendationsLLM(recommendations=[RecommendedPick(movie_id=501, reason="First pick.")])
    )
    first = client.get("/api/movies/recommendations")
    assert [item["movie"]["tmdb_id"] for item in first.json()] == [501]

    # Backdate the cache row past the 24h TTL.
    cache_row = db_session.get(RecommendationCache, "test@example.com")
    cache_row.computed_at = datetime.utcnow() - timedelta(hours=25)
    db_session.commit()

    recommendation_responses.append(
        RecommendationsLLM(recommendations=[RecommendedPick(movie_id=502, reason="Fresh pick.")])
    )
    second = client.get("/api/movies/recommendations")
    assert [item["movie"]["tmdb_id"] for item in second.json()] == [502]


def test_empty_result_is_not_cached(client, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})

    # First call: no response queued -> _call_claude returns None -> empty result, not cached.
    first = client.get("/api/movies/recommendations")
    assert first.json() == []

    recommendation_responses.append(
        RecommendationsLLM(recommendations=[RecommendedPick(movie_id=501, reason="Matches your drama taste.")])
    )
    second = client.get("/api/movies/recommendations")
    assert [item["movie"]["tmdb_id"] for item in second.json()] == [501]


def test_hallucinated_movie_id_is_dropped(client, mock_discover, recommendation_responses):
    client.post("/api/library/diary", json={"tmdb_id": 603, "watched_date": "2026-07-01", "rating": 4.5})

    recommendation_responses.append(
        RecommendationsLLM(
            recommendations=[
                RecommendedPick(movie_id=999999, reason="not a real candidate"),
                RecommendedPick(movie_id=501, reason="a real candidate"),
            ]
        )
    )

    response = client.get("/api/movies/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert [item["movie"]["tmdb_id"] for item in body] == [501]
