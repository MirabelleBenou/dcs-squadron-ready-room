"""Dépôt d'un VRAI debrief.log par l'API -- banc v6 (B7), jamais dans une archive de l'application.
Lecture seule sur le journal. Joue le chemin de production tel quel : POST /api/debrief/upload (kind=debrief), derrière
laquelle tourne le vrai `engine.ingest_file` -- rien n'est remplacé ni simulé. Puis il vérifie que la session existe
(GET /api/debrief/sessions/<id>) et qu'elle porte des vols et une durée.

Le journal : `debrief_francfort_reduit.log`, tiré du journal réel de Golem sur la Bataille de Francfort (session 89f20c83,
20 Mo, dont 19 Mo d'entrepôts). Gardés tels quels : l'en-tête, le cimetière entier, les champs racine `mission_file_mark`,
`mission_time` et `result`, et les évènements qui touchent une des 13 vies du déposant (initiateur ou cible), plus
« mission start » et « mission end » (noms pseudonymisés au v1.0114). Le déposant est Viper : c'est le profil du banc qui porte Golem (README).

À jouer sur une base SANS Débrief semé (prepare_base.sh) : sur prepare_debrief.sh, la session semée porte déjà ce titre
et peut se confondre avec elle. Le script exige que le dépôt CRÉE la session ; sinon il s'arrête (code 1).
Les fichiers bruts du dépôt vont dans /data/debrief_raw/ (DEBRIEF_STORAGE_DIR, par défaut), hors du banc.

Usage : sh servir.sh <appli> python3.12 -B deposer_journal.py [journal]
Code de sortie 1 : réponse en erreur, session non créée, aucun vol ou aucune durée. Imprime une ligne de synthèse."""
import json, os, sys, uuid
import urllib.error, urllib.request
from base64 import b64encode
from datetime import datetime, timedelta, timezone
import itsdangerous

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:8000"
JOURNAL = os.path.join(HERE, "debrief_francfort_reduit.log")
DEPOSANT = "200000000000000003"   # Viper : le profil du banc qui porte Golem (README, semis_debrief.py)
ADMIN = ("MistyKestrel42", "100000000000000001", ["700000000000000101", "111111111111111111"], "CHARLIE-33")


def secret():
    for ligne in open("/home/claude/rr/test.env", encoding="utf-8"):
        if ligne.startswith("SESSION_SECRET="):
            return ligne.split("=", 1)[1].strip()
    sys.exit("SESSION_SECRET introuvable dans /home/claude/rr/test.env")


def cookie():
    nom, pid, roles, esc = ADMIN
    session = {"id": pid, "name": nom, "roles": roles, "lang": "fr", "avatar": None, "squadron": esc,
               "exp": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
    return itsdangerous.TimestampSigner(secret()).sign(b64encode(json.dumps(session).encode())).decode()


def multipart(champs, fichier):
    """Corps multipart/form-data, en stdlib : (champs texte, (nom du champ, nom du fichier, octets))."""
    limite = "----banc" + uuid.uuid4().hex
    corps = b""
    for k, v in champs.items():
        corps += f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    nom, fichier_nom, octets = fichier
    corps += (f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"; filename="{fichier_nom}"\r\n'
              f'Content-Type: application/octet-stream\r\n\r\n').encode() + octets + b"\r\n"
    corps += f"--{limite}--\r\n".encode()
    return corps, f"multipart/form-data; boundary={limite}"


def appeler(methode, chemin, corps=None, type_=None):
    en_tetes = {"Cookie": "session=" + COOKIE}
    if type_:
        en_tetes["Content-Type"] = type_
    req = urllib.request.Request(URL + chemin, data=corps, method=methode, headers=en_tetes)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def main():
    chemin = sys.argv[1] if len(sys.argv) > 1 else JOURNAL
    octets = open(chemin, "rb").read()
    corps, type_ = multipart({"kind": "debrief", "depositor": DEPOSANT}, ("file", "debrief.log", octets))
    statut, resume = appeler("POST", "/api/debrief/upload", corps, type_)
    if statut != 200:
        sys.exit(f"dépôt refusé : HTTP {statut} · {resume}")
    if resume.get("no_op") or not resume.get("session_created"):
        sys.exit("le dépôt n'a pas créé de session (journal déjà déposé, ou session existante rejointe) : "
                 "rejouer sur une base neuve, prepare_base.sh")
    sid = resume["session_id"]
    statut, session = appeler("GET", f"/api/debrief/sessions/{sid}")
    if statut != 200:
        sys.exit(f"la session {sid[:8]} n'est pas relisible : HTTP {statut} · {session}")
    vols, duree = session.get("flights") or [], session.get("duration_s")
    du_deposant = [v for v in vols if str(v.get("pilote_profile_id")) == DEPOSANT]
    print(f"dépôt : journal {len(octets) / 1024:.0f} Ko · session {sid[:8]} créée · {len(vols)} vols "
          f"({len(du_deposant)} au déposant) · durée {duree} s · {resume.get('n_kills')} destructions · "
          f"titre « {session.get('title')} »")
    if not vols:
        sys.exit("la session ne porte aucun vol")
    if not duree:
        sys.exit("la session ne porte pas de durée")


COOKIE = cookie()
main()
