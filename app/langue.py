"""Lot « rr-public-pages-bilingues » (v1.0121) : la langue des pages d'avant la connexion
(connexion, accès refusé, lien d'entrée), des réponses de `POST /auth/lien` et de la
commande Discord `/readyroom`.

Une fonction pure choisit la langue (`?lang`, puis le cookie `rr_langue`, puis
`Accept-Language`) ; un seul dictionnaire, par langue, porte les textes. La langue de
l'App une fois connecté (celle du profil) n'en dépend pas.
"""
from __future__ import annotations

LANGUES = ("fr", "en")
COOKIE = "rr_langue"
UN_AN = 365 * 24 * 3600

# Les textes, une langue par entrée. Rien n'est écrit en dur deux fois.
TEXTES: dict[str, dict[str, str]] = {
    "fr": {
        "selecteur": "Langue",
        "login_titre": "Squadron Ready Room — Connexion",
        "login_paragraphe": "Accès réservé aux membres autorisés de l'escadre.",
        "login_bouton": "Se connecter avec Discord",
        "noaccess_titre_page": "Squadron Ready Room — Accès refusé",
        "noaccess_titre": "Accès refusé",
        "noaccess_compte": "Compte Discord utilisé :",
        "noaccess_non_membre": "Ce compte n'est pas membre du serveur Discord de l'escadre.",
        "noaccess_sans_role": "Ce compte n'a aucun rôle qui ouvre la Ready Room.",
        "noaccess_mauvais_compte": "Pas le bon compte ? Déconnecte-toi de Discord dans ce navigateur, sur discord.com, puis réessaie.",
        "noaccess_commande": "Tu peux aussi taper /readyroom dans le serveur Discord de l'escadre : tu recevras un lien d'entrée.",
        "noaccess_fin": "Sinon, contacte le staff.",
        "noaccess_bouton": "Retour",
        "lien_titre_page": "Squadron Ready Room — Lien de connexion",
        "lien_paragraphe": "Lien de connexion de secours. Il ouvre ta session une seule fois.",
        "lien_bouton": "Entrer",
        "lien_incomplet": "Ce lien est incomplet : ouvre-le tel qu'il t'a été remis.",
        "lien_echec": "La connexion n'a pas abouti. Réessaie dans un instant.",
        "auth_415": "Le corps doit être du JSON.",
        "auth_403_origine": "Origine refusée.",
        "auth_400": "Lien invalide.",
        "auth_410": "Ce lien a expiré ou a déjà servi. Demandes-en un nouveau : tape /readyroom dans le serveur Discord de l'escadre, ou adresse-toi au staff.",
        "auth_403_droit": "Ton compte n'a plus accès à la Ready Room — contacte le staff.",
        "cmd_inconnue": "Commande inconnue.",
        "cmd_hors_serveur": "Tape cette commande dans le serveur Discord de l'escadre.",
        "cmd_sans_acces": "Ton compte Discord n'a pas accès à la Ready Room — contacte le staff.",
        "cmd_erreur": "La Ready Room n'a pas pu préparer ton lien. Réessaie dans un instant.",
        "cmd_lien": "Ton lien d'entrée dans la Ready Room : valable 5 minutes, une seule fois. Ne le partage pas.",
        "cmd_bouton": "Entrer dans la Ready Room",
    },
    "en": {
        "selecteur": "Language",
        "login_titre": "Squadron Ready Room — Sign in",
        "login_paragraphe": "Access restricted to the wing's authorised members.",
        "login_bouton": "Sign in with Discord",
        "noaccess_titre_page": "Squadron Ready Room — Access denied",
        "noaccess_titre": "Access denied",
        "noaccess_compte": "Discord account used:",
        "noaccess_non_membre": "This account is not a member of the wing's Discord server.",
        "noaccess_sans_role": "This account has no role that opens the Ready Room.",
        "noaccess_mauvais_compte": "Wrong account? Sign out of Discord in this browser, on discord.com, then try again.",
        "noaccess_commande": "You can also type /readyroom in the wing's Discord server: you will receive an entry link.",
        "noaccess_fin": "Otherwise, contact the staff.",
        "noaccess_bouton": "Back",
        "lien_titre_page": "Squadron Ready Room — Sign-in link",
        "lien_paragraphe": "Backup sign-in link. It opens your session once only.",
        "lien_bouton": "Enter",
        "lien_incomplet": "This link is incomplete: open it exactly as you received it.",
        "lien_echec": "Sign-in failed. Try again in a moment.",
        "auth_415": "The body must be JSON.",
        "auth_403_origine": "Origin refused.",
        "auth_400": "Invalid link.",
        "auth_410": "This link has expired or has already been used. Ask for a new one: type /readyroom in the wing's Discord server, or ask the staff.",
        "auth_403_droit": "Your account no longer has access to the Ready Room — contact the staff.",
        "cmd_inconnue": "Unknown command.",
        "cmd_hors_serveur": "Type this command in the wing's Discord server.",
        "cmd_sans_acces": "Your Discord account has no access to the Ready Room — contact the staff.",
        "cmd_erreur": "The Ready Room could not prepare your link. Try again in a moment.",
        "cmd_lien": "Your entry link to the Ready Room: valid for 5 minutes, once only. Do not share it.",
        "cmd_bouton": "Enter the Ready Room",
    },
}

DESCRIPTION_COMMANDE = {
    "en": "Get a link to enter the Ready Room when Discord sign-in fails",
    "fr": "Recevoir un lien pour entrer dans la Ready Room, si la connexion Discord ne passe pas",
}


def _valide(valeur: str | None) -> str | None:
    return valeur if valeur in LANGUES else None


def _langue_preferee(accept_language: str | None) -> str | None:
    """La sous-étiquette primaire de la langue préférée (le plus haut `q`, le premier à
    `q` égal), ou `None` si l'en-tête est vide ou illisible."""
    meilleure: tuple[float, str] | None = None
    for morceau in (accept_language or "").split(","):
        parties = [p.strip() for p in morceau.split(";")]
        etiquette = parties[0].lower()
        if not etiquette:
            continue
        q = 1.0
        for p in parties[1:]:
            if p.lower().startswith("q="):
                try:
                    q = float(p[2:])
                except ValueError:
                    q = -1.0
        if q < 0 or q > 1:
            continue
        if meilleure is None or q > meilleure[0]:
            meilleure = (q, etiquette.split("-")[0])
    return meilleure[1] if meilleure else None


def langue_de(param: str | None, cookie: str | None, accept_language: str | None) -> str:
    """`fr` ou `en` : `param`, puis le cookie, puis `Accept-Language` ; `en` à défaut."""
    choisie = _valide(param) or _valide(cookie)
    if choisie:
        return choisie
    return "fr" if _langue_preferee(accept_language) == "fr" else "en"


def langue_requete(request) -> str:
    """La langue d'une requête : le cookie `rr_langue`, puis l'en-tête (pas de `param`)."""
    return langue_de(None, request.cookies.get(COOKIE), request.headers.get("accept-language"))


def textes(langue: str) -> dict[str, str]:
    return TEXTES[langue if langue in TEXTES else "en"]


def langue_discord(locale: str | None) -> str:
    """La langue d'une interaction Discord : `fr` si le `locale` commence par `fr`, sinon `en`."""
    return "fr" if isinstance(locale, str) and locale.lower().startswith("fr") else "en"
