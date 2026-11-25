"""Mesure commune à tous les lots -- lecture seule, jamais dans la zip.
Usage : python3 -B mesure_commune.py <base> <mesure>
Rend, pour chaque racine, l'état du CHANGELOG et la fiche Francfort ; puis
l'écart de fichiers entre les deux racines. Rien n'est écrit dans les
racines mesurées : la fiche se calcule dans un sous-processus en -B."""
import collections, difflib, os, pathlib, re, subprocess, sys

FICHE = """
import json, sys; sys.path.insert(0, '.')
from app import llm
from app.debrief.report_facts import build_report_facts
fx = json.load(open('tests/fixtures/89f20c83-54ec-4fd4-bf0c-1700463ff155.json', encoding='utf-8'))
f = build_report_facts(fx['flights'], fx)
print('fiche :', f['report_facts_sha'], '·', f['counts']['faits'], 'faits ·', [p['n_faits'] for p in f['paragraphes']], '·',
      len(json.dumps(f, sort_keys=True, separators=(',', ':'), ensure_ascii=False)), 'car. · consigne', len(llm._PROMPT_TEMPLATE))
"""

def section_unreleased(lignes):
    """(indice de la ligne exacte `## Unreleased`, indice de la ligne suivante qui commence par `## ` ou fin) ;
    `(None, None)` sans cette ligne."""
    debut = next((i for i, l in enumerate(lignes) if l == "## Unreleased"), None)
    if debut is None:
        return None, None
    fin = next((i for i in range(debut + 1, len(lignes)) if lignes[i].startswith("## ")), len(lignes))
    return debut, fin

def ecart_changelog(base, mesure):
    """Banc v8 (porte P11) : le diff ligne à ligne des deux `CHANGELOG.md`, lignes sans fin de ligne."""
    a = (pathlib.Path(base) / "CHANGELOG.md").read_text(encoding="utf-8").split("\n")
    b = (pathlib.Path(mesure) / "CHANGELOG.md").read_text(encoding="utf-8").split("\n")
    debut, fin = section_unreleased(b)
    ajoutees, retirees = [], 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("insert", "replace"):
            ajoutees += [(j, b[j]) for j in range(j1, j2) if b[j].strip()]
        if op in ("delete", "replace"):
            retirees += sum(1 for l in a[i1:i2] if l.strip())
    hors = sum(1 for j, _ in ajoutees if debut is None or not debut < j < fin)
    entetes = sum(1 for _, l in ajoutees if l.startswith("# ") or l.startswith("## "))
    return (f"changelog : +{len(ajoutees)} lignes ajoutées, {hors} hors de « ## Unreleased » · "
            f"−{retirees} lignes retirées · {entetes} en-têtes neufs")

def etat(racine):
    racine = pathlib.Path(racine).resolve()
    print(f"== {racine.name}")
    ch = (racine / "CHANGELOG.md").read_text(encoding="utf-8")
    # Banc v8 (porte P11) : les versions publiées sont les en-têtes `## RR-V<x.y.z>` (suivis d'un blanc ou de la fin
    # de ligne) ; la dernière est la première du fichier. `u` : les lignes non vides de la section `## Unreleased`.
    pub = re.findall(r"(?m)^## (RR-V\d+\.\d+\.\d+)(?=\s|$)", ch)
    dbl = sorted(v for v, n in collections.Counter(pub).items() if n > 1)
    debut, fin = section_unreleased(ch.split("\n"))
    u = "—" if debut is None else sum(1 for l in ch.split("\n")[debut + 1:fin] if l.strip())
    print(f"changelog : {len(pub)} versions publiées (dernière {pub[0] if pub else '—'}) · doublons {dbl or 'aucun'} · "
          f"{u} lignes sous « ## Unreleased »")
    env = dict(os.environ)
    for l in (racine / ".env.example").read_text(encoding="utf-8").splitlines():
        if l.strip() and not l.lstrip().startswith("#") and "=" in l:
            k, v = l.split("=", 1); env[k.strip()] = v.strip()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-B", "-c", FICHE], capture_output=True, text=True, cwd=racine, env=env)
    print(r.stdout.strip() or f"fiche : ÉCHEC ({r.stderr.strip()[-300:]})")

def fichiers(racine):
    racine = pathlib.Path(racine)
    return {str(p.relative_to(racine)): p.read_bytes() for p in racine.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts and p.suffix != ".pyc"}

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    if len(sys.argv) != 3:
        sys.exit("usage : python3 -B mesure_commune.py <base> <mesure>")
    for r in sys.argv[1:]:
        etat(r)
    a, b = fichiers(sys.argv[1]), fichiers(sys.argv[2])
    print("== écart base → mesure")
    print(ecart_changelog(sys.argv[1], sys.argv[2]))
    print("modifiés :", sorted(k for k in a.keys() & b.keys() if a[k] != b[k]))
    print("ajoutés  :", sorted(b.keys() - a.keys()), "· retirés :", sorted(a.keys() - b.keys()))
