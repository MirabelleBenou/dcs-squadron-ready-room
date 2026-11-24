"""Lanceur d'uvicorn pour le Centre (banc v4) -- depuis la copie d'essai (cwd). L'API Discord du bot
pointe sur le faux serveur (port 8999) ; l'appel de démarrage est repoussé d'une heure, pour que seuls
les appels demandés par le scénario tournent pendant un rendu. Rien d'autre n'est touché."""
import os, sys
sys.path.insert(0, os.getcwd())
import app.discord_rsvp as d
d._API_BASE = "http://127.0.0.1:8999/api/v10"
import app.appel as a
a.DELAI_DEMARRAGE_S = 3600
import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
