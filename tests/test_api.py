import pandas as pd

import main
from tests.conftest import authenticate


def create_book(client, headers, book_id, good_id, rating=4.0):
    response = client.post(
        "/createBook",
        headers=headers,
        json={
            "id": book_id,
            "good_id": good_id,
            "title": f"Book {book_id}",
            "authors": "Author",
            "average_rating": rating,
            "image_url": "",
        },
    )
    assert response.status_code == 200, response.text


def test_authentication_authorization_and_validation(client):
    admin_headers = authenticate(client, 1)
    user_headers = authenticate(client, 2)
    payload = {
        "id": 10,
        "good_id": 110,
        "title": "Book 10",
        "authors": "Author",
        "average_rating": 4.5,
        "image_url": "",
    }

    assert client.post("/createBook", json=payload).status_code == 401
    assert client.post("/createBook", headers=user_headers, json=payload).status_code == 403
    assert client.post("/createBook", headers=admin_headers, json=payload).status_code == 200

    invalid_rating = {"book_id": 10, "user_id": 2, "rating": 6}
    assert client.post("/rating", headers=user_headers, json=invalid_rating).status_code == 422

    other_user_rating = {"book_id": 10, "user_id": 3, "rating": 5}
    assert client.post("/rating", headers=user_headers, json=other_user_rating).status_code == 403

    assert client.get("/clearTables").status_code == 404
    assert client.get("/loadTest").status_code == 404
    assert client.delete("/admin/data", headers=user_headers).status_code == 403
    assert client.delete("/admin/data", headers=admin_headers).status_code == 200

    wrong_password = client.post(
        "/createUser",
        json={"id": 2, "name": "User 2", "password": "wrongpass"},
    )
    assert wrong_password.status_code == 401


def test_end_to_end_interactions_and_recommendations(client):
    admin_headers = authenticate(client, 1)
    user_headers = authenticate(client, 2)
    create_book(client, admin_headers, 10, 110, 4.8)
    create_book(client, admin_headers, 20, 120, 4.5)
    create_book(client, admin_headers, 30, 130, 4.0)

    for book_id, tag_name in ((10, "science"), (20, "science"), (30, "history")):
        response = client.post(
            "/tag",
            headers=user_headers,
            json={"book_id": book_id, "tag_name": tag_name},
        )
        assert response.status_code == 200, response.text

    rating_response = client.post(
        "/rating",
        headers=user_headers,
        json={"book_id": 10, "user_id": 2, "rating": 5},
    )
    assert rating_response.status_code == 200

    read_response = client.post(
        "/read",
        headers=user_headers,
        json={"book_id": 20, "value": True, "id": 2},
    )
    assert read_response.status_code == 200

    by_book = client.get("/RecIB/10")
    assert by_book.status_code == 200
    assert 10 not in [book["id"] for book in by_book.json()]

    personalized = client.get("/RecIBUsu/2", headers=user_headers)
    assert personalized.status_code == 200
    assert 10 not in [book["id"] for book in personalized.json()]

    collaborative = client.get("/RecUB/2", headers=user_headers)
    assert collaborative.status_code == 200
    assert 10 not in [book["id"] for book in collaborative.json()]

    forbidden = client.get("/RecUB/2", headers=admin_headers)
    assert forbidden.status_code == 200

    model_status = client.get("/recommendations/status", headers=user_headers)
    assert model_status.status_code == 200
    assert model_status.json()["is_stale"] is False

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert len(client.get("/all").json()) == 3
    assert client.get("/getBook/10").json()["title"] == "Book 10"
    assert client.get("/getBook/999").status_code == 404
    assert client.post("/admin/recommendations/rebuild", headers=user_headers).status_code == 403
    assert client.post("/admin/recommendations/rebuild", headers=admin_headers).status_code == 200


def test_admin_test_data_load_uses_validated_protected_endpoint(client, monkeypatch):
    admin_headers = authenticate(client, 1)
    user_headers = authenticate(client, 2)
    sources = {
        "books.csv": pd.DataFrame(
            {
                "id": [10, 20],
                "book_id": [110, 120],
                "original_title": ["Book 10", "Book 20"],
                "authors": ["Author", "Author"],
                "average_rating": [4.5, 4.0],
                "image_url": ["", ""],
            }
        ),
        "ratings.csv": pd.DataFrame(
            {
                "book_id": [10, 10, 20],
                "user_id": [2, 2, 3],
                "rating": [5, 3, 4],
            }
        ),
        "tags.csv": pd.DataFrame(
            {"tag_id": [1], "tag_name": ["science"]}
        ),
        "to_read.csv": pd.DataFrame({"user_id": [2], "book_id": [20]}),
        "book_tags.csv": pd.DataFrame(
            {
                "goodreads_book_id": [110, 110, 120],
                "tag_id": [1, 1, 1],
                "count": [5, 4, 4],
            }
        ),
    }

    monkeypatch.setattr(main.pd, "read_csv", lambda path: sources[path.name].copy())

    assert client.post("/admin/load-test-data", headers=user_headers).status_code == 403
    response = client.post("/admin/load-test-data", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["books"] == 2
    assert response.json()["ratings"] == 2
    assert response.json()["book_tags"] == 2
    assert len(client.get("/all").json()) == 2


def test_experiment_simulator_is_admin_only_and_does_not_mutate_domain_data(client):
    admin_headers = authenticate(client, 1)
    user_headers = authenticate(client, 2)

    assert client.get("/admin/experiments/catalog").status_code == 401
    assert (
        client.get("/admin/experiments/catalog", headers=user_headers).status_code
        == 403
    )

    catalog_response = client.get(
        "/admin/experiments/catalog", headers=admin_headers
    )
    assert catalog_response.status_code == 200
    payload = catalog_response.json()["default_request"]
    payload["models"] = ["hybrid"]

    response = client.post(
        "/admin/experiments/simulate", headers=admin_headers, json=payload
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["kind"] == "exploratory_simulation"
    assert len(result["series"]) == 2
    assert result["comparison"][0]["quality_loss_reduction_percent"] > 0
    assert client.get("/all").json() == []
