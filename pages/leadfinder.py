"""
LeadFinder – page de recherche de leads Google Maps
"""

import os, re, time, requests, pandas as pd
from dotenv import load_dotenv
from dash import html, dcc, Output, Input, State, no_update
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


def _extract_city_postal(address: str) -> str:
    """Extract 'VILLE, 00000' from a French Google Maps address."""
    # Typical format: "12 Rue X, 75011 Paris, France"
    m = re.search(r"(\d{5})\s+([^,]+)", address)
    if m:
        return f"{m.group(2).strip().upper()}, {m.group(1)}"
    # Fallback: return last meaningful part before country
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        return parts[-2].upper()
    return address.upper()


def places_to_df(places: list[dict]) -> pd.DataFrame:
    rows = []
    for p in places:
        place_id = p.get("place_id", "")
        rows.append({
            "Nom": p.get("name", ""),
            "Localisation": _extract_city_postal(p.get("formatted_address", "")),
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
            dbc.Col(html.Div([
                dbc.Input(
                    id="lf-input-activity",
                    placeholder="Ex: Plombier, Architecte, Laveur de vitres...",
                    type="text",
                    list="lf-activity-suggestions",
                ),
                html.Datalist(
                    id="lf-activity-suggestions",
                    children=[html.Option(value=o["value"]) for o in ACTIVITY_OPTIONS if not o.get("disabled")],
                ),
            ]), md=4),
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
            html.Div(id="lf-table-results"),
        ], type="circle"),

        # Hidden store for full data
        dcc.Store(id="lf-store-data"),
        dcc.Download(id="lf-download-csv"),

    ], fluid=True)


# ── Callbacks ────────────────────────────────────────────────────────

def register_callbacks(app):
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
        Output("lf-table-results", "children"),
        Output("lf-result-count", "children"),
        Input("lf-store-data", "data"),
        Input("lf-filter-no-site", "value"),
    )
    def update_table(records, filters):
        if not records:
            return "", ""
        df = pd.DataFrame(records)

        total = len(df)
        if "no_site" in (filters or []):
            df = df[df["Site web"].fillna("").str.strip() == ""]
        shown = len(df)

        cols = ["Nom", "Localisation", "Téléphone", "Note", "Avis", "Site web", "Statut", "Google Maps"]

        header = html.Thead(html.Tr([html.Th(c, style={"padding": "8px 10px", "whiteSpace": "nowrap"}) for c in cols]))

        rows = []
        for row in df.to_dict("records"):
            cells = []
            for c in cols:
                val = str(row.get(c, ""))
                if c == "Google Maps" and val:
                    cells.append(html.Td(html.A("Voir", href=val, target="_blank", style={"color": "#4dabf7"}), style={"padding": "6px 10px"}))
                elif c == "Site web" and val:
                    cells.append(html.Td(html.A(val, href=val, target="_blank", style={"color": "#4dabf7", "wordBreak": "break-all"}), style={"padding": "6px 10px", "maxWidth": "200px"}))
                else:
                    bg = "#1a3a1a" if c == "Nom" and not row.get("Site web", "").strip() else "transparent"
                    cells.append(html.Td(val, style={"padding": "6px 10px", "backgroundColor": bg}))
            rows.append(html.Tr(cells))

        table = dbc.Table(
            [header, html.Tbody(rows)],
            bordered=True,
            dark=True,
            hover=False,
            size="sm",
            style={"fontSize": "0.85rem"},
        )

        count_text = f"{shown} résultats affichés / {total} trouvés au total"
        return table, count_text

    @app.callback(
        Output("lf-download-csv", "data"),
        Input("lf-btn-csv", "n_clicks"),
        State("lf-store-data", "data"),
        prevent_initial_call=True,
    )
    def export_csv(n, records):
        if not records:
            return no_update
        df = pd.DataFrame(records)
        return dcc.send_data_frame(df.to_csv, "leads.csv", index=False)
