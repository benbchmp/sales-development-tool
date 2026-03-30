# layout.py
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from place_types import PLACE_TYPES


def create_layout():
    return dbc.Container([
        html.H2("LeadFinder", className="my-4 text-center"),

        # Filtres
        dbc.Row([
            dbc.Col([
                dbc.Label("Ville"),
                dcc.Dropdown(
                    id="input-city",
                    options=[],
                    placeholder="Tapez une ville (ex: Lyon)...",
                    search_value="",
                    style={"color": "#000"},
                ),
            ], width=4),
            dbc.Col([
                dbc.Label("Type de commerce"),
                dcc.Dropdown(
                    id="input-type",
                    options=PLACE_TYPES,
                    placeholder="Tapez un métier (ex: plombier)...",
                    search_value="",
                    style={"color": "#000"},
                ),
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
