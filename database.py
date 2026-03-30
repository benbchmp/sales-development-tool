# database.py
import sqlite3
from datetime import datetime, timezone


class Database:
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS places (
                    place_id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    phone TEXT,
                    address TEXT,
                    rating REAL,
                    user_ratings_total INTEGER,
                    has_website BOOLEAN,
                    maps_url TEXT,
                    fetched_at DATETIME,
                    status TEXT DEFAULT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def upsert_place(self, place: dict):
        conn = self._connect()
        try:
            conn.execute("""
                INSERT INTO places
                    (place_id, name, type, phone, address, rating,
                     user_ratings_total, has_website, maps_url, fetched_at)
                VALUES
                    (:place_id, :name, :type, :phone, :address, :rating,
                     :user_ratings_total, :has_website, :maps_url, :fetched_at)
                ON CONFLICT(place_id) DO UPDATE SET
                    name=excluded.name,
                    type=excluded.type,
                    phone=excluded.phone,
                    address=excluded.address,
                    rating=excluded.rating,
                    user_ratings_total=excluded.user_ratings_total,
                    has_website=excluded.has_website,
                    maps_url=excluded.maps_url,
                    fetched_at=excluded.fetched_at
            """, {**place, "fetched_at": datetime.now(timezone.utc).isoformat()})
            conn.commit()
        finally:
            conn.close()

    def get_places_without_website(self, place_type: str = None) -> list[dict]:
        conn = self._connect()
        try:
            if place_type:
                rows = conn.execute(
                    "SELECT * FROM places WHERE has_website = 0 AND type = ?",
                    (place_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM places WHERE has_website = 0"
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
