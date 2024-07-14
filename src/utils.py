import json
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def url_builder(users: List[List[str]], prefix="refs") -> str:
    args = f"?{prefix}="+"_".join(users[0])
    for user in users[1:]:
        args += f"&{prefix}="+"_".join(user)
    return args


base_url = "https://www.dfbnet.org"
dfbnet_login = "https://www.dfbnet.org/spielplus/oauth/login?submit=Anmelden"
search = "https://www.dfbnet.org/sria/mod_sria/offenespielelist.do?reqCode=view"

with open('../config.json', 'r') as f:
    config = json.load(f)

grouped_users = {group_name: url_builder(config['grouped_users'][group_name]) for group_name in config['grouped_users']}
single_users = {f"{user[0]} {user[1]}": url_builder([user]) for user in config['single_users']}
ref_whitelist = [xs for x in config['grouped_users'].values() for xs in x] + config['single_users']


def get_ref_req(vorname, nachname, datedelta):
    return {"staffel": "", "msa_id": "0", "status": "4", "date": datetime.today().strftime("%d.%m.%Y"),
            "datedelta": str(datedelta), "srvorname": vorname, "srnachname": nachname, "spieltag": ""}


def search_link(web_content, keyword):
    for el in web_content.find_all('a'):
        if el.text == keyword:
            return el['href']
    return None


class Ref:
    def __init__(self, ref_args: List[str]):
        self.role = ref_args[0]
        self.name = ref_args[1]
        self.state = ref_args[2]

    def __repr__(self):
        return f"{self.role}: {self.name} ({self.state})"

    def __eq__(self, other):
        return self.role == other.role and self.name == other.name and self.state == other.state

    def __hash__(self):
        return hash((self.role, self.name, self.state))


class Match:
    def __init__(self, match_args: List[str], ref_state):
        split_args = match_args[1].split("\n")
        if len(split_args) == 3:
            self.date = " ".join(split_args[1:])
        elif len(split_args) == 2:
            self.date = " ".join(split_args)
        else:
            self.date = " ".join(split_args)
        self.date = datetime.strptime(self.date, "%d.%m.%Y %H:%M")
        split_args = match_args[2].split("\n")
        if len(split_args) == 2:
            self.staffel, self.match_id = split_args
        else:
            self.staffel, self.match_id = " ".join(split_args), ""
        split_args = match_args[4].split("\n")
        if len(split_args) == 2:
            self.home, self.location = split_args
        else:
            self.home, self.location = split_args[0], ""
        self.guest = match_args[5]

        team_args = []
        for a in match_args[7].split("\n"):
            if not "ATS" in a and not "-->" in a and a != "":
                team_args += [a]
        assert len(team_args) % 2 == 0

        self.team = [Ref(args) for args in zip(team_args[0::2], team_args[1::2], ref_state)]

    def __repr__(self):
        return f"{self.date}\n{self.staffel}\n{self.home} v. {self.guest}\n{self.location}\n{self.team}"

    def __eq__(self, other):
        return (self.date == other.date and
                self.staffel == other.staffel and
                self.match_id == other.match_id and
                self.home == other.home and
                self.location == other.location and
                self.guest == other.guest and
                self.team == other.team)

    def __hash__(self):
        return hash((self.date, self.staffel, self.home, self.location, self.guest, self.team))


def parse_icons(contents):
    return_list = []
    for icon in contents:
        match icon['alt']:
            case "Ansetzung bestätigt.":
                return_list += ['✓']
            case "Ansetzung nicht bestätigt.":
                return_list += ['❓']
            case "Vorläufige Einteilung":
                return_list += ['✘']
    return return_list


def parse_matches(web_page):
    match = None
    try:
        matches = []

        table = web_page.find('table', attrs={"class": "sportView"})
        rows = table.find_all("tr", recursive=False)[1:]
        for row in rows:
            elements = []
            match = row.find_all("td", recursive=False)
            for el in match:
                if el.get_text() == 'Keine Einträge gefunden!':
                    return []
                elements += [el.get_text("\n").strip().replace("\xa0", "")]
            matches += [Match(elements, parse_icons(match[-2].find_all('img')))]
    except Exception as e:
        print(e)
        print(match)
    return matches


def prepare_search_session(username, password):
    s = requests.Session()

    resp = s.get(dfbnet_login)
    x = BeautifulSoup(resp.text, "html.parser")
    auth_webpage = x.find(id="kc-form-login")['action']
    resp = s.post(auth_webpage, data={
                                        "username": username,
                                        "password":	password,
                                        "credentialId":	"",
                                     })
    x = BeautifulSoup(resp.text, "html.parser")
    new_link = search_link(x, 'Schiriansetzung')
    resp = s.get(urljoin(base_url, new_link))
    x = BeautifulSoup(resp.text, "html.parser")
    new_link = search_link(x, 'Ansetzung')
    s.get(urljoin(base_url, new_link))
    return s


def search_ref(session, nachname, vorname):
    resp = session.post(search, data=get_ref_req(nachname=nachname, vorname=vorname, datedelta=999))
    x = BeautifulSoup(resp.text, "html.parser")
    return parse_matches(x)
