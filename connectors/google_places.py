# connectors/google_places.py
import time
import requests

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DETAILS_FIELDS = (
    "place_id,name,formatted_phone_number,formatted_address,"
    "website,rating,user_ratings_total,url"
)


class GooglePlacesConnector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_call_count = 0

    def geocode(self, city: str) -> tuple[float, float]:
        resp = requests.get(GEOCODE_URL, params={
            "address": f"{city}, France",
            "key": self.api_key,
        })
        self.api_call_count += 1
        data = resp.json()
        if data["status"] != "OK" or not data["results"]:
            raise ValueError(f"Geocoding failed for '{city}': {data['status']}")
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]

    def _get_place_details(self, place_id: str) -> dict:
        resp = requests.get(DETAILS_URL, params={
            "place_id": place_id,
            "fields": DETAILS_FIELDS,
            "key": self.api_key,
        })
        self.api_call_count += 1
        data = resp.json()
        if data["status"] != "OK":
            return {}
        return data.get("result", {})

    def search(self, lat: float, lng: float, place_type: str, radius: int = 15000) -> list[dict]:
        results = []
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": place_type,
            "key": self.api_key,
        }
        while True:
            resp = requests.get(NEARBY_URL, params=params)
            self.api_call_count += 1
            data = resp.json()
            if data["status"] not in ("OK", "ZERO_RESULTS"):
                break
            for item in data.get("results", []):
                details = self._get_place_details(item["place_id"])
                results.append({
                    "place_id": item["place_id"],
                    "name": details.get("name", item.get("name", "")),
                    "type": place_type,
                    "phone": details.get("formatted_phone_number", ""),
                    "address": details.get("formatted_address", ""),
                    "rating": details.get("rating"),
                    "user_ratings_total": details.get("user_ratings_total", 0),
                    "has_website": "website" in details,
                    "maps_url": details.get("url", ""),
                })
            next_token = data.get("next_page_token")
            if not next_token:
                break
            time.sleep(2)
            params = {"pagetoken": next_token, "key": self.api_key}
        return results
