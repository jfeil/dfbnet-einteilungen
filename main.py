import argon2
import dash
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from dash import Dash, dcc
import dash_bootstrap_components as dbc
import flask

from dash_auth import BasicAuth, list_groups

from src.utils import config, get_password_hash_for_user, hasher, \
    set_password_hash_for_user, url_builder, get_grouped_users, get_single_users

server = flask.Flask(__name__)  # define flask app.server
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, dbc_css], server=server, use_pages=True,
           suppress_callback_exceptions=True)


# You can also use a function to get user groups
def check_user(username, password):
    hash_ = get_password_hash_for_user(username)
    result = True
    try:
        # Verify password, raises exception if wrong.
        hasher.verify(hash_, password)
    except VerifyMismatchError or VerificationError or InvalidHashError:
        result = False

    # Now that we have the cleartext password,
    # check the hash's parameters and if outdated,
    # rehash the user's password in the database.
    if hasher.check_needs_rehash(hash_):
        set_password_hash_for_user(username, hasher.hash(password))

    return result


def get_user_groups(user):
    if user not in config["auth"]:
        return []
    if "groups" not in config["auth"][user]:
        return []
    if isinstance(config["auth"][user]["groups"], str):
        groups = [config["auth"][user]["groups"]]
    else:
        groups = config["auth"][user]["groups"]
    return groups


BasicAuth(app, auth_func=check_user, user_groups=get_user_groups,
          secret_key=config["secret_key"], public_routes=["/", "/hash"])


def layout():
    user_groups = list_groups()
    if user_groups is None:
        children = [
            dbc.NavItem(dbc.NavLink(f"Login", href="/login")),
            dbc.NavItem(dbc.NavLink(f"Registrieren", href="/hash"))
        ]
    else:
        group_links = [dbc.NavItem(dbc.NavLink(f"{key}", href="/refs" + url_builder(value)))
                       for key, value in get_grouped_users(user_groups).items()]

        single_user_links = [dbc.NavItem(dbc.NavLink(f"{group[1]} {group[0]}", href="/refs" + url_builder([group])))
                             for group in get_single_users(user_groups)]


        children = [
            dbc.Switch(
                id="mode-switch",
                label="Datum-Gruppierung",
                value=False,

            ),
            *group_links,
        ]

        if single_user_links:
            children += [
                dbc.DropdownMenu(
                    children=[
                        dbc.DropdownMenuItem("Mehr", header=True),
                        *single_user_links
                    ],
                    nav=True,
                    in_navbar=True,
                    label="More",
                ),
            ]

    return dbc.Container([
        dbc.NavbarSimple(
            children=children,
            brand="Voreinteilungen 👀",
            brand_href="/",
            color="primary",
            dark=True,
        ),
        dash.page_container,
        dcc.Location("url_name")
    ])


app.layout = layout

if __name__ == '__main__':
    app.run(debug=True)
