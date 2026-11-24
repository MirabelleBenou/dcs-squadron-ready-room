"""Tests de tools/release.py (lot rr-release-auto, v1.0118) : git reel (depot temporaire + origin nu), API simulee, aucun acces
au reseau. Copie du modele de Mission Tools (634cc50), adaptee a A1 (tag RR-V), A2 (pas de piece jointe obligatoire) et A3."""
import base64
import hashlib
import importlib.util
import json
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Le depot a deja un `release.py` a la racine (la grille de version) : l'outil de publication se charge sous un autre nom.
_spec = importlib.util.spec_from_file_location('release_publication', ROOT / 'tools' / 'release.py')
release = importlib.util.module_from_spec(_spec)
sys.modules['release_publication'] = release
_spec.loader.exec_module(release)

REPO = 'owner/suite'
TOKEN = 'ghs_TOPSECRETTOKEN0123456789'
TITRE = 'RR-V2.0.0 — 20 November 2026'
# Lot « rr-release-v1-0-0 » (controle 7) : le CHANGELOG porte un bloc `### Version numbers` avant `## Unreleased`, et les notes
# de la release le recopient, mot pour mot, sous une derniere ligne `## Version numbers`.
VN = 'Each release is tagged `RR-V<major>.<minor>.<patch>`:\n\n- **Major**: a redesign.\n- **Minor**: a new tool.\n- **Patch**: fixes.'
CHANGELOG = (f'# Changelog\n\n### Version numbers\n\n{VN}\n\n## Unreleased\n\n### Added\n- z\n\n'
             '## RR-V2.0.0 — 2026-11-20\n\n### Added\n- y\n\n## [1.4.0] — 2026-11-08\n')
NOTES = f'Release text\n\n## Version numbers\n\n{VN}\n'
RELEASE_YML_SHA256 = 'ec56d2d0a2e5485c134639bd58ed6ced3a2c1df8e0c3af571bb76dae4fdf95f6'
HTML = b'<!DOCTYPE html><html>not really a page but bytes</html>'


@pytest.fixture(autouse=True)
def pas_de_reseau(monkeypatch):
    def interdit(*a, **k):
        raise AssertionError('network access in a test')
    monkeypatch.setattr(urllib.request, 'urlopen', interdit)
    monkeypatch.setattr(socket.socket, 'connect', interdit)


def git(cwd, *args):
    p = subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com', *args], cwd=str(cwd),
                       capture_output=True, text=True, encoding='utf-8')
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


class FakeApi:
    def __init__(self, repo=REPO):
        self.repo = repo
        self.calls = []                 # ('METHODE', chemin)
        self.releases = {}              # id -> dict
        self.tags = {}                  # tag -> sha
        self.assets = {}                # id -> [{'name', 'size'}]
        self.fail = {}                  # (methode, sous-chaine du chemin) -> (statut, objet)
        self.next_id = 100
        self.bodies = []

    @property
    def writes(self):
        return [c for c in self.calls if c[0] != 'GET']

    def request(self, methode, chemin, corps=None, fichier=None):
        self.calls.append((methode, chemin))
        for (m, sub), rep in self.fail.items():
            if m == methode and sub in chemin:
                return rep
        base = f'/repos/{self.repo}'
        if methode == 'GET' and chemin.startswith(f'{base}/git/ref/tags/'):
            t = chemin.rsplit('/', 1)[1]
            return (200, {'object': {'type': 'commit', 'sha': self.tags[t]}}) if t in self.tags else (404, {'message': 'Not Found'})
        if methode == 'GET' and chemin.startswith(f'{base}/releases?'):
            return 200, [dict(r) for r in self.releases.values()]
        if methode == 'POST' and chemin == f'{base}/releases':
            self.bodies.append(corps)
            self.next_id += 1
            self.releases[self.next_id] = dict(corps, id=self.next_id, upload_url=f'https://uploads.github.com{base}/releases/{self.next_id}/assets{{?name,label}}')
            self.assets[self.next_id] = []
            return 201, self.releases[self.next_id]
        if methode == 'POST' and chemin.startswith('https://uploads.github.com/'):
            rid = int(chemin.split('/releases/')[1].split('/')[0])
            nom = chemin.split('name=')[1]
            self.assets[rid].append({'name': nom, 'size': Path(fichier).stat().st_size})
            return 201, {'name': nom}
        if methode == 'GET' and '/assets' in chemin:
            rid = int(chemin.split('/releases/')[1].split('/')[0])
            return 200, self.assets[rid]
        if methode == 'PATCH':
            rid = int(chemin.rsplit('/', 1)[1])
            r = self.releases[rid]
            r.update(corps)
            self.tags[r['tag_name']] = r['target_commitish']
            return 200, r
        if methode == 'GET' and chemin.startswith(f'{base}/releases/tags/'):
            t = chemin.rsplit('/', 1)[1]
            for r in self.releases.values():
                if r['tag_name'] == t and not r['draft']:
                    return 200, r
            return 404, {'message': 'Not Found'}
        if methode == 'DELETE':
            del self.releases[int(chemin.rsplit('/', 1)[1])]
            return 204, None
        raise AssertionError(f'unexpected call {methode} {chemin}')


