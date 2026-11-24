"""Lot « Polish du Centre » -- le journal des modifications du Centre de
Commandement.

Chaque écriture du Centre qui change quelque chose y laisse une ligne
(`CommandJournal`) : qui, quand, quoi, sur quel objet, l'avant et l'après.
Trois fonctions :

- `ecarts` écrit les lignes de détail, d'un état avant à un état après ;
- `lisibles` les rend lisibles à la lecture (les comptes par leur nom) ;
- `consigner` ajoute la ligne au journal, DANS la transaction de la route,
  avant son `commit` -- l'écriture et sa trace tiennent ou tombent ensemble.

`ecarts` et `lisibles` sont pures. Le journal ne s'écrit que par `consigner` ;
aucune route ne le modifie ni ne l'efface.
"""
from __future__ import annotations

from typing import Any

from app.models import CommandJournal

# Les champs dont la valeur est un identifiant de profil : l'écran les lit par le nom.
_CHAMPS_PROFILS = ("profile_id", "profile_ids")


def ecarts(avant: dict, apres: dict) -> list[dict]:
    """Les lignes de détail d'une écriture. Pure. Pour chaque clé de `apres`,
    dans son ordre :

    - deux listes : `{"champ", "ajoutes", "retires"}` -- `ajoutes` vaut `apres`
      moins `avant` (dans l'ordre d'`apres`), `retires` vaut `avant` moins
      `apres` (dans l'ordre d'`avant`), les éléments rendus en texte ; la ligne
      ne s'écrit que si l'une des deux est non vide ;
    - sinon, deux valeurs qui diffèrent : `{"champ", "avant", "apres"}` ;
    - sinon, rien.

    Une clé absente d'`avant` y vaut `None` : c'est ce qui écrit une valeur
    « posée »."""
    lignes: list[dict] = []
    for champ, nouveau in apres.items():
        ancien = avant.get(champ)
        if isinstance(ancien, list) and isinstance(nouveau, list):
            avant_txt = [str(v) for v in ancien]
            apres_txt = [str(v) for v in nouveau]
            ajoutes = [v for v in apres_txt if v not in avant_txt]
            retires = [v for v in avant_txt if v not in apres_txt]
            if ajoutes or retires:
                lignes.append({"champ": champ, "ajoutes": ajoutes, "retires": retires})
        elif ancien != nouveau:
            lignes.append({"champ": champ, "avant": ancien, "apres": nouveau})
    return lignes


def _nommer(valeur: Any, noms: dict[str, str]) -> Any:
    """Un identifiant de profil -> son nom ; un identifiant inconnu reste tel
    quel ; une liste se nomme élément par élément ; `None` reste `None`."""
    if isinstance(valeur, list):
        return [_nommer(v, noms) for v in valeur]
    if valeur is None:
        return None
    return noms.get(str(valeur), valeur)


def lisibles(lignes: list[dict], noms: dict[str, str]) -> list[dict]:
    """Les lignes servies à l'écran. Pure. Pour les champs `profile_id` et
    `profile_ids`, chaque identifiant devient son nom (`noms`, identifiant en
    texte -> nom) ; un identifiant inconnu reste tel quel. Les rôles restent des
    identifiants -- l'écran les nomme --, et tout le reste passe tel quel."""
    out: list[dict] = []
    for ligne in lignes:
        ligne = dict(ligne)
        if ligne.get("champ") in _CHAMPS_PROFILS:
            for cle in ("avant", "apres", "ajoutes", "retires"):
                if cle in ligne:
                    ligne[cle] = _nommer(ligne[cle], noms)
        out.append(ligne)
    return out


def consigner(
    db,
    user: dict,
    action: str,
    *,
    objet: str | None = None,
    lignes: list[dict] | None = None,
    toujours: bool = False,
) -> bool:
    """Ajoute une ligne au journal, dans la transaction de la route et AVANT
    son `commit`. N'ajoute rien si `lignes` est vide et que `toujours` est faux
    -- une écriture qui ne change rien ne se consigne pas. Rend `True` si elle
    a ajouté une ligne."""
    lignes = list(lignes or [])
    if not lignes and not toujours:
        return False
    db.add(
        CommandJournal(
            par_id=int(user["id"]), action=action, objet=objet, lignes=lignes
        )
    )
    return True
