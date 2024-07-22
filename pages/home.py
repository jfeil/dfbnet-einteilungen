import dash
from dash import html
from dash_auth import list_groups

dash.register_page(__name__, path='/')


def get_layout():
    user_groups = list_groups()
    if user_groups is None:
        return html.Div([
            html.H1('Willkommen!'),
            html.Div('Bitte melde dich an oder generiere deinen Passwort-Token zur Registrierung!'),
        ])
    elif "search" in user_groups:
        return html.Div([
            html.H1('Willkommen!'),
            html.Div('Placeholder Freitextsuche'),
        ])
    return html.Div([
        html.H1('Willkommen!'),
        html.Div('Wähle oben deinen gewünschten Schiedsrichter aus.'),
    ])


layout = get_layout
