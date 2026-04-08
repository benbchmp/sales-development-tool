# Cold Calls Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une page Cold Calls Analytics à LeadFinder avec un tracker d'appels en live et des KPI/graphiques, les données persistées dans un fichier JSON local.

**Architecture:** L'app Dash actuelle (`app.py`) est refactorisée pour gérer le routing multi-pages via `dcc.Location`. Le contenu existant est déplacé dans `pages/leadfinder.py`. La nouvelle page `pages/cold_calls.py` contient le tracker et les analytics. Une navbar commune est définie dans `app.py`.

**Tech Stack:** Python 3.12, Dash 4.0, Dash Bootstrap Components (thème DARKLY), Plotly, JSON fichier local.

---

### Task 1 : Créer `pages/leadfinder.py` — déplacer le contenu existant

**Files:**
- Create: `pages/__init__.py`
- Create: `pages/leadfinder.py`
- Modify: `app.py` (vider progressivement dans les tâches suivantes)

- [ ] **Step 1 : Créer le dossier pages et `__init__.py`**

```bash
cd C:/Users/benjb/python/websites
mkdir pages
```

Créer `pages/__init__.py` vide :
```python
```

- [ ] **Step 2 : Créer `pages/leadfinder.py`**

Copier tout le contenu de `app.py` entre les imports et le `if __name__ == "__main__"`, et l'envelopper dans des fonctions `layout()` et `register_callbacks(app)`.

Contenu complet de `pages/leadfinder.py` :

```python
"""
LeadFinder – page de recherche de leads Google Maps
"""

import os, time, requests, pandas as pd
from dotenv import load_dotenv
from dash import html, dcc, dash_table, callback, Output, Input, State, no_update, callback_context
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
                placeholder="Sélectionne une activité...",
                clearable=True,
                searchable=True,
                style={"color": "#000"},
            ), md=4),
            dbc.Col(dbc.Button("Rechercher", id="lf-btn-search", color="primary", className="w-100"), md=2),
            dbc.Col(dbc.Button("Export CSV", id="lf-btn-csv", color="success", outline=True, className="w-100"), md=2),
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
```

- [ ] **Step 3 : Vérifier que le fichier est bien créé**

```bash
cd C:/Users/benjb/python/websites && python -c "import pages.leadfinder; print('OK')"
```
Expected : `OK`

- [ ] **Step 4 : Commit**

```bash
cd C:/Users/benjb/python/websites
git add pages/__init__.py pages/leadfinder.py
git commit -m "refactor: extract leadfinder page to pages/leadfinder.py"
```

---

### Task 2 : Créer `pages/cold_calls.py` — layout + callbacks

**Files:**
- Create: `pages/cold_calls.py`

- [ ] **Step 1 : Créer `pages/cold_calls.py`**

Contenu complet :

