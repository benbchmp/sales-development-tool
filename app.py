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
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "LeadFinder"
server = app.server  # pour gunicorn

leadfinder.register_callbacks(app)
cold_calls.register_callbacks(app)

# ── Navbar ───────────────────────────────────────────────────────────

def _nav_tab(label: str, href: str, active: bool) -> html.A:
    style = {
        "display": "inline-block",
        "padding": "4px 14px",
        "fontSize": "0.78rem",
        "fontFamily": "Consolas, monospace",
        "letterSpacing": "0.05em",
        "textDecoration": "none",
        "border": "1px solid #4dabf7",
        "borderRadius": "3px",
        "color": "#fff" if active else "#4dabf7",
        "backgroundColor": "#1a6fa8" if active else "transparent",
        "transition": "background 0.15s",
    }
    return html.A(label, href=href, style=style)


def _navbar(active_path: str) -> dbc.Container:
    return dbc.Container(
        dbc.Row([
            dbc.Col(html.Img(
                src="/assets/eagle.png",
                style={
                    "height": "48px",
                    "filter": "invert(1)",
                    "mixBlendMode": "screen",
                    "display": "block",
                }
            ), width="auto", className="d-flex align-items-center"),
            dbc.Col(width=True),  # spacer
            dbc.Col(
                html.Div([
                    _nav_tab("LeadFinder", "/", active_path == "/"),
                    _nav_tab("Call Tracker", "/cold-calls", active_path == "/cold-calls"),
                ], style={"display": "flex", "gap": "8px", "alignItems": "center"}),
                width="auto", className="d-flex align-items-center",
            ),
        ], align="center", className="py-2 px-3", style={"borderBottom": "1px solid #2a2a2a"}),
        fluid=True,
        style={"marginBottom": "16px"},
    )


# ── App layout ───────────────────────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="navbar-container"),
    html.Div(leadfinder.layout(), id="page-leadfinder"),
    html.Div(cold_calls.layout(), id="page-coldcalls"),
])


@app.callback(
    Output("navbar-container", "children"),
    Output("page-leadfinder", "style"),
    Output("page-coldcalls", "style"),
    Input("url", "pathname"),
)
def route(pathname):
    show = {"display": "block"}
    hide = {"display": "none"}
    if pathname == "/cold-calls":
        return _navbar("/cold-calls"), hide, show
    return _navbar("/"), show, hide


# ── Run ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8060))
    app.run(debug=True, port=port)
