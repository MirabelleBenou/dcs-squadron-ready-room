"""Lot « rr-public-pages-bilingues » (`v1.0121`) : les pages d'avant la connexion en
français et en anglais -- six tests, sans base ni réseau (le `TestClient` de FastAPI sur
`app.main.app`, le lifespan ne tourne pas).

1. `test_langue_de` -- l'ordre `?lang` / cookie / `Accept-Language`.
2. `test_selecteur` -- `GET /?lang=…` : 303, cookie ; la page en anglais, « EN » non lien.
3. `test_trois_pages_deux_langues` -- les textes de chaque page dans chaque langue.
4. `test_scripts_identiques` -- les blocs `<script>` et la CSP ne dépendent pas de la langue.
5. `test_readyroom_deux_langues` -- la commande, ses réponses, un `detail` de `POST /auth/lien`.
6. `test_demarrage_en_anglais` -- les seize lignes d'`entrypoint.sh` et les quatre raisons.
"""
from __future__ import annotations

import asyncio
import html
import re
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

import pytest

from app import connexion_secours as cs
from app import defense, langue, main, reglages
from app.auth import get_current_user_optional, templates
from app.config import settings
from app.db import get_db
from app.main import app

pytestmark = pytest.mark.filterwarnings(
    "ignore:The `name` is not the first parameter anymore:DeprecationWarning"
)

RACINE = Path(__file__).resolve().parent.parent


async def _identite_repli():
    return ("1st EXAW", "/static/assets/img/emblem-default.png", "Example Air Wing")


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(main, "_wing_login_identity", _identite_repli)
    app.dependency_overrides[get_current_user_optional] = lambda: None
    return TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def _nettoyage():
    yield
    app.dependency_overrides.clear()


def test_langue_de():
    assert langue.langue_de("en", "fr", "fr-FR") == "en"  # ?lang avant le cookie
    assert langue.langue_de(None, "en", "fr-FR") == "en"  # le cookie avant l'en-tête
    assert langue.langue_de(None, None, "fr-FR") == "fr"
    assert langue.langue_de("de", "xx", "fr-FR,fr;q=0.9") == "fr"  # hors de fr/en : ne compte pas
    assert langue.langue_de(None, "de", "en-US") == "en"
    assert langue.langue_de(None, None, "fr-FR,fr;q=0.9,en;q=0.8") == "fr"
    assert langue.langue_de(None, None, "en-US,en;q=0.9,fr;q=0.8") == "en"
    assert langue.langue_de(None, None, "de-DE,fr;q=0.9") == "en"
    assert langue.langue_de(None, None, "en;q=0.5,fr;q=0.8") == "fr"
    for vide in (None, "", "   ", ";;;", "fr;q=abc", ",,"):
        assert langue.langue_de(None, None, vide) == "en", vide


