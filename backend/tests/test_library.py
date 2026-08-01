def test_diary_crud_flow(client):
    create_response = client.post(
        "/api/library/diary",
        json={
            "tmdb_id": 603,
            "watched_date": "2026-07-15",
            "rating": 4.5,
            "rewatch": False,
            "review_text": "Loved it.",
            "tags": ["sci-fi"],
            "liked": True,
        },
    )
    assert create_response.status_code == 201
    entry = create_response.json()
    assert entry["movie"]["tmdb_id"] == 603
    assert entry["rating"] == 4.5
    assert entry["source"] == "native"

    list_response = client.get("/api/library/diary")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    entry_id = entry["id"]
    patch_response = client.patch(f"/api/library/diary/{entry_id}", json={"rating": 5.0})
    assert patch_response.status_code == 200
    assert patch_response.json()["rating"] == 5.0

    delete_response = client.delete(f"/api/library/diary/{entry_id}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/library/diary/{entry_id}").status_code == 404


def test_watchlist_add_list_remove(client):
    add_response = client.post("/api/library/watchlist", json={"tmdb_id": 27205})
    assert add_response.status_code == 201
    movie_id = add_response.json()["movie"]["id"]

    # adding the same movie again should be idempotent, not a duplicate/error
    second_add = client.post("/api/library/watchlist", json={"tmdb_id": 27205})
    assert second_add.status_code == 201
    assert second_add.json()["movie"]["id"] == movie_id

    list_response = client.get("/api/library/watchlist")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    remove_response = client.delete(f"/api/library/watchlist/{movie_id}")
    assert remove_response.status_code == 204
    assert client.get("/api/library/watchlist").json() == []


def test_lists_create_add_reorder_remove(client):
    create_response = client.post(
        "/api/library/lists", json={"name": "Favorites", "description": "My top picks"}
    )
    assert create_response.status_code == 201
    list_id = create_response.json()["id"]

    add_first = client.post(f"/api/library/lists/{list_id}/movies", json={"tmdb_id": 603})
    assert add_first.status_code == 201
    add_second = client.post(f"/api/library/lists/{list_id}/movies", json={"tmdb_id": 604})
    assert add_second.status_code == 201

    detail = add_second.json()
    movie_ids_in_order = [item["movie"]["tmdb_id"] for item in detail["items"]]
    assert movie_ids_in_order == [603, 604]

    movie_id_603 = detail["items"][0]["movie"]["id"]
    movie_id_604 = detail["items"][1]["movie"]["id"]

    reorder_response = client.patch(
        f"/api/library/lists/{list_id}/movies/reorder",
        json={"movie_ids": [movie_id_604, movie_id_603]},
    )
    assert reorder_response.status_code == 200
    reordered_tmdb_ids = [item["movie"]["tmdb_id"] for item in reorder_response.json()["items"]]
    assert reordered_tmdb_ids == [604, 603]

    remove_response = client.delete(f"/api/library/lists/{list_id}/movies/{movie_id_603}")
    assert remove_response.status_code == 204

    get_response = client.get(f"/api/library/lists/{list_id}")
    assert len(get_response.json()["items"]) == 1

    delete_list_response = client.delete(f"/api/library/lists/{list_id}")
    assert delete_list_response.status_code == 204
    assert client.get(f"/api/library/lists/{list_id}").status_code == 404


def test_library_endpoints_require_auth(unauthenticated_client):
    assert unauthenticated_client.get("/api/library/diary").status_code == 401
    assert unauthenticated_client.get("/api/library/watchlist").status_code == 401
    assert unauthenticated_client.get("/api/library/lists").status_code == 401
