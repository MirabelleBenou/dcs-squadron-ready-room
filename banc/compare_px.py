"""Compare au pixel deux dossiers de rendus -- instrument du banc, lecture seule.
Usage : python3 -B compare_px.py <dossier_A> <dossier_B> [motif_inclus] [motif_exclu]
Les fichiers .png de même nom se comparent ; un fichier présent d'un seul côté est signalé.
Rend, par fichier : IDENTIQUE, ou le nombre de pixels qui diffèrent, l'écart maximal par canal
et le rectangle qui les contient. Code de sortie 1 s'il y a le moindre écart."""
import os, re, sys
from PIL import Image, ImageChops

a, b = sys.argv[1], sys.argv[2]
inc = re.compile(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else None
exc = re.compile(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] else None
garde = lambda f: f.endswith(".png") and (not inc or inc.search(f)) and (not exc or not exc.search(f))
fa, fb = {f for f in os.listdir(a) if garde(f)}, {f for f in os.listdir(b) if garde(f)}
ecart = 0
for f in sorted(fa | fb):
    if f not in fa or f not in fb:
        print(f"ABSENT d'un côté : {f}"); ecart = 1; continue
    ia, ib = Image.open(os.path.join(a, f)).convert("RGB"), Image.open(os.path.join(b, f)).convert("RGB")
    if ia.size != ib.size:
        print(f"TAILLE {ia.size} ≠ {ib.size} : {f}"); ecart = 1; continue
    d = ImageChops.difference(ia, ib); box = d.getbbox()
    if not box:
        continue
    px = sum(1 for v in d.convert("L").getdata() if v)
    print(f"ÉCART {px} px · max {max(e[1] for e in d.getextrema())} · zone {box} : {f}"); ecart = 1
print(f"{len(fa & fb)} comparés · {'aucun écart' if not ecart else 'ÉCARTS ci-dessus'}")
sys.exit(ecart)
