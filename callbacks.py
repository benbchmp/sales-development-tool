# callbacks.py
import os
import tempfile
import requests
from dash import Input, Output, State, no_update, dcc
from dotenv import load_dotenv
from connectors.google_places import GooglePlacesConnector
from database import Database
from utils.export import generate_excel

load_dotenv()

db = Database()


def register_callbacks(app):

    @app.callback(
        Output("input-city", "options"),
        Input("input-city", "search_value"),
        prevent_initial_call=True,
    )
    def autocomplete_city(search_value):
        if not search_value or len(search_value) < 2:
            return []
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return []
        try:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/autocomplete/json",
                params={
                    "input": search_value,
                    "types": "(cities)",
                    "components": "country:fr",
                    "language": "fr",
                    "key": api_key,
                },
                timeout=5,
            )
            data = resp.json()
            if data["status"] != "OK":
                return []
            return [
                {"label": p["description"], "value": p["structured_formatting"]["main_text"]}
                for p in data.get("predictions", [])
            ]
        except Exception:
            return []

    @app.callback(
        Output("store-results", "data"),
        Output("search-status", "children"),
        Output("btn-export", "disabled"),
        Input("btn-search", "n_clicks"),
        State("input-city", "value"),
        State("input-type", "value"),
        State("check-no-website", "value"),
        prevent_initial_call=True,
    )
    def run_search(n_clicks, city, place_type, no_website_filter):
        if not city or not place_type:
            return no_update, "Veuillez renseigner une ville et un type de commerce.", True

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return no_update, "Clé API Google manquante. Vérifiez votre fichier .env", True

        try:
            connector = GooglePlacesConnector(api_key=api_key)

            lat, lng = connector.geocode(city)
            places = connector.search(lat=lat, lng=lng, place_type=place_type)

            for place in places:
                db.upsert_place(place)

            if no_website_filter and "no_website" in no_website_filter:
                display = [p for p in places if not p["has_website"]]
            else:
                display = places

            for lead in display:
                if lead.get("maps_url"):
                    lead["maps_url"] = f"[Voir]({lead['maps_url']})"

            status = (
                f"{len(display)} résultat(s) trouvé(s) "
                f"({connector.api_call_count} appels API consommés)"
            )
            export_disabled = len(display) == 0
            return display, status, export_disabled

        except Exception as e:
            return [], f"Erreur : {e}", True

    @app.callback(
        Output("table-results", "data"),
        Input("store-results", "data"),
    )
    def update_table(data):
        return data or []

    @app.callback(
        Output("download-excel", "data"),
        Input("btn-export", "n_clicks"),
        State("store-results", "data"),
        prevent_initial_call=True,
    )
    def export_excel(n_clicks, data):
        if not data:
            return no_update
        clean_data = []
        for lead in data:
            lead = dict(lead)
            if lead.get("maps_url", "").startswith("[Voir]("):
                lead["maps_url"] = lead["maps_url"][7:-1]
            clean_data.append(lead)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        generate_excel(clean_data, tmp_path)
        return dcc.send_file(tmp_path, filename="leads.xlsx")
