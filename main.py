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

app.index_string = '''<!DOCTYPE html>
<html>
<head>
<title>My app title</title>
<link rel="manifest" href="./assets/manifest.json" />
{%metas%}
{%favicon%}
{%css%}
</head>
<script type="module">
   import 'https://cdn.jsdelivr.net/npm/@pwabuilder/pwaupdate';
   const el = document.createElement('pwa-update');
   document.body.appendChild(el);
</script>
<body>
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', ()=> {
      navigator
      .serviceWorker
      .register('./assets/sw01.js')
      .then(()=>console.log("Ready."))
      .catch(()=>console.log("Err..."));
    });
  }
</script>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>
'''

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
          secret_key=config["secret_key"], public_routes=["/", "/hash", "/assets/manifest.json", "/assets/sw01.js"])


def layout():
    user_groups = list_groups()
    if user_groups is None:
        children = [
            dbc.NavItem(dbc.NavLink(f"Login", href="/login")),
            dbc.NavItem(dbc.NavLink(f"Registrieren", href="/hash"))
        ]
    else:
        links = ([dbc.NavItem(dbc.NavLink(f"{key}", href="/refs" + url_builder(value)))
                  for key, value in get_grouped_users(user_groups).items()] +
                 [dbc.NavItem(dbc.NavLink(f"{group[1]} {group[0]}", href="/refs" + url_builder([group])))
                  for group in get_single_users(user_groups)])

        children = [
            dbc.Switch(
                id="mode-switch",
                label="Datum-Gruppierung",
                value=False,

            ),
            *links[:min(3, len(links))],
        ]

        if len(links) > 3:
            children += [
                dbc.DropdownMenu(
                    children=[
                        dbc.DropdownMenuItem("Mehr", header=True),
                        *links[3:]
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


@app.server.route('/assets/manifest.json')
def serve_manifest():
    return send_file('manifest.json', mimetype='application/manifest+json')

@app.server.route('/assets/sw01.js')
def serve_sw():
    return send_file('sw01.js', mimetype='application/javascript')


app.layout = layout

if __name__ == '__main__':
    app.run(debug=True)
