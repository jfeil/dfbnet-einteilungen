from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple

import dash
from dash import html, callback, Output, Input
from dash_auth import protected_callback, list_groups

from src.utils import prepare_search_session, search_ref, Match, config, get_grouped_users, get_single_users
import dash_ag_grid as dag
import pandas as pd

dash.register_page(__name__)

session = None
modified_timestamp = -1


def create_ag_grids(data: Dict[Tuple[str, str] | date, List[Match]]):
    def list_to_grid(data: List[Match], hide_date: bool):
        if not hide_date:
            columnDefs = [
                {'field': 'Datum', 'width': 120, 'suppressSizeToFit': True}
            ]
        else:
            columnDefs = []

        columnDefs += [
            {'field': 'Zeit', 'width': 80, 'suppressSizeToFit': True},
            {'field': 'Staffel', 'width': 100, 'suppressSizeToFit': True},
            {'field': 'Heim'},
            {'field': 'Gast'},
            {'field': 'SR-Team', "wrapText": True, "autoHeight": True,
             "cellStyle": {'wordBreak': 'normal', 'whiteSpace': 'pre'}},
            {'field': 'Ort', "wrapText": True, "cellStyle": {'wordBreak': 'normal', 'whiteSpace': 'pre'}},
        ]

        df = pd.DataFrame(columns=[x['field'] for x in columnDefs])

        for i, el in enumerate(data):
            new_row = []
            if not hide_date:
                new_row += [el.date.strftime('%a, %d.%m')]
            ref_team = ""
            for t in el.team:
                ref_team += t.role
                if t.name:
                    ref_team += f": {t.name} ({t.state})"
                if t.atspl:
                    ref_team += f" [{t.atspl}]"
                ref_team += "\n"

            new_row += [el.date.strftime('%H:%M'), el.staffel, el.home, el.guest, ref_team, el.location]
            df.loc[i] = new_row

        return html.Div(dag.AgGrid(
            rowData=df.to_dict("records"),
            columnDefs=columnDefs,
            dashGridOptions={"domLayout": "autoHeight", "enableCellTextSelection": True, "ensureDomOrder": True},
            columnSize="responsiveSizeToFit",
        ), className="dbc dbc-ag-grid")

    content = []
    for key in sorted(data):
        if isinstance(key, date):
            title = key.strftime('%a, %d.%m.%Y')
            hide_date = True
        elif isinstance(key, Tuple):
            title = " ".join(key)
            hide_date = False
        else:
            raise ValueError(f"Unexpected key type: {type(key)}")
        content.append(html.Br())
        content.append(html.H3(title))
        content.append(list_to_grid(data[key], hide_date))
    return content


def layout(refs=None):
    empty_placeholder = html.Div([
            html.Br(),
            html.H1("No referee selected..."),
                         html.Div("", id='tables-name', hidden=True),
                         html.Div("", id='tables-date', hidden=True),
                         ])
    if refs is None:
        return empty_placeholder
    if isinstance(refs, str):
        refs = [refs]
    refs_temp = [ref.split("_") for ref in refs]
    valid_refs = []
    user_groups = list_groups()
    ref_whitelist = []
    if "admin" in user_groups:
        valid_refs = refs_temp
    else:
        for value in get_grouped_users(user_groups).values():
            ref_whitelist += value
        ref_whitelist += get_single_users(user_groups)
        for ref in refs_temp:
            if ref in ref_whitelist:
                valid_refs += [ref]
        if len(valid_refs) == 0:
            return empty_placeholder
    global session, modified_timestamp
    if session is None or modified_timestamp < datetime.now() - timedelta(minutes=15):
        session = prepare_search_session(username=config["spielplus"]["username"],
                                         password=config["spielplus"]["password"])
        modified_timestamp = datetime.now()

    name_matches = {}
    for ref in valid_refs:
        name_matches[tuple(ref)] = search_ref(session, *ref)

    date_matches = defaultdict(list)
    for m in name_matches.values():
        for a in m:
            if a in date_matches[a.date.date()]:
                continue
            date_matches[a.date.date()] += [a]
    date_matches = dict(date_matches)

    content_names = html.Div(create_ag_grids(name_matches), id='tables-name', hidden=True)
    content_dates = html.Div(create_ag_grids(date_matches), id='tables-date', hidden=True)

    return html.Div([
        content_names,
        content_dates
    ])


@protected_callback(
    Output('tables-name', 'hidden'),
    Output('tables-date', 'hidden'),
    Input('mode-switch', 'value')
)
def toggle_mode(value):
    return value, not value