```python
"""
Cold Calls – tracker d'appels en live + analytics
Données persistées dans cold_calls_data.json
"""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cold_calls_data.json")

OBJECTION_OPTIONS = [
    "Redirigé vers email",
    "Pas d'intérêt",
    "Pas de budget",
    "Pas le temps",
    "Pas le bon moment",
    "Déjà équipé",
    "Pas le décideur",
]

RESULT_LABELS = {
    "pitch_fail": "Recalé au pitch",
    "objection": "Objection",
    "success": "Succès",
}

RESULT_COLORS = {
    "pitch_fail": "#dc3545",
    "objection": "#fd7e14",
    "success": "#28a745",
}

# ── Data helpers ─────────────────────────────────────────────────────

def load_calls() -> list[dict]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_calls(calls: list[dict]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(calls, f, ensure_ascii=False, indent=2)


def add_call(result: str, detail: str = "") -> None:
    calls = load_calls()
    calls.append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "result": result,
        "detail": detail,
    })
    save_calls(calls)


def undo_last_call() -> bool:
    """Remove the last call. Returns True if something was removed."""
    calls = load_calls()
    if not calls:
        return False
    calls.pop()
    save_calls(calls)
    return True


def filter_by_period(calls: list[dict], period: str) -> list[dict]:
    if period == "all":
        return calls
    days = {"1j": 1, "3j": 3, "7j": 7, "1m": 30}[period]
    cutoff = datetime.now() - timedelta(days=days)
    return [c for c in calls if datetime.fromisoformat(c["timestamp"]) >= cutoff]


def calls_to_df(calls: list[dict]) -> pd.DataFrame:
    if not calls:
        return pd.DataFrame(columns=["timestamp", "result", "detail"])
    df = pd.DataFrame(calls)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def compute_kpis(df: pd.DataFrame) -> dict:
    total = len(df)
    success = int((df["result"] == "success").sum()) if total else 0
    pitch_fail = int((df["result"] == "pitch_fail").sum()) if total else 0
    objections = int((df["result"] == "objection").sum()) if total else 0
    conversion = round(success / total * 100, 1) if total else 0.0
    return {
        "total": total,
        "success": success,
        "pitch_fail": pitch_fail,
        "objections": objections,
        "conversion": conversion,
    }


def compute_today_stats(all_calls: list[dict]) -> dict:
    today = datetime.now().date()
    today_calls = [c for c in all_calls if datetime.fromisoformat(c["timestamp"]).date() == today]
    total_today = len(today_calls)
    success_today = sum(1 for c in today_calls if c["result"] == "success")
    conversion_today = round(success_today / total_today * 100, 1) if total_today else 0.0

    # Objection la plus fréquente du jour
    obj_today = [c["detail"] for c in today_calls if c["result"] == "objection" and c.get("detail")]
    top_obj = max(set(obj_today), key=obj_today.count) if obj_today else None
    top_obj_count = obj_today.count(top_obj) if top_obj else 0

    last_call = all_calls[-1] if all_calls else None
    last_label = ""
    if last_call:
        r = last_call["result"]
        d = last_call.get("detail", "")
        label = RESULT_LABELS.get(r, r)
        last_label = f"{label} — {d}" if d else label
        ts = datetime.fromisoformat(last_call["timestamp"]).strftime("%H:%M")
        last_label = f"{last_label} ({ts})"

    return {
        "total_today": total_today,
        "conversion_today": conversion_today,
        "last_call": last_label,
        "top_objection": f"{top_obj} ({top_obj_count}×)" if top_obj else "—",
    }


# ── Layout ───────────────────────────────────────────────────────────

def layout():
    return dbc.Container([

        # ── Section 1 : KPI & Analytics ─────────────────────────────
        html.H5("KPI & Analytics", className="mt-3 mb-3 text-light"),

        # Filtre de période
        dbc.Row([
            dbc.Col(
                dbc.RadioItems(
                    id="cc-period",
                    options=[
                        {"label": "1J", "value": "1j"},
                        {"label": "3J", "value": "3j"},
                        {"label": "7J", "value": "7j"},
                        {"label": "1M", "value": "1m"},
                        {"label": "All", "value": "all"},
                    ],
                    value="all",
                    inline=True,
                    className="mb-3",
                    inputClassName="me-1",
                ),
                className="text-end"
            ),
        ]),

        # Bloc KPI
        dbc.Row(id="cc-kpi-cards", className="mb-4 g-3"),

        # Graphiques
        dbc.Row([
            dbc.Col(dcc.Graph(id="cc-graph-line", config={"displayModeBar": False}), md=7),
            dbc.Col(dcc.Graph(id="cc-graph-pie", config={"displayModeBar": False}), md=5),
        ], className="mb-4"),

        html.Hr(style={"borderColor": "#444"}),

        # ── Section 2 : Call Tracker ─────────────────────────────────
        html.H5("Call Tracker", className="mb-3 text-light"),

        # Boutons principaux
        dbc.Row([
            dbc.Col(dbc.Button(
                "✗ Recalé au pitch",
                id="cc-btn-pitch-fail",
                color="danger",
                size="lg",
                className="w-100 py-3 fw-bold",
            ), md=4),
            dbc.Col(dbc.Button(
                "⚡ Objection",
                id="cc-btn-objection",
                color="warning",
                size="lg",
                className="w-100 py-3 fw-bold",
            ), md=4),
            dbc.Col(dbc.Button(
                "✓ Succès — RDV booké",
                id="cc-btn-success",
                color="success",
                size="lg",
                className="w-100 py-3 fw-bold",
            ), md=4),
        ], className="mb-3"),

        # Sous-menu objections (caché par défaut)
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody([
                    html.P("Choisir le type d'objection :", className="text-muted mb-2"),
                    dbc.Row([
                        dbc.Col(dbc.Button(
                            label,
                            id={"type": "cc-obj-btn", "index": label},
                            color="warning",
                            outline=True,
                            size="sm",
                            className="w-100 mb-2",
                        ), md=6)
                        for label in OBJECTION_OPTIONS
                    ]),
                ]),
                style={"backgroundColor": "#2a2a2a", "border": "1px solid #fd7e14"},
            ),
            id="cc-collapse-objection",
            is_open=False,
        ),

        # Bouton annuler
        dbc.Row([
            dbc.Col(dbc.Button(
                "↩ Annuler le dernier appel",
                id="cc-btn-undo",
                color="secondary",
                outline=True,
                size="sm",
            ), className="text-center mt-2 mb-4"),
        ]),

        # Feedback action
        dbc.Alert(id="cc-action-feedback", is_open=False, duration=2000, className="text-center"),

        # Mini-stats session
        dbc.Card(
            dbc.CardBody([
                html.H6("Aujourd'hui", className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col(html.Div([
                        html.Div(id="cc-today-total", className="fs-4 fw-bold text-light"),
                        html.Small("Appels", className="text-muted"),
                    ]), md=3, className="text-center"),
                    dbc.Col(html.Div([
                        html.Div(id="cc-today-conversion", className="fs-4 fw-bold text-success"),
                        html.Small("Taux de succès", className="text-muted"),
                    ]), md=3, className="text-center"),
                    dbc.Col(html.Div([
                        html.Div(id="cc-today-last", className="fs-6 text-light"),
                        html.Small("Dernier résultat", className="text-muted"),
                    ]), md=3, className="text-center"),
                    dbc.Col(html.Div([
                        html.Div(id="cc-today-top-obj", className="fs-6 text-warning"),
                        html.Small("Objection principale", className="text-muted"),
                    ]), md=3, className="text-center"),
                ]),
            ]),
            style={"backgroundColor": "#1e1e1e", "border": "1px solid #444"},
        ),

        # Refresh interval (toutes les 5s pour garder les stats à jour)
        dcc.Interval(id="cc-interval", interval=5000, n_intervals=0),

        # Store pour trigger refresh après action
        dcc.Store(id="cc-trigger", data=0),

    ], fluid=True)


# ── Callbacks ────────────────────────────────────────────────────────

def register_callbacks(app):

    # Toggle sous-menu objections
    @app.callback(
        Output("cc-collapse-objection", "is_open"),
        Input("cc-btn-objection", "n_clicks"),
        State("cc-collapse-objection", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_objection_menu(n, is_open):
        return not is_open

    # Enregistrer un appel (pitch_fail, success, ou objection sous-cat)
    @app.callback(
        Output("cc-trigger", "data"),
        Output("cc-action-feedback", "children"),
        Output("cc-action-feedback", "color"),
        Output("cc-action-feedback", "is_open"),
        Output("cc-collapse-objection", "is_open", allow_duplicate=True),
        Input("cc-btn-pitch-fail", "n_clicks"),
        Input("cc-btn-success", "n_clicks"),
        Input("cc-btn-undo", "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[0]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[1]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[2]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[3]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[4]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[5]}, "n_clicks"),
        Input({"type": "cc-obj-btn", "index": OBJECTION_OPTIONS[6]}, "n_clicks"),
        State("cc-trigger", "data"),
        prevent_initial_call=True,
    )
    def handle_action(*args):
        trigger_val = args[-1]
        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update, no_update, no_update

        btn_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if btn_id == "cc-btn-pitch-fail":
            add_call("pitch_fail")
            return trigger_val + 1, "Recalé au pitch enregistré", "danger", True, False

        elif btn_id == "cc-btn-success":
            add_call("success")
            return trigger_val + 1, "Succès — RDV booké enregistré !", "success", True, False

        elif btn_id == "cc-btn-undo":
            removed = undo_last_call()
            msg = "Dernier appel annulé" if removed else "Aucun appel à annuler"
            return trigger_val + 1, msg, "secondary", True, False

        else:
            # Objection sous-catégorie — extraire le label du dict id
            try:
                id_dict = json.loads(btn_id)
                detail = id_dict.get("index", "")
            except (json.JSONDecodeError, AttributeError):
                detail = ""
            add_call("objection", detail)
            return trigger_val + 1, f"Objection : {detail}", "warning", True, False

    # Mettre à jour KPIs, graphiques et mini-stats
    @app.callback(
        Output("cc-kpi-cards", "children"),
        Output("cc-graph-line", "figure"),
        Output("cc-graph-pie", "figure"),
        Output("cc-today-total", "children"),
        Output("cc-today-conversion", "children"),
        Output("cc-today-last", "children"),
        Output("cc-today-top-obj", "children"),
        Input("cc-period", "value"),
        Input("cc-trigger", "data"),
        Input("cc-interval", "n_intervals"),
    )
    def update_analytics(period, _trigger, _interval):
        all_calls = load_calls()
        filtered = filter_by_period(all_calls, period)
        df = calls_to_df(filtered)
        kpis = compute_kpis(df)
        today_stats = compute_today_stats(all_calls)

        # KPI cards
        kpi_cards = [
            dbc.Col(_kpi_card("Total", kpis["total"], "#ffffff"), md=True),
            dbc.Col(_kpi_card("Succès", kpis["success"], "#28a745"), md=True),
            dbc.Col(_kpi_card("Recalés", kpis["pitch_fail"], "#dc3545"), md=True),
            dbc.Col(_kpi_card("Objections", kpis["objections"], "#fd7e14"), md=True),
            dbc.Col(_kpi_card("Conversion", f"{kpis['conversion']}%", "#17a2b8"), md=True),
        ]

        # Courbe appels par jour
        if not df.empty:
            df_day = df.copy()
            df_day["date"] = df_day["timestamp"].dt.date
            by_day = df_day.groupby("date").size().reset_index(name="appels")
            fig_line = px.line(
                by_day, x="date", y="appels",
                markers=True,
                labels={"date": "", "appels": "Appels"},
                template="plotly_dark",
            )
            fig_line.update_traces(line_color="#4dabf7", marker_color="#4dabf7")
        else:
            fig_line = go.Figure()
            fig_line.update_layout(
                template="plotly_dark",
                annotations=[{"text": "Aucune donnée", "showarrow": False, "font": {"color": "#888"}}],
            )
        fig_line.update_layout(
            plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e",
            margin=dict(l=20, r=20, t=30, b=20),
            title={"text": "Appels par jour", "font": {"color": "#ccc", "size": 13}},
        )

        # Camembert répartition
        if not df.empty:
            pie_data = df["result"].map(RESULT_LABELS).value_counts().reset_index()
            pie_data.columns = ["Résultat", "count"]
            color_map = {v: RESULT_COLORS[k] for k, v in RESULT_LABELS.items()}
            fig_pie = px.pie(
                pie_data, names="Résultat", values="count",
                color="Résultat", color_discrete_map=color_map,
                template="plotly_dark",
                hole=0.4,
            )
            fig_pie.update_traces(textfont_color="#fff")
        else:
            fig_pie = go.Figure()
            fig_pie.update_layout(
                template="plotly_dark",
                annotations=[{"text": "Aucune donnée", "showarrow": False, "font": {"color": "#888"}}],
            )
        fig_pie.update_layout(
            plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e",
            margin=dict(l=10, r=10, t=30, b=10),
            title={"text": "Répartition", "font": {"color": "#ccc", "size": 13}},
            legend={"font": {"color": "#ccc"}},
        )

        return (
            kpi_cards,
            fig_line,
            fig_pie,
            str(today_stats["total_today"]),
            f"{today_stats['conversion_today']}%",
            today_stats["last_call"] or "—",
            today_stats["top_objection"],
        )


def _kpi_card(label: str, value, color: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody([
            html.Div(str(value), style={"fontSize": "2rem", "fontWeight": "bold", "color": color}),
            html.Small(label, className="text-muted"),
        ], className="text-center p-2"),
        style={"backgroundColor": "#1e1e1e", "border": "1px solid #444"},
    )
```

