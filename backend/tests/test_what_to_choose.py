from app.services.what_to_choose import MovieChoiceLLM

REQUEST_BODY = {"local_datetime": "2026-08-01T22:15:00", "timezone_offset_minutes": 420}


def test_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/api/library/watchlist/what-to-choose", json=REQUEST_BODY)
    assert response.status_code == 401


def test_empty_watchlist_returns_400(client, claude_responses):
    response = client.post("/api/library/watchlist/what-to-choose", json=REQUEST_BODY)
    assert response.status_code == 400


def test_happy_path_returns_claude_pick(client, claude_responses):
    add_first = client.post("/api/library/watchlist", json={"tmdb_id": 603})
    add_second = client.post("/api/library/watchlist", json={"tmdb_id": 604})
    assert add_first.status_code == 201
    assert add_second.status_code == 201
    picked_movie_id = add_second.json()["movie"]["id"]

    claude_responses.append(MovieChoiceLLM(movie_id=picked_movie_id, reason="Matches your taste for sci-fi."))

    response = client.post("/api/library/watchlist/what-to-choose", json=REQUEST_BODY)
    assert response.status_code == 200
    body = response.json()
    assert body["movie"]["id"] == picked_movie_id
    assert body["reason"] == "Matches your taste for sci-fi."


def test_invalid_pick_retries_then_falls_back_to_watchlist(client, claude_responses):
    add_response = client.post("/api/library/watchlist", json={"tmdb_id": 603})
    assert add_response.status_code == 201
    valid_movie_id = add_response.json()["movie"]["id"]

    # Both attempts return a movie_id that isn't actually on the watchlist.
    claude_responses.append(MovieChoiceLLM(movie_id=999999, reason="hallucinated pick"))
    claude_responses.append(MovieChoiceLLM(movie_id=999999, reason="hallucinated pick again"))

    response = client.post("/api/library/watchlist/what-to-choose", json=REQUEST_BODY)
    assert response.status_code == 200
    body = response.json()
    # Falls back to the only real watchlist entry rather than failing the request.
    assert body["movie"]["id"] == valid_movie_id
    assert "random" in body["reason"].lower()


def test_claude_error_falls_back_to_watchlist(client, claude_responses):
    add_response = client.post("/api/library/watchlist", json={"tmdb_id": 603})
    assert add_response.status_code == 201
    valid_movie_id = add_response.json()["movie"]["id"]

    # No responses queued — fake_call_claude returns None, simulating an API failure.
    response = client.post("/api/library/watchlist/what-to-choose", json=REQUEST_BODY)
    assert response.status_code == 200
    assert response.json()["movie"]["id"] == valid_movie_id
