import json
from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests
from argon2 import PasswordHasher
from bs4 import BeautifulSoup


title = "Voreinteilungen 👀"

with open('config.json', 'r') as f:
    config = json.load(f)

hasher = PasswordHasher()


def update_config():
    with open('config.json', 'w') as f:
        json.dump(config, f)


def get_password_hash_for_user(username: str) -> str:
    if username not in config["auth"]:
        return ""
    return config["auth"][username]["password"]


def set_password_hash_for_user(user: str, pw_hash: str) -> None:
    config["auth"][user]["password"] = pw_hash
    update_config()


def url_builder(users: List[List[str]], prefix="refs") -> str:
    args = f"?{prefix}=" + "_".join(users[0])
    for user in users[1:]:
        args += f"&{prefix}=" + "_".join(user)
    return args


base_url = "https://www.dfbnet.org"
dfbnet_login = "https://www.dfbnet.org/spielplus/oauth/login?submit=Anmelden"
search = "https://www.dfbnet.org/sria/mod_sria/offenespielelist.do?reqCode=view"


def get_grouped_users(user_groups):
    group_links = {}  # name: list_of_users
    for key in config["grouped_users"]:
        if config["grouped_users"][key]["group"] not in user_groups:
            continue
        group_links[key] = config['grouped_users'][key]["users"]
    return group_links


def get_single_users(user_groups):
    single_user_links = []  # list_of_users
    for group in user_groups:
        if not isinstance(group, list) and len(group) != 2:
            continue
        single_user_links += [group]
    return single_user_links


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
        self.role = ref_args[0][0]
        self.name = ref_args[0][1]
        self.state = ref_args[1]
        self.atspl = ref_args[0][2]

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

        valid_roles = ["SR", "SRA1", "SRA2", "BEO", "PA", "4OF"]
        search_for_name = False
        team_args = []
        current_ref = []
        current_ATSPL = ""
        for a in match_args[7].split("\n"):
            if "ATS" in a or a == "":
                continue
            elif "-->" in a:
                current_ATSPL = a.replace("-->", "").strip()
                continue
            elif a in valid_roles:
                if not search_for_name:
                    search_for_name = True
                else:
                    current_ref.append("")
                    current_ref.append(current_ATSPL)
                    team_args.append(current_ref)
                current_ref = [a]
                current_ATSPL = ""
                continue
            else:
                current_ref.append(a)
                current_ref.append(current_ATSPL)
                team_args.append(current_ref)
            current_ref = []
            search_for_name = False
        if search_for_name:
            current_ref.append("")
            current_ref.append(current_ATSPL)
            team_args.append(current_ref)

        self.team = [Ref(args) for args in zip(team_args, ref_state)]

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
    rows = contents.find_all('tr')
    return_list = []

    for row in rows:
        icons = row.find_all('img')
        if len(icons) == 0:
            if "ATS" not in row.text:
                return_list.append("")
        else:
            for icon in icons:
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
            matches += [Match(elements, parse_icons(match[-2]))]
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
        "password": password,
        "credentialId": "",
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