def monte(tmp_path, *, branche='release/RR-V2.0.0', tag='RR-V2.0.0', changelog=CHANGELOG, notes=NOTES,
          assets=None, manifeste=True, manifest_edit=None, main_avance=False, hors_release=False, extra_asset=None,
          essai=False):
    """Depot origin nu, un commit C sur main, la branche release, puis un clone `action` sur la tete de la branche."""
    origin = tmp_path / 'origin.git'
    subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(origin)], check=True)
    w = tmp_path / 'work'
    subprocess.run(['git', 'clone', '-q', str(origin), str(w)], check=True, capture_output=True)
    git(w, 'checkout', '-q', '-b', 'main')
    (w / 'CHANGELOG.md').write_text(changelog, encoding='utf-8')
    git(w, 'add', 'CHANGELOG.md')
    git(w, 'commit', '-q', '-m', 'C')
    c = git(w, 'rev-parse', 'HEAD')
    git(w, 'push', '-q', 'origin', 'main')
    git(w, 'checkout', '-q', '-b', branche)
    rel = w / '.release'
    (rel / 'assets').mkdir(parents=True)
    (rel / 'notes.md').write_text(notes, encoding='utf-8')
    if assets is None:
        assets = {'guide-fr.pdf': HTML, 'guide-en.pdf': HTML + b'2'}
    liste = []
    for nom, data in assets.items():
        (rel / 'assets' / nom).write_bytes(data)
        liste.append({'name': nom, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    if extra_asset:
        (rel / 'assets' / extra_asset).write_bytes(b'x')
    man = {'tag': tag, 'title': TITRE, 'commit': c, 'assets': liste}
    if manifest_edit:
        manifest_edit(man)
    if manifeste:
        (rel / 'manifest.json').write_text(json.dumps(man), encoding='utf-8')
    if hors_release:
        (w / 'README.md').write_text('sneaky', encoding='utf-8')
        git(w, 'add', 'README.md')
    git(w, 'add', '-A')
    git(w, 'commit', '-q', '-m', 'release files')
    git(w, 'push', '-q', 'origin', branche)
    if main_avance:
        git(w, 'checkout', '-q', 'main')
        (w / 'CHANGELOG.md').write_text(changelog + '\nmore\n', encoding='utf-8')
        git(w, 'commit', '-q', '-am', 'later')
        git(w, 'push', '-q', 'origin', 'main')
    act = tmp_path / 'action'
    subprocess.run(['git', 'clone', '-q', str(origin), str(act)], check=True, capture_output=True)
    git(act, 'checkout', '-q', '--detach', f'origin/{branche}')
    api = FakeApi()
    deps = release.Deps(release.Git(act), api, REPO, TOKEN, now=lambda: 1795000000)
    return deps, api, origin, c, branche


def sur_origin(origin, branche, chemin):
    p = subprocess.run(['git', 'show', f'{branche}:{chemin}'], cwd=str(origin), capture_output=True, text=True, encoding='utf-8')
    return p.stdout if p.returncode == 0 else None


def branches(origin):
    return subprocess.run(['git', 'branch', '--format=%(refname:short)'], cwd=str(origin), capture_output=True, text=True).stdout.split()


# ------------------------------------------------------------------ publication

def test_publication_reussie(tmp_path):
    deps, api, origin, c, br = monte(tmp_path)
    assert release.run(deps, br) == 0
    base = f'/repos/{REPO}'
    up = f'https://uploads.github.com{base}/releases/101/assets?name='
    assert api.calls == [
        ('GET', f'{base}/git/ref/tags/RR-V2.0.0'),
        ('GET', f'{base}/releases?per_page=100&page=1'),
        ('POST', f'{base}/releases'),
        ('POST', up + 'guide-fr.pdf'),
        ('POST', up + 'guide-en.pdf'),
        ('GET', f'{base}/releases/101/assets?per_page=100'),
        ('PATCH', f'{base}/releases/101'),
        ('GET', f'{base}/releases/tags/RR-V2.0.0'),
        ('GET', f'{base}/git/ref/tags/RR-V2.0.0'),
    ]
    b = api.bodies[0]
    assert b == {'tag_name': 'RR-V2.0.0', 'target_commitish': c, 'name': TITRE, 'body': NOTES,
                 'draft': True, 'prerelease': False}
    r = api.releases[101]
    assert r['draft'] is False and api.tags['RR-V2.0.0'] == c
    assert br not in branches(origin)


def test_pas_de_manifeste_aucun_appel(tmp_path, capsys):
    deps, api, origin, c, br = monte(tmp_path, manifeste=False)
    assert release.run(deps, br) == 0
    assert api.calls == []
    assert 'Waiting for the manifest' in capsys.readouterr().out
    assert br in branches(origin)
    assert sur_origin(origin, br, '.release/FAILED.md') is None


def _m_tag_branche(m):
    m['tag'] = 'RR-V1.8.0'


def _m_cle_en_trop(m):
    m['extra'] = 1


# (cas, options de monte, controle attendu, API avec une release existante ?)
DEFAUTS = [
    ('1-tag-different-de-la-branche', {'manifest_edit': _m_tag_branche}, '1'),
    ('1-cle-inconnue', {'manifest_edit': _m_cle_en_trop}, '1'),
    ('1-nom-de-branche', {'branche': 'release/autre'}, '1'),
    ('2-fichier-hors-release', {'hors_release': True}, '2'),
    ('2-commit-pas-tete-de-main', {'main_avance': True}, '2'),
    ('3-seulement-unreleased', {'changelog': '# Changelog\n\n## [Unreleased]\n'}, '3'),
    ('3-titre-d-une-autre-version', {'changelog': '# Changelog\n\n## [1.4.0] — 2026-11-08\n'}, '3'),
    ('5-fichier-en-trop', {'extra_asset': 'extra.pdf'}, '5'),
    ('5-nom-invalide', {'assets': {'mauvais nom.html': HTML}}, '5'),
    ('5-nom-avec-chemin', {'assets': {'../x.pdf': HTML}}, '5'),
    ('5-nom-avec-espace', {'assets': {'a b.pdf': HTML}}, '5'),
    ('6-notes-vides', {'notes': '  \n'}, '6'),
]


@pytest.mark.parametrize('cas,opts,controle', DEFAUTS, ids=[d[0] for d in DEFAUTS])
def test_controle_en_defaut(tmp_path, cas, opts, controle):
    deps, api, origin, c, br = monte(tmp_path, **opts)
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert f is not None and f'Control or step: {controle}' in f
    assert br in branches(origin)


def test_controle_4_tag_existant(tmp_path):
    deps, api, origin, c, br = monte(tmp_path)
    api.tags['RR-V2.0.0'] = 'a' * 40
    assert release.run(deps, br) == 1
    assert api.writes == []
    assert 'Control or step: 4' in sur_origin(origin, br, '.release/FAILED.md')


def test_controle_4_brouillon_existant(tmp_path):
    deps, api, origin, c, br = monte(tmp_path)
    api.releases[7] = {'id': 7, 'tag_name': 'RR-V2.0.0', 'draft': True}
    assert release.run(deps, br) == 1
    assert api.writes == []
    assert 'Control or step: 4' in sur_origin(origin, br, '.release/FAILED.md')


def test_controle_5_sha_different(tmp_path):
    def edit(m):
        m['assets'][0]['sha256'] = '0' * 64
    deps, api, origin, c, br = monte(tmp_path, manifest_edit=edit)
    assert release.run(deps, br) == 1
    assert api.writes == []
    assert 'SHA-256' in sur_origin(origin, br, '.release/FAILED.md')


def test_controle_5_taille_differente(tmp_path):
    def edit(m):
        m['assets'][0]['size'] += 1
    deps, api, origin, c, br = monte(tmp_path, manifest_edit=edit)
    assert release.run(deps, br) == 1
    assert 'size' in sur_origin(origin, br, '.release/FAILED.md')


def test_controle_5_aucune_entree_passe(tmp_path):
    # A2 : la release de l'App est l'archive « Source code » du tag ; zero piece jointe est valide et rien n'est televerse.
    deps, api, origin, c, br = monte(tmp_path, assets={})
    assert release.run(deps, br) == 0
    assert [p for m, p in api.calls if m == 'POST' and 'uploads' in p] == []
    assert [m for m, _ in api.writes] == ['POST', 'PATCH']
    assert api.assets[101] == [] and api.releases[101]['draft'] is False


def test_controle_5_aucune_entree_message(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, assets={}, branche='release/essai-un')
    assert release.run(deps, br) == 0
    l5 = sur_origin(origin, br, '.release/CHECK.md').strip().splitlines()[4]
    assert l5 == '5. OK - no asset: the release carries the source archive'


def test_controle_5_aucune_entree_mais_un_fichier_en_trop(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, assets={}, extra_asset='extra.pdf')
    assert release.run(deps, br) == 1
    assert api.writes == []
    assert 'not listed in the manifest' in sur_origin(origin, br, '.release/FAILED.md')


def test_televersement_en_echec_supprime_le_brouillon(tmp_path):
    deps, api, origin, c, br = monte(tmp_path)
    api.fail[('POST', 'uploads.github.com')] = (500, {'message': 'boom'})
    assert release.run(deps, br) == 1
    assert [m for m, _ in api.writes] == ['POST', 'POST', 'DELETE']
    assert api.releases == {}
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'step 2' in f and 'draft release was deleted' in f
    assert br in branches(origin)


# ------------------------------------------------------------------ essai

def test_essai_reussi(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-un', main_avance=True)
    assert release.run(deps, br) == 0
    assert api.writes == []
    check = sur_origin(origin, br, '.release/CHECK.md')
    lignes = check.strip().splitlines()
    assert len(lignes) == 7 and all(' OK ' in l for l in lignes)
    assert 'head of main: no' in lignes[1]
    assert br in branches(origin)
    assert sur_origin(origin, br, '.release/FAILED.md') is None


def test_essai_c_tete_de_main(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-un')
    assert release.run(deps, br) == 0
    assert 'head of main: yes' in sur_origin(origin, br, '.release/CHECK.md')


def test_essai_en_defaut(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-un', notes='')
    assert release.run(deps, br) == 1
    assert api.writes == []
    lignes = sur_origin(origin, br, '.release/CHECK.md').strip().splitlines()
    assert lignes[-1].startswith('6. FAILED') and all(' OK ' in l for l in lignes[:-1])
    assert sur_origin(origin, br, '.release/FAILED.md') is None


# ------------------------------------------------------------------ le jeton

def _b64():
    return base64.b64encode(f'x-access-token:{TOKEN}'.encode()).decode()


@pytest.mark.parametrize('essai', [False, True])
def test_jeton_jamais_ecrit(tmp_path, capsys, essai):
    opts = {'branche': 'release/essai-un'} if essai else {}
    deps, api, origin, c, br = monte(tmp_path, **opts)
    # l'API renvoie des erreurs qui citent le jeton (et sa forme base64) : au controle 4, puis a la creation du brouillon
    api.fail[('GET', 'git/ref/tags')] = (401, {'message': f'Bad credentials {TOKEN} {_b64()}'})
    assert release.run(deps, br) == 1
    sortie = capsys.readouterr().out
    nom = 'CHECK.md' if essai else 'FAILED.md'
    texte = sur_origin(origin, br, f'.release/{nom}')
    assert 'Bad credentials' in texte
    for t in (sortie, texte):
        assert TOKEN not in t and _b64() not in t


def test_jeton_dans_une_exception_et_au_televersement(tmp_path, capsys):
    deps, api, origin, c, br = monte(tmp_path)
    api.fail[('POST', 'uploads.github.com')] = (403, {'message': f'denied for {TOKEN}'})
    assert release.run(deps, br) == 1
    api.fail.clear()

    class Boum(FakeApi):
        def request(self, *a, **k):
            raise OSError(f'connection with {TOKEN} lost')
    deps2, api2, origin2, c2, br2 = monte(tmp_path / 'b')
    deps2.api = Boum()
    assert release.run(deps2, br2) == 1
    sortie = capsys.readouterr().out
    for o, b in ((origin, br), (origin2, br2)):
        assert TOKEN not in sur_origin(o, b, '.release/FAILED.md')
    assert TOKEN not in sortie and 'connection with' in sortie


def test_succes_sans_jeton_dans_la_sortie(tmp_path, capsys):
    deps, api, origin, c, br = monte(tmp_path)
    assert release.run(deps, br) == 0
    assert TOKEN not in capsys.readouterr().out


# ------------------------------------------------------------------ le workflow

def _workflow(nom):
    """Le workflow lu par yaml.safe_load. `.github/` est `export-ignore` : l'archive de deploiement ne le porte pas, le test
    ne joue alors que sur le depot (clone, CI) ; sur l'archive il est saute."""
    yaml = pytest.importorskip('yaml')
    f = ROOT / '.github' / 'workflows' / nom
    if not f.is_file():
        pytest.skip('.github/ is not part of the deployment archive')
    return yaml.safe_load(f.read_text(encoding='utf-8'))


def test_workflow():
    w = _workflow('release.yml')
    assert w['permissions'] == {'contents': 'write'}
    assert w[True]['push']['branches'] == ['release/**']          # `on` est lu comme True par YAML 1.1
    assert 'group' in w['concurrency']
    usages = [s['uses'] for j in w['jobs'].values() for s in j['steps'] if 'uses' in s]
    assert usages == ['actions/checkout@v4']
    assert all(j['runs-on'] == 'ubuntu-latest' and 'permissions' not in j for j in w['jobs'].values())
    assert any('tools/release.py' in s.get('run', '') for j in w['jobs'].values() for s in j['steps'])


def test_workflow_tests():
    # R4 : tests.yml, sur push vers main et sur pull_request ; lecture seule, aucun secret.
    w = _workflow('tests.yml')
    assert w['permissions'] == {'contents': 'read'}
    assert w[True]['push']['branches'] == ['main'] and 'pull_request' in w[True]
    jobs = list(w['jobs'].values())
    assert len(jobs) == 1 and jobs[0]['runs-on'] == 'ubuntu-latest' and 'permissions' not in jobs[0]
    brut = (ROOT / '.github' / 'workflows' / 'tests.yml').read_text(encoding='utf-8')
    assert 'secrets.' not in brut
    etapes = jobs[0]['steps']
    py = [e for e in etapes if str(e.get('uses', '')).startswith('actions/setup-python')]
    assert py and py[0]['with']['python-version'] == '3.12'
    runs = '\n'.join(e.get('run', '') for e in etapes)
    assert 'pip install -r requirements.txt pyflakes pytest' in runs
    assert '.env.example' in runs
    assert runs.index('python -m pytest -q') < runs.index('python -m pyflakes app/')


def test_workflow_release_identique_au_modele():
    # C1 : release.yml est la copie a l'octet du modele ; son empreinte est gelee ici (modele 634cc50).
    f = ROOT / '.github' / 'workflows' / 'release.yml'
    if not f.is_file():
        pytest.skip('.github/ is not part of the deployment archive')
    assert hashlib.sha256(f.read_bytes()).hexdigest() == RELEASE_YML_SHA256


# ------------------------------------------------------------------ fichiers en morceaux

GROS = b'<!DOCTYPE html>' + bytes(range(256)) * 40 + b'tail'
NOM_GROS = 'archive.bin'


def _en_morceaux(data, n=3):
    t = -(-len(data) // n)
    return [data[i:i + t] for i in range(0, len(data), t)]


def monte_morceaux(tmp_path, monkeypatch, parts=None, entier=None, sha=None, extra=None, **kw):
    """Depot avec le fichier NOM_GROS en morceaux ; le manifeste decrit le fichier entier."""
    rt = tmp_path / 'runner_temp'
    rt.mkdir()
    monkeypatch.setenv('RUNNER_TEMP', str(rt))
    deps, api, origin, c, br = monte(tmp_path / 'r', assets={'guide-fr.pdf': HTML}, **kw)
    # on ajoute les morceaux au depot de l'action, puis on met a jour le manifeste (sur la branche, localement)
    rel = deps.root / '.release'
    man = json.loads((rel / 'manifest.json').read_text(encoding='utf-8'))
    man['assets'].append({'name': NOM_GROS, 'size': len(GROS), 'sha256': sha or hashlib.sha256(GROS).hexdigest()})
    (rel / 'manifest.json').write_text(json.dumps(man), encoding='utf-8')
    morceaux = _en_morceaux(GROS) if parts is None else parts
    for i, d in enumerate(morceaux, 1):
        (rel / 'assets' / f'{NOM_GROS}.part{i:03d}').write_bytes(d)
    if entier:
        (rel / 'assets' / NOM_GROS).write_bytes(GROS)
    for nom in (extra or []):
        (rel / 'assets' / nom).write_bytes(b'x')
    return deps, api, origin, br, rt


class FakeApiCapture(FakeApi):
    def __init__(self):
        super().__init__()
        self.recus = {}

    def request(self, methode, chemin, corps=None, fichier=None):
        if methode == 'POST' and chemin.startswith('https://uploads.github.com/'):
            self.recus[chemin.split('name=')[1]] = Path(fichier).read_bytes()
        return super().request(methode, chemin, corps=corps, fichier=fichier)


def test_publication_en_trois_morceaux(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch)
    deps.api = FakeApiCapture()
    api = deps.api
    assert len(_en_morceaux(GROS)) == 3
    assert release.run(deps, br) == 0
    assert api.recus[NOM_GROS] == GROS and api.recus['guide-fr.pdf'] == HTML
    assert not any(NOM_GROS + '.part' in n for n in api.recus)
    assert api.assets[101] and sorted(a['name'] for a in api.assets[101]) == sorted([NOM_GROS, 'guide-fr.pdf'])
    assert api.releases[101]['draft'] is False
    assert list(rt.iterdir()) == []


def _echec(tmp_path, monkeypatch, attendu, **kw):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch, **kw)
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = deps.root / '.release' / 'FAILED.md'
    texte = f.read_text(encoding='utf-8')
    assert 'Control or step: 5' in texte and attendu in texte
    assert list(rt.iterdir()) == []
    return texte


def test_morceaux_avec_un_trou(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch)
    (deps.root / '.release' / 'assets' / f'{NOM_GROS}.part002').rename(deps.root / '.release' / 'assets' / f'{NOM_GROS}.part004')
    assert release.run(deps, br) == 1
    t = (deps.root / '.release' / 'FAILED.md').read_text(encoding='utf-8')
    assert NOM_GROS in t and 'continuous' in t and api.writes == []
    assert list(rt.iterdir()) == []


def test_morceaux_part001_part003(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch, parts=[GROS[:100], GROS[100:]])
    a = deps.root / '.release' / 'assets'
    (a / f'{NOM_GROS}.part002').rename(a / f'{NOM_GROS}.part003')
    assert release.run(deps, br) == 1
    assert f'{NOM_GROS}.part003' in (deps.root / '.release' / 'FAILED.md').read_text(encoding='utf-8')
    assert api.writes == []


def test_morceaux_et_entier_ensemble(tmp_path, monkeypatch):
    _echec(tmp_path, monkeypatch, f'asset {NOM_GROS} is present both whole and in parts', entier=True)


def test_morceau_de_trop_sans_nom(tmp_path, monkeypatch):
    _echec(tmp_path, monkeypatch, 'autre.bin.part001', extra=['autre.bin.part001'])


def test_sha_faux_apres_jonction(tmp_path, monkeypatch):
    _echec(tmp_path, monkeypatch, f'asset {NOM_GROS}: SHA-256 differs', sha='0' * 64)


def test_taille_fausse_apres_jonction(tmp_path, monkeypatch):
    _echec(tmp_path, monkeypatch, f'asset {NOM_GROS}: size', parts=_en_morceaux(GROS[:-1]))


def test_essai_avec_morceaux(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch, branche='release/essai-un')
    br = 'release/essai-un'
    assert release.run(deps, br) == 0
    assert api.writes == []
    lignes = (deps.root / '.release' / 'CHECK.md').read_text(encoding='utf-8').strip().splitlines()
    assert len(lignes) == 7 and all(' OK ' in l for l in lignes)
    assert '5. OK' in lignes[4] and 'joined from parts' in lignes[4]
    assert list(rt.iterdir()) == []


def test_jonction_sans_runner_temp(tmp_path, monkeypatch):
    monkeypatch.delenv('RUNNER_TEMP', raising=False)
    monkeypatch.setattr(release.tempfile, 'tempdir', str(tmp_path))
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch)
    monkeypatch.delenv('RUNNER_TEMP', raising=False)
    cree = []
    orig = release.Deps.dossier_temp
    monkeypatch.setattr(release.Deps, 'dossier_temp', lambda self: cree.append(orig(self)) or cree[-1])
    assert release.run(deps, br) == 0
    assert cree and not cree[0].exists() and not str(cree[0]).startswith(str(deps.root))


def test_joints_supprimes_apres_echec_au_televersement(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch)
    api.fail[('POST', 'uploads.github.com')] = (500, {'message': 'boom'})
    assert release.run(deps, br) == 1
    assert [m for m, _ in api.writes] == ['POST', 'POST', 'DELETE']
    assert list(rt.iterdir()) == [] and deps.joints == {}


# ------------------------------------------------------------------ adaptations de l'App (A1 a A3)

# A1 : le tag et la branche

def test_a1_branche_rr_v_publie(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/RR-V2.0.0', tag='RR-V2.0.0')
    assert release.run(deps, br) == 0
    assert api.releases[101]['tag_name'] == 'RR-V2.0.0'


@pytest.mark.parametrize('branche,tag', [('release/V2.0.0', 'V2.0.0'), ('release/MT-V2.0.0', 'MT-V2.0.0'),
                                         ('release/V2.0.0', 'RR-V2.0.0'), ('release/MT-V2.0.0', 'RR-V2.0.0'),
                                         ('release/v2.0.1', 'v2.0.1'), ('release/v2.0.1', 'RR-V2.0.1'),
                                         ('release/MT-v2.0.1', 'RR-V2.0.1'),
                                         ('release/MT-V1.0.0', 'MT-V1.0.0'), ('release/rr-v1.0.0', 'rr-v1.0.0'),
                                         ('release/RR-V1.0', 'RR-V1.0')])
def test_a1_autres_formes_refusees(tmp_path, branche, tag):
    deps, api, origin, c, br = monte(tmp_path, branche=branche, tag=tag)
    assert release.run(deps, br) == 1
    assert api.calls == [] and api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 1' in f and 'release/RR-V<x.y.z>' in f


def test_a1_manifeste_mt_v_sur_branche_essai(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-x', tag='MT-V2.0.0')
    assert release.run(deps, br) == 1
    assert api.calls == []
    t = sur_origin(origin, br, '.release/CHECK.md')
    assert t.strip().splitlines()[-1].startswith('1. FAILED') and 'must look like RR-V<x.y.z>' in t


# Controle 3 : le CHANGELOG du commit C

def _cl(titre):
    return f'# Changelog\n\n### Version numbers\n\n{VN}\n\n## Unreleased\n\n{titre}\n\n### Added\n- x\n'


def test_c3_titre_date_passe(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, changelog=_cl('## RR-V2.0.0 — 2026-11-20'))
    assert release.run(deps, br) == 0


def test_c3_message_de_reussite(tmp_path, capsys):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-un')
    assert release.run(deps, br) == 0
    assert '3. OK - CHANGELOG line "## RR-V2.0.0 — 2026-11-20" found for RR-V2.0.0' in sur_origin(origin, br, '.release/CHECK.md')


@pytest.mark.parametrize('ligne', [
    '', '## [1.4.0] — 2026-11-08', '## RR-V2.0.0', '## RR-V2.0.0 - 2026-11-20', '### RR-V2.0.0 — 2026-11-20',
    '## RR-V2.0.0 — 2026-11-20 extra', '## RR-V2x0x0 — 2026-11-20', ' ## RR-V2.0.0 — 2026-11-20', '## RR-V2.0.0 — 2026-11-2',
    '## [2.0.0] — 2026-11-20', '## v2.0.0 — 2026-11-20', '## MT-v2.0.0 — 2026-11-20'])
def test_c3_refus(tmp_path, ligne):
    deps, api, origin, c, br = monte(tmp_path, changelog=_cl(ligne))
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 3' in f
    assert 'CHANGELOG.md at the commit has no line "## RR-V2.0.0 — YYYY-MM-DD"' in f


def test_c3_points_echappes(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, tag='RR-V2.0.0', changelog=_cl('## RR-V2x0x0 — 2026-11-20'))
    assert release.run(deps, br) == 1


def test_c3_changelog_absent(tmp_path):
    deps, api, origin, c, br = monte(tmp_path)
    git(deps.root, 'checkout', '-q', '--detach', f'{c}')
    c2 = c  # le commit C porte CHANGELOG.md : on teste avec un manifeste dont C n'a pas le fichier
    m = {'tag': 'RR-V2.0.0', 'commit': c2}
    git(deps.root, 'rm', '-q', 'CHANGELOG.md')
    git(deps.root, 'commit', '-q', '-m', 'sans changelog')
    m['commit'] = git(deps.root, 'rev-parse', 'HEAD')
    with pytest.raises(release.Echec) as e:
        release._controle_changelog(deps, m)
    assert e.value.quoi == '3' and 'not found' in e.value.message


# Controle 3 sur le CHANGELOG.md de la base 4fedd14 (v1.0117) : copie GELEE dans ce test (jamais lue sur le depot : le fichier
# du depot change a chaque lot). Les lignes de titre sont celles de la base ; elles ne portent aucun titre RR-V.
CHANGELOG_BASE = (
    '# Changelog\n\n'
    'Tous les changements notables de la Squadron Ready Room.\n\n'
    '## Unreleased\n\n'
    '### v1.0117 — 2026-11-22\n- x\n\n'
    '### v1.0116 — 2026-11-21\n- y\n\n'
    '## v0.9 — 2026-01-01\n\n### v0.9.1 — 2026-01-01\n- z\n')


def _insere_release(texte, tag, date):
    """Ce que fait `release.py --release` : la ligne `## <tag> — <date>` sous `## Unreleased` et sa ligne vide."""
    return texte.replace('## Unreleased\n\n', f'## Unreleased\n\n## {tag} — {date}\n\n', 1)


def test_c3_vrai_changelog_de_la_base(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/RR-V1.0.0', tag='RR-V1.0.0', changelog=CHANGELOG_BASE)
    assert release.run(deps, br) == 1                      # aucun titre RR-V1.0.0 dans la base
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 3' in f and 'has no line "## RR-V1.0.0 — YYYY-MM-DD"' in f
    avec = _insere_release(CHANGELOG_BASE, 'RR-V1.0.0', '2026-12-01')
    assert '## RR-V1.0.0 — 2026-12-01' in avec
    # controle 7 : la copie gelee n'a pas de bloc « Version numbers » ; on l'ajoute au-dessus de `## Unreleased`
    avec = avec.replace('## Unreleased', f'### Version numbers\n\n{VN}\n\n## Unreleased', 1)
    deps, api, origin, c, br = monte(tmp_path / 'b', branche='release/RR-V1.0.0', tag='RR-V1.0.0', changelog=avec)
    assert release.run(deps, br) == 0
    assert api.releases[101]['tag_name'] == 'RR-V1.0.0'


# A2 : zero ou plusieurs pieces jointes ; A3 : textes propres au depot

@pytest.mark.parametrize('nom', ['guide-en.pdf', 'a.b_c-d.zip', '0x.bin', 'Guide.PDF'])
def test_a2_noms_conformes_passent(tmp_path, nom):
    deps, api, origin, c, br = monte(tmp_path, assets={nom: HTML})
    assert release.run(deps, br) == 0
    assert [a['name'] for a in api.assets[101]] == [nom]


def test_a2_une_piece_conforme_est_televersee(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, assets={'guide-en.pdf': HTML})
    assert release.run(deps, br) == 0
    ups = [p for m, p in api.calls if m == 'POST' and 'uploads' in p]
    assert [u.split('name=')[1] for u in ups] == ['guide-en.pdf']


@pytest.mark.parametrize('nom', ['../x.pdf', 'a b.pdf', '-x.pdf', '.x.pdf', 'x\u00e9.pdf'])
def test_a2_noms_refuses(tmp_path, nom):
    deps, api, origin, c, br = monte(tmp_path, assets={nom: HTML})
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 5' in f and '[A-Za-z0-9][A-Za-z0-9._-]*' in f


def test_a2_plus_de_marque_de_dev(tmp_path):
    assert not hasattr(release, 'MARQUE_DEV')
    page = HTML + b'<div data-dev-build>RR-V2.0.0+1</div>'
    deps, api, origin, c, br = monte(tmp_path, assets={'archive.bin': page})
    assert release.run(deps, br) == 0


def test_a3_televersement_type_du_nom(monkeypatch, tmp_path):
    envoyes = {}

    class Rep:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{}'

    def faux(req, timeout=None):
        envoyes['type'] = req.get_header('Content-type')
        envoyes['ua'] = req.get_header('User-agent')
        return Rep()

    monkeypatch.setattr(urllib.request, 'urlopen', faux)
    f = tmp_path / 'guide-fr.pdf'
    f.write_bytes(HTML)
    statut, _ = release.Api('tok').request('POST', 'https://uploads.github.com/x?name=guide-fr.pdf', fichier=str(f))
    assert statut == 201
    assert envoyes == {'type': 'application/pdf', 'ua': 'squadron-ready-room-release'}


def test_a3_publication_ordre_des_appels_avec_trois_fichiers(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, assets={'guide-fr.pdf': HTML, 'archive.bin': HTML + b'1'})
    assert release.run(deps, br) == 0
    ups = [p for m, p in api.calls if m == 'POST' and 'uploads' in p]
    assert [u.split('name=')[1] for u in ups] == ['guide-fr.pdf', 'archive.bin']


def test_fichier_en_morceaux_part001_part002(tmp_path, monkeypatch):
    deps, api, origin, br, rt = monte_morceaux(tmp_path, monkeypatch, parts=[GROS[:300], GROS[300:]])
    deps.api = FakeApiCapture()
    assert sorted(p.name for p in (deps.root / '.release' / 'assets').iterdir()) == [
        'archive.bin.part001', 'archive.bin.part002', 'guide-fr.pdf']
    assert release.run(deps, br) == 0
    assert deps.api.recus['archive.bin'] == GROS


def test_a3_type_par_defaut(monkeypatch, tmp_path):
    envoyes = []

    class Rep:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{}'

    def faux(req, timeout=None):
        envoyes.append(req.get_header('Content-type'))
        return Rep()

    monkeypatch.setattr(urllib.request, 'urlopen', faux)
    noms = ['archive.bin', 'sansext', 'paquet.tar.gz', 'page.html']
    for nom in noms:
        f = tmp_path / nom
        f.write_bytes(HTML)
        statut, _ = release.Api('tok').request('POST', 'https://uploads.github.com/x?name=' + nom, fichier=str(f))
        assert statut == 201
    assert envoyes == ['application/octet-stream', 'application/octet-stream',
                       'application/octet-stream', 'text/html']


# Controle 7 : le paragraphe « Version numbers » des notes egale celui de l'en-tete du CHANGELOG (lot « rr-release-v1-0-0 »)

def test_c7_paragraphe_juste_passe(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, branche='release/essai-un')
    assert release.run(deps, br) == 0
    lignes = sur_origin(origin, br, '.release/CHECK.md').strip().splitlines()
    assert lignes[6] == '7. OK - "Version numbers" paragraph matches the CHANGELOG header'
    assert api.writes == []


def test_c7_paragraphe_absent(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, notes='Release text\n')
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 7' in f and 'notes.md has no "## Version numbers" paragraph' in f
    assert br in branches(origin)


def test_c7_un_mot_change(tmp_path):
    deps, api, origin, c, br = monte(tmp_path, notes=NOTES.replace('a redesign', 'a redraw'))
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 7' in f
    assert 'the "Version numbers" paragraph of notes.md differs from the CHANGELOG header' in f


def test_c7_changelog_sans_bloc(tmp_path):
    sans = '# Changelog\n\n## Unreleased\n\n## RR-V2.0.0 — 2026-11-20\n\n### Added\n- y\n'
    deps, api, origin, c, br = monte(tmp_path, changelog=sans)
    assert release.run(deps, br) == 1
    assert api.writes == []
    f = sur_origin(origin, br, '.release/FAILED.md')
    assert 'Control or step: 7' in f
    assert 'CHANGELOG.md at the commit has no "### Version numbers" block before "## Unreleased"' in f
