#!/bin/bash
# Rituel de reprise — une commande, toutes les grandeurs. $1 = racine du paquet déballé.
R="${1:?usage: rituel.sh <racine_du_paquet>}"
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
# ⚠ Le paquet doit être FRAÎCHEMENT déballé : un arbre où l'on a exécuté du
# Python porte des .pyc qui faussent le décompte. Le compte de .pyc DOIT être 0.
# Empreinte du moteur : ast.dump depuis le lot « Le passage moteur » (v1.0003) --
# même valeur sur tous les correctifs d'une version mineure de Python, donc
# comparable à la production. La ligne « application » la fait calculer par
# app/debrief/revision.py lui-même (python -B : aucun .pyc) : les deux doivent
# être égales.
echo "VERSION        : $(cat "$R/VERSION")"
echo "fichiers       : $(find "$R" -type f ! -name '*.pyc' | wc -l) hors .pyc · $(find "$R" -type f -name '*.pyc' | wc -l) .pyc · $(find "$R" -name cssrules.py | wc -l) cssrules · $(find "$R" -type f -name '.*' | wc -l) cachés"
echo "cachés         : $(cd "$R" && find . -type f -name '.*' | sort | tr '\n' ' ')"
echo "migrations     : $(ls "$R"/alembic/versions/*.py | wc -l)"
printf "routes         : "
for f in app/api.py app/debrief/api.py app/command/api.py; do
  printf "%s " "$(grep -cE '^@router\.(get|post|put|patch|delete)' "$R/$f")"
done; echo "(api · debrief · command)"
echo "--- CSS (instrument, jamais grep) ---"
"$PY" cssrules.py "$R/app/static/styles.css" | sed 's/^/  /'
echo "--- i18n (évaluation réelle, jamais motif de ligne) ---"
node -e '
const fs=require("fs"), s=fs.readFileSync(process.argv[1],"utf8");
const i=s.indexOf("const I18N = {"); let j=s.indexOf("{",i), d=0, k=j;
for(;k<s.length;k++){ if(s[k]==="{")d++; else if(s[k]==="}"){d--; if(d===0){k++;break;}} }
const o=(0,eval)("("+s.slice(j,k)+")"), fr=Object.keys(o.fr), en=Object.keys(o.en);
const sf=new Set(fr), se=new Set(en);
console.log("  fr "+fr.length+" · en "+en.length+" · doublons "+(fr.length-sf.size)+"/"+(en.length-se.size)+" · manquantes "+[...sf].filter(x=>!se.has(x)).length+"/"+[...se].filter(x=>!sf.has(x)).length);
' "$R/app/static/app.js"
echo "--- empreinte du moteur ---"
( cd "$R/app/debrief" && "$PY" -c "
import ast,hashlib
# banc v6 : la liste des modules est celle de _MODULES dans revision.py de l'archive mesurée, lue sans l'importer
# (ast.literal_eval) : la formule reste calculée ici, à part de celle de l'application.
def modules():
    for n in ast.parse(open('revision.py',encoding='utf-8').read()).body:
        cibles=[n.target] if isinstance(n,ast.AnnAssign) else (n.targets if isinstance(n,ast.Assign) else [])
        if any(isinstance(c,ast.Name) and c.id=='_MODULES' for c in cibles) and n.value is not None:
            return ast.literal_eval(n.value)
    raise SystemExit('  ENGINE_REVISION : _MODULES introuvable dans app/debrief/revision.py')
m=modules()
def s(t):
    for n in ast.walk(t):
        if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
            b=n.body
            if b and isinstance(b[0],ast.Expr) and isinstance(b[0].value,ast.Constant) and isinstance(b[0].value.value,str): b.pop(0)
    return t
print('  ENGINE_REVISION :', hashlib.sha256(''.join(f+ast.dump(s(ast.parse(open(f,encoding='utf-8').read()))) for f in m).encode()).hexdigest()[:12])
" )
( cd "$R" && "$PY" -B -c "
import sys; sys.path.insert(0, '.')
from app.debrief.revision import ENGINE_REVISION
print('  application     :', ENGINE_REVISION, '· python', sys.version.split()[0])
" )
