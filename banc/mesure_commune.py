"""Mesure commune à tous les lots -- lecture seule, jamais dans la zip.
Usage : python3 -B mesure_commune.py <base> <mesure>
Rend, pour chaque racine, l'état du CHANGELOG et la fiche Francfort ; puis
l'écart de fichiers entre les deux racines. Rien n'est écrit dans les
racines mesurées : la fiche se calcule dans un sous-processus en -B."""
import collections, os, pathlib, re, subprocess, sys

FICHE = """
import json, sys; sys.path.insert(0, '.')
from app import llm
from app.debrief.report_facts import build_report_facts
fx = json.load(open('tests/fixtures/89f20c83-54ec-4fd4-bf0c-1700463ff155.json', encoding='utf-8'))
f = build_report_facts(fx['flights'], fx)
print('fiche :', f['report_facts_sha'], '·', f['counts']['faits'], 'faits ·', [p['n_faits'] for p in f['paragraphes']], '·',
      len(json.dumps(f, sort_keys=True, separators=(',', ':'), ensure_ascii=False)), 'car. · consigne', len(llm._PROMPT_TEMPLATE))
"""

def etat(racine):
    racine = pathlib.Path(racine).resolve()
    print(f"== {racine.name}")
    ch = (racine / "CHANGELOG.md").read_text(encoding="utf-8")
    ent = re.findall(r"(?m)^#{2,3} (v[\d.]+)", ch)
    dbl = sorted(v for v, n in collections.Counter(ent).items() if n > 1)
    print(f"changelog : {ch.count('<à compléter>')} « à compléter » · {len(ent)} en-têtes · doublons {dbl or 'aucun'} · "
          f"premier en-tête {ent[0] if ent else '—'}")
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
    print("modifiés :", sorted(k for k in a.keys() & b.keys() if a[k] != b[k]))
    print("ajoutés  :", sorted(b.keys() - a.keys()), "· retirés :", sorted(a.keys() - b.keys()))
