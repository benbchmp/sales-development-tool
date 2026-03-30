"""
LeadFinder – Trouve les entreprises sans site web sur Google Maps
Lance : python app.py  →  http://127.0.0.1:8060
"""

import os, time, requests, pandas as pd
from dotenv import load_dotenv
from dash import Dash, html, dcc, dash_table, callback, Output, Input, State, no_update
import dash_bootstrap_components as dbc

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# ── Google Places helpers ────────────────────────────────────────────

PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def text_search(query: str, page_token: str | None = None) -> dict:
    """Google Places API – Text Search."""
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
    """Fetch phone number and website for a single place."""
    params = {
        "place_id": place_id,
        "fields": "formatted_phone_number,website",
        "key": API_KEY,
    }
    r = requests.get(PLACE_DETAILS_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("result", {})


def search_all_pages(query: str, max_pages: int = 3) -> list[dict]:
    """Paginate through results (up to max_pages × 20 = 60 results)."""
    all_places: list[dict] = []
    token = None
    for _ in range(max_pages):
        data = text_search(query, page_token=token)
        all_places.extend(data.get("results", []))
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(2)  # old API needs ~2s before next_page_token is valid
    return all_places


def enrich_with_details(places: list[dict]) -> list[dict]:
    """Add phone + website via Place Details for each result."""
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


# ── Dash app ─────────────────────────────────────────────────────────

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "LeadFinder"

app.layout = dbc.Container([
    # Header
    dbc.Row(dbc.Col(html.H2("LeadFinder", className="text-center my-3"))),
    dbc.Row(dbc.Col(html.P(
        "Trouve les entreprises Google Maps sans site web pour les démarcher.",
        className="text-center text-muted mb-4",
    ))),

    # Search form
    dbc.Row([
        dbc.Col(dbc.Input(id="input-city", placeholder="Ville (ex: Lyon)", type="text"), md=4),
        dbc.Col(dbc.Input(id="input-activity", placeholder="Activité (ex: plombier)", type="text"), md=4),
        dbc.Col(dbc.Button("Rechercher", id="btn-search", color="primary", className="w-100"), md=2),
        dbc.Col(dbc.Button("Export CSV", id="btn-csv", color="success", outline=True, className="w-100"), md=2),
    ], className="mb-3"),

    # Filters
    dbc.Row([
        dbc.Col(dbc.Checklist(
            id="filter-no-site",
            options=[{"label": " Sans site web uniquement", "value": "no_site"}],
            value=["no_site"],
            inline=True,
        ), md=4),
        dbc.Col(html.Div(id="result-count", className="text-end text-muted"), md=8),
    ], className="mb-3"),

    # Loading + results
    dcc.Loading(id="loading", children=[
        dash_table.DataTable(
            id="table-results",
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
    dcc.Store(id="store-data"),
    dcc.Download(id="download-csv"),

], fluid=True, className="py-3")


# ── Callbacks ────────────────────────────────────────────────────────

@callback(
    Output("store-data", "data"),
    Input("btn-search", "n_clicks"),
    State("input-city", "value"),
    State("input-activity", "value"),
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


@callback(
    Output("table-results", "data"),
    Output("table-results", "columns"),
    Output("table-results", "tooltip_data"),
    Output("result-count", "children"),
    Input("store-data", "data"),
    Input("filter-no-site", "value"),
)
def update_table(records, filters):
    if not records:
        return [], [], [], ""
    df = pd.DataFrame(records)

    total = len(df)
    if "no_site" in (filters or []):
        df = df[df["Site web"].fillna("").str.strip() == ""]
    shown = len(df)

    # Columns to show (hide raw URL, show as link text)
    visible_cols = ["Nom", "Adresse", "Téléphone", "Note", "Avis", "Site web", "Statut"]
    columns = [{"name": c, "id": c} for c in visible_cols]
    # Add Google Maps as a clickable column
    columns.append({"name": "Google Maps", "id": "Google Maps", "presentation": "markdown"})

    # Convert Google Maps URL to markdown link
    df["Google Maps"] = df["Google Maps"].apply(
        lambda u: f"[Voir]({u})" if u else ""
    )

    tooltip = [
        {col: {"value": str(row.get(col, "")), "type": "text"} for col in visible_cols}
        for row in df.to_dict("records")
    ]

    count_text = f"{shown} résultats affichés / {total} trouvés au total"
    return df.to_dict("records"), columns, tooltip, count_text


@callback(
    Output("download-csv", "data"),
    Input("btn-csv", "n_clicks"),
    State("table-results", "data"),
    prevent_initial_call=True,
)
def export_csv(n, records):
    if not records:
        return no_update
    df = pd.DataFrame(records)
    return dcc.send_data_frame(df.to_csv, "leads.csv", index=False)


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=8060)
