"""
LeadFinder – page de recherche de leads Google Maps
"""

import os, time, requests, pandas as pd
from dotenv import load_dotenv
from dash import html, dcc, dash_table, Output, Input, State, no_update
import dash_bootstrap_components as dbc

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# ── Liste des activités ──────────────────────────────────────────────

def _cat(label):
    return {"label": f"── {label} ──", "value": f"__{label}", "disabled": True}

def _opt(label):
    return {"label": f"  {label}", "value": label}

ACTIVITY_OPTIONS = [
    _cat("Artisanat & BTP"),
    _opt("Plombier"), _opt("Électricien"), _opt("Menuisier"), _opt("Maçon"),
    _opt("Carreleur"), _opt("Peintre en bâtiment"), _opt("Serrurier"),
    _opt("Chauffagiste"), _opt("Couvreur"), _opt("Vitrier"),

    _cat("Beauté & Bien-être"),
    _opt("Coiffeur"), _opt("Barbier"), _opt("Esthéticienne"),
    _opt("Institut de beauté"), _opt("Massage"),

    _cat("Alimentation"),
    _opt("Boulangerie"), _opt("Boucherie"), _opt("Épicerie"),
    _opt("Traiteur"), _opt("Pizzeria"), _opt("Restaurant"),

    _cat("Auto & Moto"),
    _opt("Garagiste"), _opt("Carrossier"),
    _opt("Contrôle technique"), _opt("Pneumatiques"),

    _cat("Services"),
    _opt("Pressing"), _opt("Cordonnerie"), _opt("Photographe"),
    _opt("Agence immobilière"), _opt("Expert-comptable"), _opt("Avocat"),
    _opt("Vétérinaire"), _opt("Déménagement"), _opt("Nettoyage"),
]

