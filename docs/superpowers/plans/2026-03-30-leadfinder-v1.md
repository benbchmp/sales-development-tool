# LeadFinder V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dash web app that searches Google Places API for businesses without websites in a given French city, displays them in a filterable table, and exports results to Excel.

**Architecture:** Three-layer architecture: Dash UI (layout + callbacks) → business logic (connectors + cache) → data storage (SQLite). Google Places connector handles geocoding + nearby search + place details. SQLite cache avoids redundant API calls and prepares the foundation for a future CRM.

**Tech Stack:** Python 3.x, Dash 4.0.0, dash-bootstrap-components (DARKLY), requests, sqlite3 (stdlib), openpyxl, python-dotenv, pytest

---

### Task 1: Project setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `connectors/__init__.py`
- Create: `utils/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
dash==4.0.0
dash-bootstrap-components==1.6.0
requests==2.31.0
openpyxl==3.1.2
python-dotenv==1.0.0
pytest==8.0.0
```

- [ ] **Step 2: Create .env.example**

```
GOOGLE_API_KEY=your_google_api_key_here
```

- [ ] **Step 3: Create .gitignore**

```
.env
cache.db
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: Create empty __init__.py files**

```bash
touch connectors/__init__.py utils/__init__.py tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore connectors/__init__.py utils/__init__.py tests/__init__.py
git commit -m "feat: project setup and dependencies"
```

---

### Task 2: Database layer (SQLite)

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_database.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'database'`

- [ ] **Step 3: Implement database.py**

```python
# database.py
import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "cache.db"):
        self.db_path = db_path
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
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

    def upsert_place(self, place: dict):
        with self._connect() as conn:
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
            """, {**place, "fetched_at": datetime.utcnow().isoformat()})

    def get_places_without_website(self, place_type: str = None) -> list[dict]:
        with self._connect() as conn:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: SQLite database layer with upsert and website filter"
```

---

### Task 3: Google Places connector

**Files:**
- Create: `connectors/google_places.py`
- Create: `tests/test_google_places.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_google_places.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'connectors.google_places'`

- [ ] **Step 3: Implement connectors/google_places.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_google_places.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add connectors/google_places.py tests/test_google_places.py
git commit -m "feat: Google Places connector with geocoding, nearby search, place details"
```

---

### Task 4: Export Excel

**Files:**
- Create: `utils/export.py`
- Create: `tests/test_export.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_export.py
import os
from openpyxl import load_workbook
from utils.export import generate_excel

SAMPLE_LEADS = [
    {
        "name": "Dupont Plomberie", "type": "plumber", "phone": "0601020304",
        "address": "12 rue de la Paix, 69001 Lyon", "rating": 4.5,
        "user_ratings_total": 12, "maps_url": "https://maps.google.com/?cid=p1",
    },
    {
        "name": "Martin Électricité", "type": "electrician", "phone": "0607080910",
        "address": "5 avenue Foch, 69006 Lyon", "rating": 4.0,
        "user_ratings_total": 5, "maps_url": "https://maps.google.com/?cid=p2",
    },
]


def test_generate_excel_creates_file(tmp_path):
    output_path = str(tmp_path / "leads.xlsx")
    generate_excel(SAMPLE_LEADS, output_path)
    assert os.path.exists(output_path)


def test_generate_excel_has_correct_headers(tmp_path):
    output_path = str(tmp_path / "leads.xlsx")
    generate_excel(SAMPLE_LEADS, output_path)
    wb = load_workbook(output_path)
    ws = wb.active
    headers = [ws.cell(1, col).value for col in range(1, 8)]
    assert headers == ["Nom", "Type", "Téléphone", "Adresse", "Note", "Nb avis", "Google Maps"]


def test_generate_excel_has_correct_data(tmp_path):
    output_path = str(tmp_path / "leads.xlsx")
    generate_excel(SAMPLE_LEADS, output_path)
    wb = load_workbook(output_path)
    ws = wb.active
    assert ws.cell(2, 1).value == "Dupont Plomberie"
    assert ws.cell(2, 3).value == "0601020304"
    assert ws.cell(3, 1).value == "Martin Électricité"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_export.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'utils.export'`

- [ ] **Step 3: Implement utils/export.py**

```python
# utils/export.py
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