def test_selecteur(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(settings, "BASE_URL", "https://rr.example.org")
    r = client.get("/?lang=en")
    assert r.status_code == 303 and r.headers["location"] == "/"
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("rr_langue=en;")
    for attribut in ("Path=/", "Max-Age=31536000", "SameSite=lax", "HttpOnly", "Secure"):
        assert attribut.lower() in cookie.lower(), attribut
    monkeypatch.setattr(settings, "BASE_URL", "http://rr.example.org")
    assert "secure" not in client.get("/?lang=fr").headers["set-cookie"].lower()
    # La page suit le cookie, avant l'en-tête.
    page = client.get("/", headers={"cookie": "rr_langue=en", "accept-language": "fr"})
    assert page.status_code == 200
    assert '<html lang="en">' in page.text and "Sign in with Discord" in page.text
    assert '<span aria-current="true">EN</span>' in page.text
    assert 'href="/?lang=fr"' in page.text and 'href="/?lang=en"' not in page.text
    assert 'aria-label="Language"' in page.text
    # Une autre valeur : la page, sans cookie.
    r = client.get("/?lang=de", headers={"accept-language": "fr"})
    assert r.status_code == 200 and "set-cookie" not in r.headers
    assert 'aria-label="Langue"' in r.text


def _refus(lang: str, **contexte) -> str:
    base = {"nom": "Pilote", "identifiant": "pilote", "motif": "sans_role", "commande": True,
            "lang": lang, "t": langue.textes(lang)}
    base.update(contexte)
    return templates.get_template("noaccess.html").render(**base)


def test_trois_pages_deux_langues(monkeypatch):
    client = _client(monkeypatch)
    attendu = {
        "fr": {
            "login": ["Squadron Ready Room — Connexion", "Accès réservé aux membres autorisés de l'escadre.", "Se connecter avec Discord"],
            "refus": ["Squadron Ready Room — Accès refusé", "Accès refusé",
                      "Compte Discord utilisé : <strong>Pilote</strong> (@pilote).",
                      "Pas le bon compte ? Déconnecte-toi de Discord dans ce navigateur, sur discord.com, puis réessaie.",
                      "Tu peux aussi taper /readyroom dans le serveur Discord de l'escadre : tu recevras un lien d'entrée.",
                      "Sinon, contacte le staff.", ">Retour</a>"],
            "non_membre": "Ce compte n'est pas membre du serveur Discord de l'escadre.",
            "sans_role": "Ce compte n'a aucun rôle qui ouvre la Ready Room.",
            "lien": ["Squadron Ready Room — Lien de connexion", "Lien de connexion de secours. Il ouvre ta session une seule fois.",
                     ">Entrer</button>", "Ce lien est incomplet : ouvre-le tel qu'il t'a été remis.",
                     "La connexion n'a pas abouti. Réessaie dans un instant."],
        },
        "en": {
            "login": ["Squadron Ready Room — Sign in", "Access restricted to the wing's authorised members.", "Sign in with Discord"],
            "refus": ["Squadron Ready Room — Access denied", "Access denied",
                      "Discord account used: <strong>Pilote</strong> (@pilote).",
                      "Wrong account? Sign out of Discord in this browser, on discord.com, then try again.",
                      "You can also type /readyroom in the wing's Discord server: you will receive an entry link.",
                      "Otherwise, contact the staff.", ">Back</a>"],
            "non_membre": "This account is not a member of the wing's Discord server.",
            "sans_role": "This account has no role that opens the Ready Room.",
            "lien": ["Squadron Ready Room — Sign-in link", "Backup sign-in link. It opens your session once only.",
                     ">Enter</button>", "This link is incomplete: open it exactly as you received it.",
                     "Sign-in failed. Try again in a moment."],
        },
    }
    credit = "Based on Squadron Ready Room by MirabelleBenou"
    for lang, a in attendu.items():
        cookie = {"cookie": f"rr_langue={lang}"}
        login = client.get("/", headers=cookie).text
        assert f'<html lang="{lang}">' in login
        for texte in a["login"]:
            assert texte in login, (lang, texte)
        assert login.count(credit) == 1, lang
        lien = html.unescape(client.get("/auth/lien", headers=cookie).text)
        assert f'<html lang="{lang}">' in lien
        for texte in a["lien"]:
            assert texte in lien, (lang, texte)
        sans_role, non_membre = _refus(lang, motif="sans_role"), _refus(lang, motif="non_membre")
        assert f'<html lang="{lang}">' in sans_role
        for texte in a["refus"]:
            assert texte in sans_role, (lang, texte)
        assert a["sans_role"] in sans_role and a["non_membre"] not in sans_role
        assert a["non_membre"] in non_membre and a["sans_role"] not in non_membre
        # Sans la commande : sa phrase disparaît.
        assert a["refus"][4] not in _refus(lang, commande=False)
        # Le nom reste échappé.
        assert "&lt;b&gt;" in _refus(lang, nom="<b>X</b>")


def _scripts(texte: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", texte, re.DOTALL)


def test_scripts_identiques(monkeypatch):
    client = _client(monkeypatch)
    for chemin in ("/", "/auth/lien"):
        fr = client.get(chemin, headers={"cookie": "rr_langue=fr"})
        en = client.get(chemin, headers={"cookie": "rr_langue=en"})
        assert _scripts(fr.text) and _scripts(fr.text) == _scripts(en.text), chemin
        assert fr.headers["content-security-policy"] == en.headers["content-security-policy"], chemin
    # Aucune syntaxe Jinja dans un bloc `<script>`, et le texte du lien vient de la page.
    for nom in ("login.html", "lien.html"):
        source = (RACINE / "app" / "templates" / nom).read_text(encoding="utf-8")
        for bloc in _scripts(source):
            assert "{{" not in bloc and "{%" not in bloc and "{#" not in bloc, nom


def test_readyroom_deux_langues(monkeypatch):
    commande = cs.commande_readyroom()
    assert commande["description"] == "Get a link to enter the Ready Room when Discord sign-in fails"
    assert set(commande["description_localizations"]) == {"fr"}
    assert len(commande["description"]) <= 100
    assert all(len(d) <= 100 for d in commande["description_localizations"].values())

    class _Base:
        pass

    for locale, lang in (("fr", "fr"), ("fr-CA", "fr"), ("en-US", "en"), ("de", "en"), (None, "en")):
        t = langue.textes(lang)
        corps = {"data": {"name": "autre"}}
        if locale is not None:
            corps["locale"] = locale
        assert asyncio.run(cs.traiter_commande(_Base(), corps))["data"]["content"] == t["cmd_inconnue"]
        sans_membre = {**corps, "data": {"name": "readyroom"}}
        assert asyncio.run(cs.traiter_commande(_Base(), sans_membre))["data"]["content"] == t["cmd_hors_serveur"]
        reponse = cs.reponse_commande("https://x/auth/lien#t", langue.langue_discord(locale))
        assert reponse["data"]["content"] == t["cmd_lien"]
        assert reponse["data"]["components"][0]["components"][0]["label"] == t["cmd_bouton"]
    # Une erreur imprévue : la phrase d'erreur, dans la langue.
    erreur = asyncio.run(cs.traiter_commande(None, {"data": {"name": "readyroom"}, "member": {"user": {}}, "locale": "fr"}))
    assert erreur["data"]["content"] == langue.textes("fr")["cmd_erreur"]
    erreur = asyncio.run(cs.traiter_commande(None, {"data": {"name": "readyroom"}, "member": {"user": {}}}))
    assert erreur["data"]["content"] == langue.textes("en")["cmd_erreur"]

    # `detail` de `POST /auth/lien` : 400 (jeton absent) dans chaque langue.
    monkeypatch.setattr(settings, "BASE_URL", "http://testserver")
    app.dependency_overrides[get_db] = lambda: None
    client = TestClient(app, follow_redirects=False)
    for lang, detail in (("fr", "Lien invalide."), ("en", "Invalid link.")):
        r = client.post("/auth/lien", json={}, headers={"cookie": f"rr_langue={lang}"})
        assert r.status_code == 400 and r.json()["detail"] == detail, lang
    r = client.post("/auth/lien", content=b"x", headers={"content-type": "text/plain", "accept-language": "fr"})
    assert r.status_code == 415 and r.json()["detail"] == "Le corps doit être du JSON."
    r = client.post("/auth/lien", content=b"x", headers={"content-type": "text/plain"})
    assert r.status_code == 415 and r.json()["detail"] == "The body must be JSON."


LIGNES_DEMARRAGE = [
    "[entrypoint] Failure: SESSION_SECRET refused (${RAISON_SECRET}).",
    "[entrypoint] Failure: configuration refused (${RAISON_CONFIG}).",
    "[entrypoint] Waiting for the database...",
    "[entrypoint] Failure: the database did not become available after $MAX_ATTEMPTS attempts.",
    "[entrypoint] Database not ready (attempt $ATTEMPTS/$MAX_ATTEMPTS), retrying in 2s...",
    "[entrypoint] Database ready.",
    "[entrypoint] Migration pending (current: ${CURRENT_REV:-none}, target: $HEAD_REV): backup before applying.",
    "[entrypoint] Backing up to $BACKUP_FILE...",
    "[entrypoint] Failure: pg_dump returned an error. Migration not applied, stopping.",
    "[entrypoint] Failure: the backup file is empty ($BACKUP_FILE). Migration not applied, stopping.",
    "[entrypoint] Backup OK ($(du -h \"$BACKUP_FILE\" | cut -f1)).",
    "[entrypoint] Purge: $BACKUP_COUNT backups, keeping the 10 most recent.",
    "[entrypoint] No migration pending ($CURRENT_REV): no backup.",
    "[entrypoint] Applying migrations...",
    "[entrypoint] Migrations applied (alembic upgrade head OK).",
    "[entrypoint] Starting the application...",
]


def test_demarrage_en_anglais():
    source = (RACINE / "entrypoint.sh").read_text(encoding="utf-8")
    lignes = re.findall(r'echo "(\[entrypoint\] .*)"$', source, re.MULTILINE)
    assert lignes == LIGNES_DEMARRAGE
    assert defense.secret_refuse("court") == "fewer than 32 characters"
    exemple = "x" * 40
    assert defense.secret_refuse(exemple) is None
    assert reglages.controle_au_demarrage({"CONFIG_KEY": "", "ADMIN_IDS": "1"}) == "CONFIG_KEY missing or invalid"
    from cryptography.fernet import Fernet

    cle = Fernet.generate_key().decode()
    assert reglages.controle_au_demarrage({"CONFIG_KEY": cle, "ADMIN_IDS": ""}) == "ADMIN_IDS empty: at least one founding administrator"
    assert reglages.controle_au_demarrage({"CONFIG_KEY": cle, "ADMIN_IDS": "123"}) is None
