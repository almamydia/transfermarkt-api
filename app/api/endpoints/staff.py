import re
import urllib.request
import urllib.parse
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup

router = APIRouter()

TM_BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

@router.get("/search/{name}")
def search_staff(name: str):
    """Recherche un membre du staff sur Transfermarkt par nom."""
    url = f"{TM_BASE}/schnellsuche/ergebnis/schnellsuche?query={urllib.parse.quote(name)}&Typ=trainer"
    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    results = []
    for link in soup.select("a[href*='/profil/trainer/']"):
        href = link.get("href", "")
        m = re.search(r"/profil/trainer/(\d+)", href)
        if not m:
            continue
        tm_id = m.group(1)
        name_text = link.text.strip()
        if not name_text:
            continue

        row = link.find_parent("tr") or link.find_parent("td")
        club, role, photo = "", "", ""
        if row:
            cells = row.find_all("td")
            role = cells[1].text.strip() if len(cells) > 1 else ""
            club = cells[2].text.strip() if len(cells) > 2 else ""
            img = row.find("img")
            if img:
                photo = img.get("src", img.get("data-src", ""))

        if any(r["id"] == tm_id for r in results):
            continue

        results.append({
            "id": tm_id,
            "name": name_text,
            "role": role,
            "club": club,
            "photo": photo,
            "tmic": f"TMIC:{tm_id}",
            "tm_url": f"{TM_BASE}{href}",
        })

    return JSONResponse(content={"query": name, "results": results[:10]})


@router.get("/{staff_id}/profile")
def get_staff_profile(staff_id: str):
    """Récupère le profil complet d'un membre du staff."""
    url = f"{TM_BASE}/staff/profil/trainer/{staff_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    photo = ""
    img = soup.select_one("img.data-header__profile-image")
    if img:
        photo = img.get("src", "")

    club = ""
    club_el = soup.select_one("span.data-header__club a") or soup.select_one("div.data-header__club a")
    if club_el:
        club = club_el.text.strip()

    nationality = ""
    nat_imgs = soup.select("span.data-header__content img.flaggenrahmen")
    if nat_imgs:
        nationality = nat_imgs[0].get("title", "")

    dob = ""
    for item in soup.select("li.data-header__label"):
        if "Date of birth" in item.text:
            content = item.find_next("span", class_="data-header__content")
            if content:
                dob = content.text.strip().split("(")[0].strip()
                break

    return JSONResponse(content={
        "id": staff_id,
        "club": club,
        "nationality": nationality,
        "dob": dob,
        "photo": photo,
        "tm_url": url,
    })