HEADERS = ["Nom", "Type", "Téléphone", "Adresse", "Note", "Nb avis", "Google Maps"]
HEADER_FILL = PatternFill(start_color="1F3864", end_color="1F3864", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def generate_excel(leads: list[dict], output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"

    for col, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    for row, lead in enumerate(leads, start=2):
        ws.cell(row=row, column=1, value=lead.get("name", ""))
        ws.cell(row=row, column=2, value=lead.get("type", ""))
        ws.cell(row=row, column=3, value=lead.get("phone", ""))
        ws.cell(row=row, column=4, value=lead.get("address", ""))
        ws.cell(row=row, column=5, value=lead.get("rating"))
        ws.cell(row=row, column=6, value=lead.get("user_ratings_total", 0))
        ws.cell(row=row, column=7, value=lead.get("maps_url", ""))

    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    wb.save(output_path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_export.py -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add utils/export.py tests/test_export.py
git commit -m "feat: Excel export utility with styled headers"
```

---

### Task 5: Dash layout

**Files:**
- Create: `layout.py`

- [ ] **Step 1: Create layout.py**

```python
# layout.py
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table


def create_layout():
    return dbc.Container([
        html.H2("LeadFinder", className="my-4 text-center"),

        # Filtres
        dbc.Row([
            dbc.Col([
                dbc.Label("Ville"),
                dbc.Input(id="input-city", placeholder="ex: Lyon", type="text"),
            ], width=4),
            dbc.Col([
                dbc.Label("Type de commerce"),
                dbc.Input(id="input-type", placeholder="ex: plumber, photographer", type="text"),
            ], width=4),
            dbc.Col([
                dbc.Label("Filtre"),
                dbc.Checklist(
                    options=[{"label": "Sans site web uniquement", "value": "no_website"}],
                    value=["no_website"],
                    id="check-no-website",
                    switch=True,
                ),
            ], width=2),
            dbc.Col([
                dbc.Label("\u00a0"),
                dbc.Button("Rechercher", id="btn-search", color="primary", className="w-100"),
            ], width=2),
        ], className="mb-4 align-items-end"),

        # Statut + export
        dbc.Row([
            dbc.Col(html.Div(id="search-status", className="text-muted"), width=8),
            dbc.Col([
                dbc.Button(
                    "Exporter en Excel",
                    id="btn-export",
                    color="success",
                    outline=True,
                    disabled=True,
                ),
                dcc.Download(id="download-excel"),
            ], width=4, className="text-end"),
        ], className="mb-2"),

        # Tableau
        dbc.Row([
            dbc.Col(
                dbc.Spinner(
                    dash_table.DataTable(
                        id="table-results",
                        columns=[
                            {"name": "Nom", "id": "name"},
                            {"name": "Type", "id": "type"},
                            {"name": "Téléphone", "id": "phone"},
                            {"name": "Adresse", "id": "address"},
                            {"name": "Note", "id": "rating"},
                            {"name": "Nb avis", "id": "user_ratings_total"},
                            {"name": "Google Maps", "id": "maps_url", "presentation": "markdown"},
                        ],
                        data=[],
                        sort_action="native",
                        filter_action="native",
                        page_size=20,
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
                        style_header={
                            "fontWeight": "bold",
                            "backgroundColor": "#1F3864",
                            "color": "white",
                        },
                        style_data_conditional=[
                            {"if": {"row_index": "odd"}, "backgroundColor": "#2c2c2c"}
                        ],
                    ),
                    color="primary",
                )
            )
        ]),

        # Store pour passer les données au callback export
        dcc.Store(id="store-results"),
    ], fluid=True)
```

- [ ] **Step 2: Verify no import errors**

```bash
python -c "from layout import create_layout; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add layout.py
git commit -m "feat: Dash layout with filters, results table, and export button"
```

---

### Task 6: Callbacks

**Files:**
- Create: `callbacks.py`

- [ ] **Step 1: Create callbacks.py**

```python
# callbacks.py
import os
import tempfile
from dash import Input, Output, State, no_update, dcc
from dotenv import load_dotenv
from connectors.google_places import GooglePlacesConnector
from database import Database
from utils.export import generate_excel

load_dotenv()

db = Database()


def register_callbacks(app):

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

        connector = GooglePlacesConnector(api_key=api_key)

        try:
            lat, lng = connector.geocode(city)
        except ValueError as e:
            return no_update, f"Erreur de géocodage : {e}", True

        places = connector.search(lat=lat, lng=lng, place_type=place_type)

        for place in places:
            db.upsert_place(place)

        if no_website_filter and "no_website" in no_website_filter:
            display = [p for p in places if not p["has_website"]]
        else:
            display = places

        # Formater les liens pour la colonne Google Maps
        for lead in display:
            if lead.get("maps_url"):
                lead["maps_url"] = f"[Voir]({lead['maps_url']})"

        status = (
            f"{len(display)} résultat(s) trouvé(s) "
            f"({connector.api_call_count} appels API consommés)"
        )
        export_disabled = len(display) == 0
        return display, status, export_disabled

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
        # Restaurer les URLs brutes avant export (supprimer le formatage markdown)
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
```

- [ ] **Step 2: Verify no import errors**

```bash
python -c "from callbacks import register_callbacks; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add callbacks.py
git commit -m "feat: search and export callbacks"
```

---

### Task 7: App entry point + smoke test final

**Files:**
- Create: `app.py`
- Create: `.env` (à partir de `.env.example`, avec la vraie clé API)

- [ ] **Step 1: Create app.py**

```python
# app.py
import dash
import dash_bootstrap_components as dbc
from layout import create_layout
from callbacks import register_callbacks

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="LeadFinder",
)

app.layout = create_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True)
```

- [ ] **Step 2: Smoke test — vérifier que l'app s'assemble sans erreur**

```bash
python -c "
import dash
import dash_bootstrap_components as dbc
from layout import create_layout
from callbacks import register_callbacks
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.layout = create_layout()
register_callbacks(app)
print('App OK')
"
```
Expected: `App OK`

- [ ] **Step 3: Run all tests**

```bash
pytest tests/ -v
```
Expected: 11 tests PASS (4 database + 4 google_places + 3 export)

- [ ] **Step 4: Créer le fichier .env avec ta vraie clé API Google**

```
GOOGLE_API_KEY=<ta_clé_ici>
```

Pour obtenir la clé gratuitement :
1. Va sur https://console.cloud.google.com
2. Crée un projet
3. Active "Places API" et "Geocoding API"
4. Génère une clé API dans "Identifiants"

- [ ] **Step 5: Lancer l'app**

```bash
python app.py
```
Ouvre http://127.0.0.1:8050 — tu dois voir l'interface avec les filtres et le tableau vide.

- [ ] **Step 6: Commit final**

```bash
git add app.py
git commit -m "feat: app entry point — LeadFinder V1 complete"
```

---

## Résumé des tests

```bash
pytest tests/ -v
```
Expected: **11 tests PASS** (4 database + 4 google_places + 3 export)
