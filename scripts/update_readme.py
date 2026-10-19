#!/usr/bin/env python3
"""Régénère le tableau « Projets » du README de profil.

Les textes viennent de projects.json (rédigés à la main : on n'affiche que ce
qui est vrai). L'API GitHub ajoute la date du dernier push et ignore les dépôts
inexistants ou privés.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "stephanemetche")
ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PROJECTS = ROOT / "projects.json"
START, END = "<!--PROJECTS:START-->", "<!--PROJECTS:END-->"


def fetch_repo(name: str) -> dict | None:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{name}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"},
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def build_table(projects: list[dict]) -> str:
    rows = ["| Projet | Description | Domaine | Mis à jour |", "|---|---|---|---|"]
    for p in projects:
        data = fetch_repo(p["repo"])
        if data is None or data.get("private"):
            print(f"[skip] {p['repo']} introuvable ou privé", file=sys.stderr)
            continue
        updated = datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
        rows.append(
            f"| [**{data['name']}**]({data['html_url']}) | {p['description']} | {p['domain']} | {updated} |"
        )
    return "\n".join(rows)


def main() -> int:
    projects = json.loads(PROJECTS.read_text(encoding="utf-8"))
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        print("Marqueurs PROJECTS:START/END absents du README", file=sys.stderr)
        return 1
    new = pattern.sub(f"{START}\n{build_table(projects)}\n{END}", text)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README mis à jour")
    else:
        print("Aucun changement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
