"""
LeadFinder – page de recherche de leads Google Maps
"""

import io, os, re, time, requests, pandas as pd
from dotenv import load_dotenv
from dash import html, dcc, Output, Input, State, no_update, ALL, callback_context
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
                html.I(className="bi bi-file-earmark-excel", style={"fontSize": "1.1rem"}),
                id="lf-btn-csv",
                color="success",
                outline=True,
                title="Exporter en Excel",
                style={"padding": "6px 12px"},
            ), md="auto", className="d-flex align-items-center"),
        ], className="mb-3"),

        # Filters row
        dbc.Row([
            dbc.Col(dbc.Checklist(
                id="lf-filter-no-site",
                options=[{"label": " Sans site web uniquement", "value": "no_site"}],
                value=["no_site"],
                inline=True,
            ), md="auto"),
            dbc.Col(dbc.Button(
                [html.I(className="bi bi-funnel me-1"), "Filtres"],
                id="lf-btn-toggle-filters",
                color="secondary", outline=True, size="sm",
            ), md="auto"),
            dbc.Col(dbc.DropdownMenu(
                label=html.Span([html.I(className="bi bi-layout-three-columns me-1"), "Colonnes"]),
                children=[
                    dbc.Checklist(
                        id="lf-col-visibility",
                        options=[{"label": c, "value": c} for c in ["Nom", "Localisation", "Téléphone", "Note", "Avis", "Site web", "Google Maps"]],
                        value=["Nom", "Localisation", "Téléphone", "Note", "Avis", "Site web", "Google Maps"],
                        style={"padding": "8px 12px"},
                    )
                ],
                color="secondary", size="sm",
                toggle_style={"fontSize": "0.85rem"},
            ), md="auto"),
            dbc.Col(html.Div(id="lf-result-count", className="text-muted"), md=True, className="text-end d-flex align-items-center justify-content-end"),
        ], className="mb-2 g-2", align="center"),

        # Collapse filtres par colonne
        dbc.Collapse(
            dbc.Card(dbc.CardBody(
                html.Div(id="lf-filter-inputs-container"),
                style={"padding": "8px"},
            ), style={"backgroundColor": "#1e1e1e", "border": "1px solid #444"}),
            id="lf-collapse-filters",
            is_open=False,
            className="mb-2",
        ),

        # Loading + results
        dcc.Loading(id="lf-loading", children=[
            html.Div(id="lf-table-results"),
        ], type="circle"),

        # Hidden stores
        dcc.Store(id="lf-store-data"),
        dcc.Store(id="lf-col-filters", data={}),
        dcc.Download(id="lf-download-csv"),
        dcc.Store(id="lf-pending-prospect", data=None),

        # Feedback ajout prospect
        dbc.Alert(id="lf-prospect-feedback", is_open=False, duration=2500, className="text-center mt-2"),

        # Modal ajout aux prospects
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="lf-modal-title")),
            dbc.ModalBody([
                html.P("Ajouter à un groupe existant :", className="text-muted mb-2"),
                html.Div(id="lf-modal-groups"),
                html.Hr(style={"borderColor": "#444"}),
                html.P("Ou créer un nouveau groupe :", className="text-muted mb-2"),
                dbc.Row([
                    dbc.Col(dbc.Input(id="lf-modal-new-group", placeholder="Nom du groupe...", size="sm"), md=8),
                    dbc.Col(dbc.Button("Créer & Ajouter", id="lf-modal-btn-create", color="primary", size="sm"), width="auto"),
                ], className="g-2", align="center"),
            ]),
        ], id="lf-prospect-modal", is_open=False),

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

    ALL_COLS = ["Nom", "Localisation", "Téléphone", "Note", "Avis", "Site web", "Google Maps"]

    # Toggle panneau filtres
    @app.callback(
        Output("lf-collapse-filters", "is_open"),
        Output("lf-filter-inputs-container", "children"),
        Input("lf-btn-toggle-filters", "n_clicks"),
        State("lf-collapse-filters", "is_open"),
        State("lf-col-visibility", "value"),
        State("lf-col-filters", "data"),
        prevent_initial_call=True,
    )
    def toggle_filters(n, is_open, visible_cols, current_filters):
        visible = visible_cols or ALL_COLS
        inputs = dbc.Row([
            dbc.Col([
                html.Small(c, className="text-muted d-block mb-1"),
                dbc.Input(
                    id=f"lf-filter-{c.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e').replace('ê', 'e')}",
                    value=current_filters.get(c, ""),
                    placeholder=f"Filtrer {c}...",
                    size="sm",
                    debounce=True,
                    style={"backgroundColor": "#2a2a2a", "color": "#ddd", "border": "1px solid #555"},
                ),
            ], md=True)
            for c in visible if c != "Google Maps"
        ], className="g-2")
        return not is_open, inputs

    # Agréger les filtres colonnes dans le Store
    @app.callback(
        Output("lf-col-filters", "data"),
        Input("lf-filter-nom", "value"),
        Input("lf-filter-localisation", "value"),
        Input("lf-filter-telephone", "value"),
        Input("lf-filter-note", "value"),
        Input("lf-filter-avis", "value"),
        Input("lf-filter-site-web", "value"),
        prevent_initial_call=True,
    )
    def aggregate_filters(nom, loc, tel, note, avis, site):
        return {
            "Nom": nom or "",
            "Localisation": loc or "",
            "Téléphone": tel or "",
            "Note": note or "",
            "Avis": avis or "",
            "Site web": site or "",
        }

    @app.callback(
        Output("lf-table-results", "children"),
        Output("lf-result-count", "children"),
        Input("lf-store-data", "data"),
        Input("lf-filter-no-site", "value"),
        Input("lf-col-filters", "data"),
        Input("lf-col-visibility", "value"),
    )
    def update_table(records, filters, col_filters, visible_cols):
        if not records:
            return "", ""
        df = pd.DataFrame(records)

        total = len(df)
        if "no_site" in (filters or []):
            df = df[df["Site web"].fillna("").str.strip() == ""]

        # Appliquer filtres par colonne
        for col, val in (col_filters or {}).items():
            if val and col in df.columns:
                df = df[df[col].astype(str).str.contains(val, case=False, na=False)]

        shown = len(df)
        cols = [c for c in ALL_COLS if c in (visible_cols or ALL_COLS)]

        header = html.Thead(html.Tr(
            [html.Th("", style={"padding": "8px 6px", "width": "32px"})] +
            [html.Th(c, style={"padding": "8px 10px", "whiteSpace": "nowrap"}) for c in cols]
        ))

        rows = []
        for i, row in enumerate(df.reset_index(drop=True).to_dict("records")):
            cells = [html.Td(
                dbc.Button(
                    html.I(className="bi bi-plus-circle"),
                    id={"type": "lf-add-prospect-btn", "idx": i},
                    color="success", outline=True, size="sm",
                    title="Ajouter aux prospects",
                    style={"padding": "2px 6px"},
                    n_clicks=0,
                ),
                style={"padding": "4px 6px"},
            )]
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
            bordered=True, dark=True, hover=False, size="sm",
            style={"fontSize": "0.85rem"},
        )

        count_text = f"{shown} résultats affichés / {total} trouvés au total"
        return table, count_text

    @app.callback(
        Output("lf-download-csv", "data"),
        Input("lf-btn-csv", "n_clicks"),
        State("lf-store-data", "data"),
        State("lf-filter-no-site", "value"),
        State("lf-col-filters", "data"),
        State("lf-col-visibility", "value"),
        prevent_initial_call=True,
    )
    def export_excel(n, records, filters, col_filters, visible_cols):
        if not records:
            return no_update
        df = pd.DataFrame(records)
        # Appliquer les mêmes filtres que le tableau affiché
        if "no_site" in (filters or []):
            df = df[df["Site web"].fillna("").str.strip() == ""]
        for col, val in (col_filters or {}).items():
            if val and col in df.columns:
                df = df[df[col].astype(str).str.contains(val, case=False, na=False)]
        cols = [c for c in ALL_COLS if c in (visible_cols or ALL_COLS)]
        df = df[[c for c in cols if c in df.columns]]

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Leads")
            ws = writer.sheets["Leads"]
            # Largeurs automatiques
            for col_cells in ws.columns:
                max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 4, 50)
        buf.seek(0)
        return dcc.send_bytes(buf.read, "leads.xlsx")

    # Ouvrir le modal ajout prospect
    @app.callback(
        Output("lf-prospect-modal", "is_open"),
        Output("lf-modal-title", "children"),
        Output("lf-modal-groups", "children"),
        Output("lf-pending-prospect", "data"),
        Input({"type": "lf-add-prospect-btn", "idx": ALL}, "n_clicks"),
        State("lf-store-data", "data"),
        State("lf-filter-no-site", "value"),
        prevent_initial_call=True,
    )
    def open_prospect_modal(n_clicks_list, records, filters):
        from pages.prospects import get_groups, add_prospect_to_group
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            return no_update, no_update, no_update, no_update

        triggered_id = ctx.triggered[0]["prop_id"]
        import json as _json
        try:
            idx = _json.loads(triggered_id.replace(".n_clicks", ""))["idx"]
        except Exception:
            return no_update, no_update, no_update, no_update

        if not records:
            return no_update, no_update, no_update, no_update

        df = pd.DataFrame(records)
        if "no_site" in (filters or []):
            df = df[df["Site web"].fillna("").str.strip() == ""]
        df = df.reset_index(drop=True)

        if idx >= len(df):
            return no_update, no_update, no_update, no_update

        row = df.iloc[idx].to_dict()
        groups = get_groups()

        # Vérifier lesquels contiennent déjà ce prospect
        already_in = set()
        for g in groups:
            for p in g["prospects"]:
                if p["Nom"] == row.get("Nom") and p.get("Localisation") == row.get("Localisation"):
                    already_in.add(g["id"])

        if groups:
            group_btns = [
                dbc.Button(
                    [g["name"], html.Span(" (déjà ajouté)", className="text-muted ms-1 small") if g["id"] in already_in else ""],
                    id={"type": "lf-modal-group-btn", "gid": g["id"]},
                    color="secondary" if g["id"] in already_in else "primary",
                    outline=True,
                    disabled=g["id"] in already_in,
                    className="me-2 mb-2",
                    n_clicks=0,
                )
                for g in groups
            ]
        else:
            group_btns = [html.P("Aucun groupe existant.", className="text-muted")]

        return True, f"Ajouter : {row.get('Nom', '')}", group_btns, row

    # Ajouter au groupe existant via modal
    @app.callback(
        Output("lf-prospect-modal", "is_open", allow_duplicate=True),
        Output("lf-prospect-feedback", "children"),
        Output("lf-prospect-feedback", "color"),
        Output("lf-prospect-feedback", "is_open"),
        Input({"type": "lf-modal-group-btn", "gid": ALL}, "n_clicks"),
        State("lf-pending-prospect", "data"),
        prevent_initial_call=True,
    )
    def add_to_existing_group(n_clicks_list, prospect):
        from pages.prospects import get_groups, add_prospect_to_group
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            return no_update, no_update, no_update, no_update
        import json as _json
        triggered_id = ctx.triggered[0]["prop_id"].replace(".n_clicks", "")
        try:
            gid = _json.loads(triggered_id)["gid"]
        except Exception:
            return no_update, no_update, no_update, no_update

        groups = get_groups()
        group_name = next((g["name"] for g in groups if g["id"] == gid), "?")
        add_prospect_to_group(gid, prospect)
        return False, f"✓ Ajouté à « {group_name} »", "success", True

    # Créer groupe et ajouter via modal
    @app.callback(
        Output("lf-prospect-modal", "is_open", allow_duplicate=True),
        Output("lf-prospect-feedback", "children", allow_duplicate=True),
        Output("lf-prospect-feedback", "color", allow_duplicate=True),
        Output("lf-prospect-feedback", "is_open", allow_duplicate=True),
        Output("lf-modal-new-group", "value"),
        Input("lf-modal-btn-create", "n_clicks"),
        State("lf-modal-new-group", "value"),
        State("lf-pending-prospect", "data"),
        prevent_initial_call=True,
    )
    def create_group_and_add(n, group_name, prospect):
        from pages.prospects import add_group, add_prospect_to_group
        if not group_name or not group_name.strip() or not prospect:
            return no_update, "Saisis un nom de groupe.", "warning", True, no_update
        gid = add_group(group_name)
        add_prospect_to_group(gid, prospect)
        return False, f"✓ Groupe « {group_name.strip()} » créé et prospect ajouté.", "success", True, ""
