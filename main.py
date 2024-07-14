import dash
from dash import Dash
import dash_bootstrap_components as dbc
import flask

from dash_auth import BasicAuth

from src.utils import grouped_users, single_users, config

server = flask.Flask(__name__)  # define flask app.server
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, dbc_css], server=server, use_pages=True)

USER_PWD = {
    config["auth"]["username"]: config["auth"]["password"],
}
BasicAuth(app, USER_PWD, secret_key=config["auth"]["secret_key"])

app.layout = dbc.Container([
    dbc.NavbarSimple(
        children=[
            dbc.Switch(
                id="mode-switch",
                label="Datum-Gruppierung",
                value=False,
            ),
            *[
                dbc.NavItem(dbc.NavLink(f"{key}", href="/refs" + value))
                for key, value in grouped_users.items()
            ],
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Mehr", header=True),
                    *[
                        dbc.NavItem(dbc.NavLink(f"{key}", href="/refs" + value))
                        for key, value in single_users.items()
                    ]
                ],
                nav=True,
                in_navbar=True,
                label="More",
            ),
        ],
        brand="Voreinteilungen 👀",
        brand_href="/",
        color="primary",
        dark=True,
    ),
    dash.page_container
])

if __name__ == '__main__':
    app.run(debug=True)
