import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback

dash.register_page(__name__)

layout = dbc.Container([])


@callback(
        Output('url_name', 'pathname'),
        Input('url_name', 'pathname'))
def login(current_url):
    print(current_url)
    if current_url == "/login":
        return "/"
    return dash.no_update