- [ ] **Step 2 : Vérifier que le module s'importe sans erreur**

```bash
cd C:/Users/benjb/python/websites && python -c "import pages.cold_calls; print('OK')"
```
Expected : `OK`

- [ ] **Step 3 : Commit**

```bash
cd C:/Users/benjb/python/websites
git add pages/cold_calls.py
git commit -m "feat: add cold calls tracker and analytics page"
```

---

### Task 3 : Refactoriser `app.py` — routing multi-pages + navbar

**Files:**
- Modify: `app.py` (remplacement complet)

- [ ] **Step 1 : Remplacer `app.py` par la version multi-pages**

Remplacer tout le contenu de `app.py` par :

```python
"""
LeadFinder – Entry point
Routing multi-pages : / → leadfinder, /cold-calls → cold calls analytics
"""

import os
from dotenv import load_dotenv
from dash import Dash, html, dcc, Output, Input
import dash_bootstrap_components as dbc

import pages.leadfinder as leadfinder
import pages.cold_calls as cold_calls

load_dotenv()

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True,
)
app.title = "LeadFinder"
server = app.server  # pour gunicorn

leadfinder.register_callbacks(app)
cold_calls.register_callbacks(app)

# ── Navbar ───────────────────────────────────────────────────────────

def _navbar(active_path: str) -> dbc.Container:
    return dbc.Container([
        dbc.Row(dbc.Col(html.Img(
            src="/assets/eagle.png",
            style={
                "height": "60px",
                "display": "block",
                "margin": "16px auto 8px auto",
                "filter": "invert(1)",
                "mixBlendMode": "screen",
            }
        ))),
        dbc.Row(dbc.Col(
            dbc.ButtonGroup([
                dbc.Button(
                    "LeadFinder",
                    href="/",
                    external_link=False,
                    color="primary",
                    outline=active_path != "/",
                    id="nav-leadfinder",
                ),
                dbc.Button(
                    "Cold Calls",
                    href="/cold-calls",
                    external_link=False,
                    color="primary",
                    outline=active_path != "/cold-calls",
                    id="nav-coldcalls",
                ),
            ], className="d-flex justify-content-center mb-3"),
        )),
    ], fluid=True)


# ── App layout ───────────────────────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="navbar-container"),
    html.Div(id="page-content"),
])


@app.callback(
    Output("navbar-container", "children"),
    Output("page-content", "children"),
    Input("url", "pathname"),
)
def route(pathname):
    if pathname == "/cold-calls":
        return _navbar("/cold-calls"), cold_calls.layout()
    return _navbar("/"), leadfinder.layout()


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8060))
    app.run(debug=True, port=port)
```

- [ ] **Step 2 : Lancer l'app et vérifier que les 2 pages fonctionnent**

```bash
cd C:/Users/benjb/python/websites && python app.py
```

Ouvrir http://127.0.0.1:8060 et vérifier :
- La page LeadFinder s'affiche (logo + formulaire de recherche)
- Le bouton "Cold Calls" redirige vers `/cold-calls`
- La page Cold Calls s'affiche (KPI + tracker)
- Le bouton "Recalé au pitch" enregistre un appel et met à jour les stats
- Le bouton "Annuler" supprime le dernier appel
- Le menu Objection s'ouvre et une sous-catégorie s'enregistre correctement
- Le filtre de période filtre les graphiques
- Le bouton "LeadFinder" ramène vers `/`

- [ ] **Step 3 : Commit final**

```bash
cd C:/Users/benjb/python/websites
git add app.py
git commit -m "feat: refactor app.py for multi-page routing with navbar"
```
