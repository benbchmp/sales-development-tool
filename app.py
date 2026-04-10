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
                    color="primary",
                    outline=active_path != "/",
                ),
                dbc.Button(
                    "Cold Calls",
                    href="/cold-calls",
                    color="primary",
                    outline=active_path != "/cold-calls",
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
