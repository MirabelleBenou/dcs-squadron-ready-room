"""Faux Discord pour la sonde. Usage : python3 faux_discord.py <port> <fichier_mode> <membres.json> <journal>
Le mode se relit à chaque requête :
  ok · 403 · vide · 500 · 429 (un 429 puis ok) · parti (Nomad absent, 10007 en lecture directe)
  incomplet (Dragoon-1 absent, 200 en lecture directe) · incomplet500 (Dragoon-1 absent, 500 en lecture directe)
  plafond2 (pages de 2 au plus, quoi que demande la sonde)"""
import json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT, MODE, MEMBRES, JOURNAL = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
GUILD = "900000000000000001"
OMIS = {"parti": "200000000000000007", "incomplet": "200000000000000001", "incomplet500": "200000000000000001"}
etat = {"n429": 0}

# --- v4 (lot « Le banc v4 ») : ce qui suit s'ajoute au v3, aucune réponse existante ne change ---------------
# MP : POST /users/@me/channels ouvre un canal privé (identifiant « 9 » + celui du destinataire) ;
# POST /channels/<canal>/messages y dépose le message. Un destinataire listé dans <fichier_mode>.refus
# (un identifiant par ligne, relu à chaque requête) refuse : 403, code 50007, comme Discord. Chaque MP --
# envoyé ou refusé -- s'ajoute à <journal>.mp.jsonl, une ligne JSON {"n", "destinataire", "statut", "corps"}.
# Toute autre écriture répond 404. Le journal reçoit aussi les POST, au format des GET (<mode> TAB METHODE chemin).
# Rôles : GET /guilds/<guilde>/roles rend les rôles du scénario, dans un ordre fixe : l'écran Droits les nomme.
# Les rôles du serveur : les trois escadrilles de production, les cinq d'essai de semis_e.py (identifiants
# 7000000000000010 + rang), puis les rôles de statut et « Officier » (semis_r.py).
ROLES = [("700000000000000101", "CHARLIE-33"), ("700000000000000103", "BRAVO-22"), ("700000000000000102", "ALPHA-11"),
         ("700000000000001001", "T-14"), ("700000000000001002", "T-SANS"), ("700000000000001003", "T-UN"),
         ("700000000000001004", "T-SEUL"), ("700000000000001005", "T-MEMB"),
         ("111111111111111111", "Pilote"), ("222222222222222222", "Probatoire"),
         ("333333333333333333", "Visiteur"), ("444444444444444444", "Officier")]
mp = {"n": 0}
REFUS, MPJ = MODE + ".refus", JOURNAL + ".mp.jsonl"


def refusants():
    try:
        return {l.strip() for l in open(REFUS) if l.strip()}
    except FileNotFoundError:
        return set()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def rendre(self, code, corps, entetes=None):
        b = json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (entetes or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        mode = open(MODE).read().strip()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        with open(JOURNAL, "a") as f:
            f.write(f"{mode}\tGET {self.path}\t{self.headers.get('Authorization')}\n")
        membres = sorted(json.load(open(MEMBRES)), key=lambda m: int(m["user"]["id"]))
        omis = OMIS.get(mode)
        base = f"/api/v10/guilds/{GUILD}/members"
        if u.path == base:
            if mode == "403":
                return self.rendre(403, {"message": "Missing Access", "code": 50001})
            if mode == "500":
                return self.rendre(500, {"message": "Internal Server Error", "code": 0})
            if mode == "vide":
                return self.rendre(200, [])
            if mode == "429" and etat["n429"] == 0:
                etat["n429"] += 1
                return self.rendre(429, {"message": "You are being rate limited.", "retry_after": 0.2,
                                         "global": False}, {"Retry-After": "0.2"})
            limite = int(q.get("limit", ["1"])[0])
            if mode == "plafond2":
                limite = min(limite, 2)
            apres = int(q.get("after", ["0"])[0])
            page = [m for m in membres if int(m["user"]["id"]) > apres and m["user"]["id"] != omis][:limite]
            return self.rendre(200, page)
        if u.path.startswith(base + "/"):
            uid = u.path.rsplit("/", 1)[1]
            if uid == omis and mode == "parti":
                return self.rendre(404, {"message": "Unknown Member", "code": 10007})
            if uid == omis and mode == "incomplet500":
                return self.rendre(500, {"message": "Internal Server Error", "code": 0})
            for m in membres:
                if m["user"]["id"] == uid:
                    return self.rendre(200, m)
            return self.rendre(404, {"message": "Unknown Member", "code": 10007})
        if u.path == f"/api/v10/guilds/{GUILD}/roles":
            return self.rendre(200, [{"id": i, "name": n} for i, n in ROLES])
        return self.rendre(404, {"message": "404: Not Found", "code": 0})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            corps = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            corps = None
        with open(JOURNAL, "a") as f:
            f.write(f"{open(MODE).read().strip()}\tPOST {self.path}\t{self.headers.get('Authorization')}\n")
        if u.path == "/api/v10/users/@me/channels" and isinstance(corps, dict) and corps.get("recipient_id"):
            rid = str(corps["recipient_id"])
            return self.rendre(200, {"id": "9" + rid, "type": 1, "recipients": [{"id": rid}]})
        parts = u.path.split("/")
        if len(parts) == 6 and parts[:4] == ["", "api", "v10", "channels"] and parts[5] == "messages" \
                and parts[4].startswith("9") and len(parts[4]) == 19:
            rid = parts[4][1:]
            mp["n"] += 1
            statut = "refuse" if rid in refusants() else "envoye"
            with open(MPJ, "a", encoding="utf-8") as f:
                f.write(json.dumps({"n": mp["n"], "destinataire": rid, "statut": statut, "corps": corps},
                                   ensure_ascii=False) + "\n")
            if statut == "refuse":
                return self.rendre(403, {"message": "Cannot send messages to this user", "code": 50007})
            return self.rendre(200, {"id": str(960000000000000000 + mp["n"]), "channel_id": parts[4],
                                     "content": (corps or {}).get("content")})
        return self.rendre(404, {"message": "404: Not Found", "code": 0})


ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