# ── Google Places helpers ────────────────────────────────────────────

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def text_search(query: str, page_token: str | None = None) -> dict:
    params = {"query": query, "key": API_KEY}
    if page_token:
        params["pagetoken"] = page_token
    r = requests.get(PLACES_SEARCH_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API error: {data.get('status')} – {data.get('error_message', '')}")
    return data


def get_place_details(place_id: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website",
        "key": API_KEY,
    }
    r = requests.get(PLACE_DETAILS_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("result", {})


def search_all_pages(query: str, max_pages: int = 3) -> list[dict]:
    all_places: list[dict] = []
    token = None
    for _ in range(max_pages):
        data = text_search(query, page_token=token)
        all_places.extend(data.get("results", []))
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(2)
    return all_places


def enrich_with_details(places: list[dict]) -> list[dict]:
    for p in places:
        pid = p.get("place_id")
        if not pid:
            continue
        try:
            details = get_place_details(pid)
            p["_phone"] = details.get("formatted_phone_number", "")
            p["_website"] = details.get("website", "")
        except Exception:
            p["_phone"] = ""
            p["_website"] = ""
        time.sleep(0.1)
    return places


def places_to_df(places: list[dict]) -> pd.DataFrame:
    rows = []
    for p in places:
        place_id = p.get("place_id", "")
        rows.append({
            "Nom": p.get("name", ""),
            "Adresse": p.get("formatted_address", ""),
            "Téléphone": p.get("_phone", ""),
            "Note": p.get("rating", ""),
            "Avis": p.get("user_ratings_total", ""),
            "Site web": p.get("_website", ""),
            "Statut": p.get("business_status", ""),
            "Google Maps": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "",
        })
    return pd.DataFrame(rows)


# ── Layout ───────────────────────────────────────────────────────────

def layout():
    return dbc.Container([
        # Search form
        dbc.Row([
            dbc.Col(dbc.Input(id="lf-input-city", placeholder="Ville (ex: Lyon)", type="text"), md=4),
            dbc.Col(dcc.Dropdown(
                id="lf-input-activity",
                options=ACTIVITY_OPTIONS,
                placeholder="Activité (liste ou texte libre)...",
                clearable=True,
                searchable=True,
                style={"color": "#000"},
            ), md=4),
            dbc.Col(dbc.Button("Rechercher", id="lf-btn-search", color="primary", className="w-100"), md=2),
            dbc.Col(dbc.Button(
                html.I(className="bi bi-download", style={"fontSize": "1.1rem"}),
                id="lf-btn-csv",
                color="secondary",
                outline=True,
                title="Exporter en CSV",
                style={"padding": "6px 12px"},
            ), md="auto", className="d-flex align-items-center"),
        ], className="mb-3"),

        # Filters
        dbc.Row([
            dbc.Col(dbc.Checklist(
                id="lf-filter-no-site",
                options=[{"label": " Sans site web uniquement", "value": "no_site"}],
                value=["no_site"],
                inline=True,
            ), md=4),
            dbc.Col(html.Div(id="lf-result-count", className="text-end text-muted"), md=8),
        ], className="mb-3"),

        # Loading + results
        dcc.Loading(id="lf-loading", children=[
            dash_table.DataTable(
                id="lf-table-results",
                columns=[],
                data=[],
                page_size=20,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_header={"backgroundColor": "#303030", "fontWeight": "bold", "color": "#fff"},
                style_cell={
                    "backgroundColor": "#222",
                    "color": "#ddd",
                    "border": "1px solid #444",
                    "textAlign": "left",
                    "padding": "8px",
                    "maxWidth": "300px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {"if": {"filter_query": '{Site web} = ""'}, "backgroundColor": "#1a3a1a"},
                ],
                tooltip_duration=None,
                css=[{"selector": ".dash-table-tooltip", "rule": "background-color: #333; color: #eee;"}],
            ),
        ], type="circle"),

        # Hidden store for full data
        dcc.Store(id="lf-store-data"),
        dcc.Download(id="lf-download-csv"),

    ], fluid=True)


# ── Callbacks ────────────────────────────────────────────────────────

def register_callbacks(app):
    @app.callback(
        Output("lf-input-activity", "options"),
        Input("lf-input-activity", "search_value"),
        prevent_initial_call=True,
    )
    def update_activity_options(search):
        if not search or not search.strip():
            return ACTIVITY_OPTIONS
        search_lower = search.strip().lower()
        # Garder les options existantes qui matchent
        filtered = [
            o for o in ACTIVITY_OPTIONS
            if o.get("disabled") or search_lower in o.get("label", "").lower()
        ]
        # Supprimer les catégories orphelines (header sans enfants)
        cleaned = []
        for i, o in enumerate(filtered):
            if o.get("disabled"):
                has_child = any(
                    not filtered[j].get("disabled")
                    for j in range(i + 1, len(filtered))
                    if not filtered[j].get("disabled") or filtered[j].get("disabled") != filtered[i].get("disabled")
                )
                if has_child:
                    cleaned.append(o)
            else:
                cleaned.append(o)
        # Ajouter le texte libre en tête si pas déjà dans la liste
        exact_match = any(
            o.get("value", "").lower() == search_lower
            for o in ACTIVITY_OPTIONS if not o.get("disabled")
        )
        if not exact_match:
            free = [{"label": f'🔍 "{search.strip()}"', "value": search.strip()}]
            return free + (cleaned if cleaned else ACTIVITY_OPTIONS)
        return cleaned if cleaned else ACTIVITY_OPTIONS

    @app.callback(
        Output("lf-store-data", "data"),
        Input("lf-btn-search", "n_clicks"),
        State("lf-input-city", "value"),
        State("lf-input-activity", "value"),
        prevent_initial_call=True,
    )
    def run_search(n, city, activity):
        if not city or not activity:
            return no_update
        query = f"{activity} à {city}"
        try:
            places = search_all_pages(query)
            places = enrich_with_details(places)
            df = places_to_df(places)
            return df.to_dict("records")
        except Exception as e:
            print(f"[LeadFinder] Erreur API : {e}")
            return []

    @app.callback(
        Output("lf-table-results", "data"),
        Output("lf-table-results", "columns"),
        Output("lf-table-results", "tooltip_data"),
        Output("lf-result-count", "children"),
        Input("lf-store-data", "data"),
        Input("lf-filter-no-site", "value"),
    )
    def update_table(records, filters):
        if not records:
            return [], [], [], ""
        df = pd.DataFrame(records)

        total = len(df)
        if "no_site" in (filters or []):
            df = df[df["Site web"].fillna("").str.strip() == ""]
        shown = len(df)

        visible_cols = ["Nom", "Adresse", "Téléphone", "Note", "Avis", "Site web", "Statut"]
        columns = [{"name": c, "id": c} for c in visible_cols]
        columns.append({"name": "Google Maps", "id": "Google Maps", "presentation": "markdown"})

        df["Google Maps"] = df["Google Maps"].apply(
            lambda u: f"[Voir]({u})" if u else ""
        )

        tooltip = [
            {col: {"value": str(row.get(col, "")), "type": "text"} for col in visible_cols}
            for row in df.to_dict("records")
        ]

        count_text = f"{shown} résultats affichés / {total} trouvés au total"
        return df.to_dict("records"), columns, tooltip, count_text

    @app.callback(
        Output("lf-download-csv", "data"),
        Input("lf-btn-csv", "n_clicks"),
        State("lf-table-results", "data"),
        prevent_initial_call=True,
    )
    def export_csv(n, records):
        if not records:
            return no_update
        df = pd.DataFrame(records)
        return dcc.send_data_frame(df.to_csv, "leads.csv", index=False)
