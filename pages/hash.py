import dash
import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State
from dash_auth import public_callback

from src.utils import hasher


dash.register_page(__name__)


def layout():
    password_input = html.Div(
        [
            dbc.Label("Password", html_for="example-password"),
            dbc.Input(
                type="password",
                id="password",
                placeholder="Enter password",
            ),
            dbc.FormText(
                "Schick den untenstehenden Hash an den Admin...", color="secondary"
            ),
        ],
        className="mb-3"
    )

    return dbc.Container([
        dbc.Form([password_input], id="password-input"),
        dbc.Button("Passwort erzeugen",color="primary", className="me-1", id="generate"),
        html.Br(),
        html.Div(id="output-container"),
    ])


@public_callback(
    Output("output-container", "children"),
    Input("generate", "n_clicks"),
    Input("password-input", "n_submit"),
    State("password", "value"),
)
def generate_hash(_, _1, password):
    if not password:
        return ""
    return hasher.hash(password)
