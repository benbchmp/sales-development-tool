# tests/test_google_places.py
from unittest.mock import patch, MagicMock
from connectors.google_places import GooglePlacesConnector

MOCK_API_KEY = "test_key"


def test_geocode_returns_coordinates():
    mock_response = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 45.748, "lng": 4.846}}}]
    }
    with patch("connectors.google_places.requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)
        connector = GooglePlacesConnector(api_key=MOCK_API_KEY)
        lat, lng = connector.geocode("Lyon")
        assert abs(lat - 45.748) < 0.001
        assert abs(lng - 4.846) < 0.001


def test_geocode_raises_on_failure():
    mock_response = {"status": "ZERO_RESULTS", "results": []}
    with patch("connectors.google_places.requests.get") as mock_get:
        mock_get.return_value = MagicMock(json=lambda: mock_response)
        connector = GooglePlacesConnector(api_key=MOCK_API_KEY)
        try:
            connector.geocode("VilleInexistante99999")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_search_flags_website_correctly():
    nearby_page1 = {
        "status": "OK",
        "results": [
            {"place_id": "p1", "name": "Dupont Plomberie", "types": ["plumber"]},
            {"place_id": "p2", "name": "Martin BTP", "types": ["plumber"]},
        ],
        "next_page_token": None,
    }
    details_no_site = {
        "status": "OK",
        "result": {
            "place_id": "p1", "name": "Dupont Plomberie",
            "formatted_phone_number": "0601020304",
            "formatted_address": "12 rue de la Paix, 69001 Lyon",
            "rating": 4.5, "user_ratings_total": 12,
            "url": "https://maps.google.com/?cid=p1",
        },
    }
    details_with_site = {
        "status": "OK",
        "result": {
            "place_id": "p2", "name": "Martin BTP",
            "website": "https://martin-btp.fr",
            "formatted_phone_number": "0607080910",
            "formatted_address": "5 avenue Foch, 69006 Lyon",
            "rating": 4.0, "user_ratings_total": 5,
            "url": "https://maps.google.com/?cid=p2",
        },
    }
    responses = [
        MagicMock(json=lambda r=nearby_page1: r),
        MagicMock(json=lambda r=details_no_site: r),
        MagicMock(json=lambda r=details_with_site: r),
    ]
    with patch("connectors.google_places.requests.get", side_effect=responses):
        connector = GooglePlacesConnector(api_key=MOCK_API_KEY)
        results = connector.search(lat=45.748, lng=4.846, place_type="plumber")
    no_site = next(r for r in results if r["place_id"] == "p1")
    with_site = next(r for r in results if r["place_id"] == "p2")
    assert no_site["has_website"] is False
    assert with_site["has_website"] is True


def test_api_call_count_tracked():
    nearby = {
        "status": "OK",
        "results": [{"place_id": "p1", "name": "Test", "types": ["plumber"]}],
        "next_page_token": None,
    }
    details = {
        "status": "OK",
        "result": {
            "place_id": "p1", "name": "Test",
            "formatted_phone_number": "0601020304",
            "formatted_address": "Lyon", "rating": 4.0,
            "user_ratings_total": 1,
            "url": "https://maps.google.com/?cid=p1",
        },
    }
    responses = [MagicMock(json=lambda r=nearby: r), MagicMock(json=lambda r=details: r)]
    with patch("connectors.google_places.requests.get", side_effect=responses):
        connector = GooglePlacesConnector(api_key=MOCK_API_KEY)
        connector.search(lat=45.748, lng=4.846, place_type="plumber")
    assert connector.api_call_count == 2
