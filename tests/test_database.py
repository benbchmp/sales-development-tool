# tests/test_database.py
import os
import pytest
from database import Database

TEST_DB = "test_cache.db"

@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_schema_created():
    db = Database(TEST_DB)
    import sqlite3
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='places'")
    assert cursor.fetchone() is not None
    conn.close()

def test_insert_and_query():
    db = Database(TEST_DB)
    place = {
        "place_id": "abc123",
        "name": "Dupont Plomberie",
        "type": "plumber",
        "phone": "0601020304",
        "address": "12 rue de la Paix, Lyon",
        "rating": 4.5,
        "user_ratings_total": 23,
        "has_website": False,
        "maps_url": "https://maps.google.com/?cid=abc123",
    }
    db.upsert_place(place)
    results = db.get_places_without_website(place_type="plumber")
    assert len(results) == 1
    assert results[0]["name"] == "Dupont Plomberie"

def test_upsert_updates_existing():
    db = Database(TEST_DB)
    place = {
        "place_id": "abc123",
        "name": "Dupont Plomberie",
        "type": "plumber",
        "phone": "0601020304",
        "address": "12 rue de la Paix, Lyon",
        "rating": 4.5,
        "user_ratings_total": 23,
        "has_website": False,
        "maps_url": "https://maps.google.com/?cid=abc123",
    }
    db.upsert_place(place)
    place["rating"] = 4.8
    db.upsert_place(place)
    results = db.get_places_without_website(place_type="plumber")
    assert results[0]["rating"] == 4.8

def test_website_filter():
    db = Database(TEST_DB)
    db.upsert_place({
        "place_id": "no_site", "name": "Sans Site", "type": "plumber",
        "phone": "0601020304", "address": "Lyon", "rating": 4.0,
        "user_ratings_total": 5, "has_website": False,
        "maps_url": "https://maps.google.com/?cid=no_site",
    })
    db.upsert_place({
        "place_id": "with_site", "name": "Avec Site", "type": "plumber",
        "phone": "0607080910", "address": "Paris", "rating": 3.5,
        "user_ratings_total": 2, "has_website": True,
        "maps_url": "https://maps.google.com/?cid=with_site",
    })
    results = db.get_places_without_website(place_type="plumber")
    assert len(results) == 1
    assert results[0]["place_id"] == "no_site"
