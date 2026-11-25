# Banc d'essai — Ready Room · v8 · 25 novembre 2026

Outils du dev et du CdP. **Lecture seule pour la production ; rien de ce banc n'entre dans une archive.**
*v1 : éprouvé au lot « L'effectif complet » (`v1.0016`). v2 : le rendu des écrans D et E, au pixel. v3 : tout
l'outillage en un seul zip. **v4 : le Centre de Commandement (écrans Droits et Membres) et le scénario des relances,
MP compris, sous une horloge de scénario ; un faux Discord qui reçoit les MP ; la réception à froid du CdP, en phases.**
Le v3 est intact : tout fichier du v3 est identique à l'octet, sauf ce `README` et `faux_discord.py` (qui ne fait
qu'ajouter) (noms pseudonymisés au v1.0114). Le banc est tenu par le dev ; il évolue par un lot.*
*v5 (lot « Le banc v5 ») : **le semis du Débrief** (deux sessions de la fixture « Bataille de Francfort », deux campagnes,
40 vols et leurs évènements), **l'instrument de rendu de l'écran A** (le dossier du pilote), et **la réception allégée**
(maquette facultative, PostgreSQL 16 et libfaketime seulement pour les phases qui rendent, empreinte du code facultative).
Le v4 est resté intact : les 24 fichiers autres que ce `README` et `reception.sh` sont identiques à l'octet — `prepare_base.sh`,
`semis.py`, `semis_e.py`, `rendu_de.py` et `rendu_cc.py` compris : les recettes de D, de E et du Centre ne bougent pas (noms pseudonymisés au v1.0114).*
*v6 (lot « Les dettes hors plume ») : **Python 3.12 sans shim** (variable `PY`) ; **le rituel lit la liste des modules du moteur** dans l'archive
mesurée ; **libfaketime seulement pour les phases du Centre** ; **le pied de version masqué** dans les trois instruments de rendu ;
**Hunter, adjoint non administrateur**, consigné au semis ; **des sessions semées avec une durée** ; **un vrai `debrief.log` à déposer** par l'API.
Voir « Ce qui a changé au v6 » plus bas. Le v5 est resté intact hors de ce `README`, des 13 fichiers modifiés et des 2 fichiers ajoutés qui y sont listés.*
*v8 (lot « Le banc et les droits », `RR-V1.0.0+1`) : **la phase `droits` de la réception**, **le semis qui pose `app.access` au rôle Pilote**, **la sonde des relances qui lit un ensemble**
et **la mesure commune qui lit le `CHANGELOG` au format `RR-V`**. Voir « Ce qui a changé au v8 » plus bas.*

## Disposition attendue (chemins écrits en dur)

- `/home/claude/rr/harness/` — ce banc, déballé ici ;
- `/home/claude/rr/test.env` — l'environnement de test (copie de `test.env`, sans secret) ;
- les copies de l'application se passent en argument (`prepare_base.sh`, `servir.sh`) ;
- **v6 — Python 3.12, sans shim `PATH`** : tout appel à Python du banc passe par la variable `PY`, par défaut `python3.12`
  (`export PY=…` pour une autre commande). Les recettes de ce `README` écrivent donc `python3.12`. Les dépendances de
  l'application et du banc s'installent pour cette version : `python3.12 -m pip install … pip-audit==2.10.1` (v7 : la phase `statique` de `reception.sh` joue `pip-audit` sur le `requirements.txt` de la livraison).

## Les pièces

| fichier | rôle |
|---|---|
| `rituel_reprise.sh <racine>` | **le rituel** : version, fichiers, migrations, routes, CSS à l'instrument, i18n évaluée, empreinte du moteur. Se lance **depuis ce dossier** (`cssrules.py` doit être dans le répertoire courant). |
| `cssrules.py` | l'instrument CSS — **la CSS se mesure ici, jamais au `grep`**. |
| `mesure_commune.py <base> <mesure>` | état du `CHANGELOG` (en-têtes de version à `##` ou `###`), fiche Francfort, écart de fichiers entre deux racines. En `python3.12 -B`. |
| `89f20c83-…-1700463ff155.json` | la fixture « Bataille de Francfort » (copie de référence ; l'archive porte la sienne dans `tests/fixtures/`). |
| `pg_up.sh` | relance le cluster PostgreSQL 16 s'il s'est arrêté. Les scripts ci-dessous l'appellent eux-mêmes. |
| `prepare_base.sh <appli>` | **base d'essai neuve** : base recréée, migrations de `0001` à la tête depuis `<appli>`, `semis.py`, `semis_e.py`. Rejouable, déterministe. |
| `semis.py <membres.json>` | sème profils, escadrilles, événements, exceptions, réponses ; écrit les membres du faux Discord. Scénario daté du 02/10/2026. |
| `semis_e.py` | complète le semis : la composition de production du 2/10 (CHARLIE-33 7, BRAVO-22 5, ALPHA-11 5, chefs et adjoints posés) et cinq escadrilles d'essai — `T-14`, `T-SANS`, `T-UN`, `T-SEUL`, `T-MEMB` — pour les cas limites d'un organigramme. |
| `servir.sh <appli> <commande…>` | lance uvicorn depuis `<appli>` (env de test, **sans jeton bot** : l'appel ne tourne pas et n'écrit rien), joue la commande, arrête uvicorn. |
| `rendu_de.py <sortie> [paliers]` | **l'instrument de rendu** : les écrans D et E par le vrai code, aux trois largeurs du porteur, bloc par bloc ; la géométrie de chaque organigramme de E ; F ouvert au clic et à la touche Entrée. Écrit les PNG et `mesures.json`, imprime un tableau. |
| `compare_px.py <A> <B> [inclus] [exclus]` | compare au pixel deux dossiers de rendus, fichier par fichier ; code 1 au moindre écart. |
| `faux_discord.py <port> <mode> <membres.json> <journal>` | faux Discord : liste paginée, lecture par identifiant, rôles. Modes : `ok · 403 · vide · 500 · 429 · parti · incomplet · incomplet500 · plafond2`, relus à chaque requête. |
| `bin/docker` | faux `docker compose exec -T -e K=V app python -B -` : joue le Python reçu dans la copie d'essai, l'API Discord pointée sur le faux serveur ; refuse toute autre forme d'appel. |
| `jouer.sh <sh\|bash> <mode> [script]` | joue un script de production tel quel contre le faux Discord, en `sh` ou en `bash`. |
| `maquette.py <sortie> <mode>` | l'écran Membres du Centre, appel au bouton, aux trois largeurs (patron du lot `v1.0016`). |
| `sonde_effectif_relances.sh` | la sonde jouée en production le 2/10 (lecture seule) : entrants de l'appel, retards de planning (R196). |

### Les pièces neuves du v4

| fichier | rôle |
|---|---|
| `pg_faux.sh` | (re)démarre PostgreSQL 16 **sous l'horloge du scénario** : le 02/10/2026, 10:00 UTC (12:00 à Paris), puis l'heure avance. Exige libfaketime. |
| `prepare_cc.sh <appli>` | comme `prepare_base.sh`, **sous l'horloge du scénario**, avec `semis_r.py` après les deux autres. |
| `servir_cc.sh <appli> <commande…>` | PostgreSQL sous horloge ; faux Discord (port 8999, mode `ok`, MP reçus dans `/tmp/faux_discord.log.mp.jsonl`) ; uvicorn **avec jeton bot** et heure figée au 02/10/2026 10:00 UTC ; joue la commande ; arrête tout. `LANCEUR=<script>` remplace `lancer_cc.py`. |
| `lancer_cc.py` | lanceur d'uvicorn : l'API Discord du bot pointe sur le faux serveur, l'appel de démarrage est repoussé d'une heure (seuls les appels du scénario tournent). |
| `semis_r.py <membres.json> <fichier_mode>` | le scénario des relances : réponses, rôle « Officier » (MistyKestrel42, Ghost, Fog, Ancien), faux Discord fidèle à la base (42 membres), Fog refuse les MP (`<mode>.refus`). |
| `retards_ref.py [AAAA-MM-JJ]` | calcul de référence des retards de planning, lecture seule. Sur une base de `prepare_cc.sh`, sous l'heure du scénario : 5 retards (CHARLIE-33 : Jamais, Kerberos, thorn · ALPHA-11 : Fog · T-14 : Odin). |
| `rendu_cc.py <sortie>` | **l'instrument de rendu du Centre** : état 0, puis le scénario des relances si `GET /api/command/rights` porte la clé `relances`. |
| `reception.sh <phase> <livraison.zip> <maquette.zip> <attendu/>` | la réception à froid du CdP, en six phases (une commande chacune). |
| `faux_discord.py` (étendu) | reçoit les MP (voir plus bas) et sert les 12 rôles du scénario. Aucune réponse du v3 ne change. |

**Le faux Discord v4.** `POST /api/v10/users/@me/channels` `{recipient_id}` → 200 `{id: "9"+recipient_id, type: 1, recipients}` ·
`POST /api/v10/channels/9<id>/messages` → 200, ou 403 `{code: 50007}` si l'identifiant est dans `<fichier_mode>.refus` (relu à chaque requête) ·
chaque MP s'ajoute à `<journal>.mp.jsonl` : `{n, destinataire, statut, corps}` · toute autre écriture : 404 ·
`GET /api/v10/guilds/<guilde>/roles` → `CHARLIE-33 · BRAVO-22 · ALPHA-11 · T-14 · T-SANS · T-UN · T-SEUL · T-MEMB · Pilote · Probatoire · Visiteur · Officier`
(champs `id`, `name`), pour que les pastilles de l'écran Droits portent un nom. Le journal reçoit aussi les POST, au format des GET.

### Les pièces neuves du v5

| fichier | rôle |
|---|---|
| `semis_debrief.py` | le semis du Débrief, lancé **après** `semis.py` et `semis_e.py`, depuis la copie d'essai, l'environnement de test chargé. Rejouable (il retire d'abord ses propres lignes) et déterministe. Imprime **une ligne de synthèse**. |
| `prepare_debrief.sh <appli>` | `prepare_base.sh <appli>` (inchangé), puis `semis_debrief.py`. La base d'essai neuve **avec** le Débrief. |
| `rendu_a.py <sortie> [paliers] [clair\|sombre]` | **l'instrument de rendu de l'écran A**, le dossier du pilote (voir plus bas). |

### Les pièces neuves du v6

| fichier | rôle |
|---|---|
| `deposer_journal.py [journal]` | dépose un vrai `debrief.log` par `POST /api/debrief/upload`, **sans remplacer `engine.ingest_file`**, puis vérifie que la session existe et porte des vols et une durée (voir « Déposer un vrai journal »). |
| `debrief_francfort_reduit.log` | le journal à déposer : 170 Ko, tiré du journal réel de Golem sur la Bataille de Francfort (session `89f20c83`), réduit. |

## Ce qui a changé au v6

*Lot « Les dettes hors plume » — 13 fichiers modifiés (`bin/docker`, `prepare_base.sh`, `prepare_cc.sh`, `prepare_debrief.sh`, `reception.sh`, `rendu_a.py`,
`rendu_cc.py`, `rendu_de.py`, `rituel_reprise.sh`, `semis_debrief.py`, `semis_e.py`, `servir.sh`, `servir_cc.sh`), 2 ajoutés (`deposer_journal.py`,
`debrief_francfort_reduit.log`), plus ce `README`. Les 15 autres fichiers sont identiques à l'octet au v5 — `cssrules.py`, `mesure_commune.py` et
`compare_px.py` compris (noms pseudonymisés au v1.0114). Le zip en compte 31.*

- **B1 · Python 3.12, toujours.** `PY="${PY:-python3.12}"` dans `rituel_reprise.sh`, `reception.sh`, `prepare_base.sh`, `prepare_cc.sh`, `prepare_debrief.sh`,
  `servir.sh`, `servir_cc.sh` et le faux `bin/docker` : plus aucun appel à `python3`. Le banc marche sans le shim `PATH` que la méthode imposait. Le
  `python -B -` de `sonde_effectif_relances.sh` est celui de la production, dans le conteneur : le faux `docker` le joue avec `PY`.
- **B2 · Le rituel lit la liste des modules de l'archive.** La ligne `ENGINE_REVISION` prend la liste `_MODULES` de `app/debrief/revision.py` de l'archive
  mesurée (lue par `ast.literal_eval`, sans importer le module : la formule reste calculée à part de celle de l'application). Sur une archive saine, les deux
  lignes du moteur sont égales. Une archive sans `_MODULES` écrit « _MODULES introuvable » à la place de l'empreinte. Seule cette ligne change dans la
  sortie du rituel.
- **B3 · libfaketime, seulement là où il sert.** Voir « La réception à froid » : `centre-base` et `centre` l'exigent, `de-base` et `de` non.
- **B4 · Le pied de version masqué au pixel.** Le `MASQUE` de `rendu_de.py` et celui de `rendu_cc.py` rendent `#app-version-footer` invisible
  (`visibility:hidden`, la mise en page ne bouge pas), comme la barre ; `rendu_a.py` importe celui de `rendu_de.py`. Une version qui change ne fait plus
  bouger un pixel.
- **B5 · Hunter, adjoint non administrateur, porteur de l'accès au Centre.** Hunter est adjoint du ALPHA-11 (`semis_e.py`, `TETES_BASE`) et n'est pas dans
  `ADMIN_IDS`. Son rang d'adjoint lui donne `command.access` dans `GET /api/me` et `GET /api/command/archives` répond 200 ; `PUT /api/command/archives/automatique`
  lui répond **403 « Réservé à l'administrateur. »**. C'est le semis qui pose cet état : `etat_banc_pol.sql` n'est plus nécessaire. `semis_e.py` porte désormais un
  commentaire qui le dit.
- **B6 · Des sessions semées avec une durée.** `semis_debrief.py` pose `duration_s = 5298` sur ses deux sessions (la durée de Francfort en production depuis le
  `v1.0041`). La fixture ne change pas.
- **B7 · Un vrai `debrief.log` à déposer.** `deposer_journal.py` et `debrief_francfort_reduit.log` : voir ci-dessous.
- **B8 · Ce `README`.**

## Ce qui a changé au v8

*Lot « Le banc et les droits » (`RR-V1.0.0+1`) — 4 fichiers modifiés (`semis.py`, `sonde_effectif_relances.sh`, `mesure_commune.py`, `reception.sh`), plus ce `README`.*

- **`semis.py` · l'accès non administrateur** (`rr-banc-acces-non-admin`). Il pose la capacité `app.access` au rôle Pilote (`111111111111111111`) dans `role_capabilities`,
  sans doublon (`ON CONFLICT DO NOTHING`). Depuis le `v1.0111`, la base fait autorité seule sur l'accès à l'application : sans cette ligne, seul l'administrateur entrait au banc
  (`role_capabilities` vide après `prepare_base.sh`). **Cela remplace la phrase du semis du Débrief plus haut** (« le semis n'écrit aucune ligne `app.access` ») : après `prepare_debrief.sh`,
  le rôle Pilote porte `app.access` **et** `debrief.access` (`semis_debrief.py` garde le sien tel quel : au banc, un membre et un débriefeur se confondent). Les instruments qui posaient
  `app.access` eux-mêmes n'en ont plus besoin. L'import inutile de `text`, que `pyflakes` signalait depuis le v3, est retiré : le fichier est modifié, la règle du banc s'applique.
- **`sonde_effectif_relances.sh` · `_app_access_role_ids`** (`rr-sonde-adresse-g`, résolu par le point précédent). Depuis le `v1.0111`, `_app_access_role_ids` rend **un ensemble** :
  `porte = await _app_access_role_ids(db)`. Aucune autre ligne ne lisait `_depuis_env`.
- **`mesure_commune.py` · le `CHANGELOG`** (porte P11, `rr-banc-p11-unreleased`). La ligne `changelog :` de chaque racine devient
  `changelog : <n> versions publiées (dernière <TAG>|—) · doublons <liste|aucun> · <u> lignes sous « ## Unreleased »` (les versions publiées sont les en-têtes `## RR-V<x.y.z>` suivis d'un
  blanc ou de la fin de ligne, la dernière est la première du fichier ; `u` compte les lignes non vides de la section `## Unreleased`, `—` sans elle). Juste après `== écart base → mesure`,
  une ligne neuve : `changelog : +<a> lignes ajoutées, <h> hors de « ## Unreleased » · −<r> lignes retirées · <e> en-têtes neufs`, tirée du diff ligne à ligne des deux `CHANGELOG.md`
  (`difflib.SequenceMatcher`, `autojunk=False`). Les formes sont fixes, même au singulier. Le reste de la sortie ne change pas.
- **`reception.sh` · la phase `droits`**, après `statique`, avant `verdict`. Elle se joue si `droits.txt` est dans les attendus (le compte du test, `2 passed`), sinon elle se saute : PostgreSQL 16 à l'heure
  réelle (`pg_up.sh`), une base **neuve** `readyroom_droits` (supprimée puis recréée, supprimée de nouveau à la fin), la copie de la livraison (`$D/essai`, refaite depuis `$D/mesure` : `statique` a supprimé la
  sienne), les variables de `.env.example`, `RR_TEST_PG_URL=postgresql+asyncpg://readyroom:readyroom@127.0.0.1:5432/readyroom_droits`, puis
  `pytest -q tests/test_droits_routes.py`. La dernière ligne doit commencer par le contenu de `droits.txt` suivi d'une espace ou d'une virgule, sinon l'écart « droits » (la sortie est gardée pour `verdict`).
  `verdict` exige la phase `droits` quand `droits.txt` est présent, comme il exige `centre` et `de`. Mesurée : une trentaine de secondes.

## Déposer un vrai journal — la recette

```sh
sh /home/claude/rr/harness/prepare_base.sh <appli>
sh /home/claude/rr/harness/servir.sh <appli> python3.12 -B /home/claude/rr/harness/deposer_journal.py [journal]
```

- **Une base sans Débrief semé** (`prepare_base.sh`, pas `prepare_debrief.sh`) : le dépôt doit CRÉER sa session, et le script s'arrête sinon. Il passe par la
  vraie route, avec le vrai `engine.ingest_file` — rien n'est remplacé. Les fichiers bruts vont dans `/data/debrief_raw/` (`DEBRIEF_STORAGE_DIR`), hors du banc.
- **Le journal** : le journal de Golem (`debrief.log (1).txt`, 20 Mo, session `89f20c83`), déposé par Viper (le profil du banc qui porte Golem). **Réduit** à
  170 Ko : l'en-tête, le cimetière entier (136 entrées), les champs racine `mission_file_mark`, `mission_time` et `result`, et 349 évènements sur 2 431 — ceux
  qui touchent une des 13 vies du déposant (initiateur ou cible d'un objet des évènements « under control »), plus « mission start » et « mission end ». Les
  entrepôts, les routes et l'état du monde (19 Mo) sont retirés. Le texte gardé est celui du journal, à l'octet (noms pseudonymisés au v1.0114). L'en-tête garde le chemin Windows d'origine (noms pseudonymisés au v1.0114).
- **Ce que la session obtient** : 11 vols servis, tous au déposant (13 lignes en base, une par vie ; deux sont écartées comme vides), durée 4268 s (de la première
  arrivée de Golem, à 1 029,5 s, à la sortie, à 5 297,5 s), 6 destructions, titre « Foothold_GCW_V5.2.5_Coldwar-Modern_radios_20260730-2219 ». Le journal complet
  (20 Mo), déposé de la même façon, donne pour ces 13 vies des lignes identiques — `stats` comprises —, la même durée et le même cimetière ; il voit en plus
  5 autres vols et 26 destructions au total, parce que les évènements qui ne touchent pas le déposant sont retirés ici.
- **Un seul journal, donc pas 5298 s** : la durée de 5298 s de la production vient des trois journaux de la session (le premier commence à 0,001 s).
- Sortie : une ligne `dépôt : journal … Ko · session … créée · … vols … · durée … s …`. Code 1 : réponse en erreur, session non créée, aucun vol ou aucune durée.

## Semer le Débrief — la recette

```sh
sh /home/claude/rr/harness/prepare_debrief.sh <appli>
```

Sortie attendue, sur la `v1.0022` (8 s) : `migration 0032`, puis
`semis du débrief : sessions 89f20c83 · 3e03afb4 · 2 sessions · 40 vols · 318 évènements · 2 campagnes · droit debrief.access posé au rôle Pilote (111111111111111111)`.
*Sur un cluster neuf, le tout premier passage imprime en plus le message PostgreSQL « database "readyroom" does not exist, skipping » ; rien d'autre ne change d'un passage à l'autre.*

**La source** est la fixture du banc, `89f20c83-…-1700463ff155.json`, identique à l'octet à celle de l'archive (`tests/fixtures/`) : le semis
s'arrête si elles diffèrent (noms pseudonymisés au v1.0114).

**Deux copies, deux campagnes**

| | copie 1 | copie 2 |
|---|---|---|
| identifiants (session, vols, évènements) | ceux de la fixture | dérivés de ceux de la copie 1 par `uuid5` |
| `mission_date` | 2026-08-17 | 2026-09-20 |
| `reference_time` | celui de la fixture | décalé de 34 jours |
| `title` | celui de la fixture | `Fulda_Gap_Coldwar_V1.0_20260920-2124` |
| `display_name` | `Bataille de Francfort` | vide : le titre s'embellit en « Fulda Gap Coldwar V1.0 » |
| campagne | « Foothold Germany » (identifiant de la fixture) | « Fulda Gap » |

Le reste de chaque session reprend la fixture (`sim`, `acmi_present`). **v6 : `duration_s` vaut 5298 s sur les deux sessions** — la durée de la Bataille de
Francfort en production depuis le `v1.0041` ; la fixture, elle, n'en porte pas et ne change pas. Les deux campagnes sont en `sim` `dcs`, au statut par
défaut ; la première est écrite avant la seconde, avec des `created_at` explicites et distincts (le rang d'une campagne, donc la teinte de
sa barrette, suit `created_at`).

**Les pilotes.** Chaque copie reprend les 20 vols, `stats` à l'identique ; les pilotes identifiés passent sur des profils du banc, et
`pilot_callsign` devient le nom du profil ; les trois vols anonymes le restent.

| pilote de la fixture | profil du banc |
|---|---|
| `800000000000000002` (MistyKestrel42) | `100000000000000001` MistyKestrel42 |
| `8000000000000000001` (Golem) | `200000000000000003` Viper |
| `800000000000000006` (Kraken) | `200000000000000004` Ghost |
| `800000000000000003` (Vortex) | `200000000000000010` Rover |
| `800000000000000004` (Noctis) | `200000000000000001` Dragoon-1 |
| `800000000000000005` (GRIFFON) | `200000000000000006` Fog |

**Hunter (`200000000000000005`) n'a aucun vol : c'est le dossier vide.**

**Les évènements.** La fixture n'en porte aucun ; un vol n'est « réel » que s'il porte un évènement non mécanique qui le nomme en initiateur ou
en cible. Chaque vol reçoit donc des évènements tirés de ses `stats`, jamais d'un des six types mécaniques : chaque destruction → `kill`
(initiateur) ; chaque menace visée → `shot`, touchée ou abattue → `hit` (cible) ; la fin du vol → `crash`, `eject`, `pilot dead`, `land`
(initiateur). Les 20 vols de chaque session sont servis (`GET /api/debrief/sessions/<id>`).

**Les deux pièges du Débrief, réglés par le semis.** Chaque session porte `stats_engine_rev` = l'`ENGINE_REVISION` de l'appli servie (sans cela, le
recalcul au démarrage d'uvicorn efface ses vols) ; le rôle Pilote (`111111111111111111`) reçoit `debrief.access` dans `role_capabilities` (sans cela,
un non-admin reçoit un 403 sur tout le Débrief). **Le semis n'écrit aucune ligne `app.access`** : la porte de l'application se replie sur
`ALLOWED_ROLE_IDS` du `test.env`, où figure Pilote, tant que la base n'en porte aucune — une seule ligne ferait de la base l'autorité.

## Rendre A — la recette (le dossier du pilote)

```sh
sh /home/claude/rr/harness/prepare_debrief.sh <appli>
sh /home/claude/rr/harness/servir.sh <appli> python3.12 -B /home/claude/rr/harness/rendu_a.py <sortie> [large,intermediaire,compact] [clair|sombre]
```

- **Les pilotes** : MistyKestrel42 (admin), Viper, Ghost et Hunter, chacun avec sa session forgée. A ne montre que le dossier du compte connecté.
- **Les appareils** sont ceux de `rendu_de.py` (paysage 1 150, portrait 720, téléphone 393) ; la barre de l'application est masquée de la même façon.
- **Le contrat de l'écran A**, que le lot suivant tiendra : l'onglet « Pilotes » est `button[data-nav="pilotes"]`, dans la nav du Débrief ; A vit dans
  `#view-pilotes`, sur une `.sheet` ; ses blocs sont les enfants directs de `#pilotes-mount` ; le lien vers F porte `data-ouvre-membre="<id du pilote>"`.
- **A présent** : chaque bloc en `A_<pilote>_<i>-<bloc>_<palier>.png`, la feuille entière en `A_<pilote>_page_<palier>.png` (pour le regard, jamais comparée) ;
  le lien vers F se clique, et doit ouvrir F **du même pilote** (colonne `F:lien`).
- **A absent** (l'onglet n'a pas `data-nav="pilotes"`) : l'instrument écrit « Écran A : absent de cette version — F rendu à la place » et rend F de chaque
  pilote, ouvert depuis sa case dans l'organigramme de D, en `F_<pilote>_<i>-<bloc>_<palier>.png` et `F_<pilote>_page_<palier>.png`. `F:lien` y vaut `—`, et une
  ligne « F ouvert depuis D » dit si chaque case a ouvert F.
- **Le thème** : `clair` par défaut ; `sombre` passe `color_scheme` au navigateur (l'application suit le thème du système) et suffixe les fichiers en `_sombre`.
- **Le tableau**, imprimé par palier et écrit dans `mesures.json`, se lit sur `GET /api/debrief/dossier` avec la session du pilote ; il est suivi des erreurs JS.
  Colonnes : `pilote · vols · fiables · air · sol · perdus · éjections · ratio · armes · menaces · appareils · carnet · campagnes · blocs · F:lien`
  (`blocs` : ceux de A ; sans A, ceux de F). Code de sortie 1 : une erreur JS, un lien qui n'ouvre pas le bon F, un F qui ne s'ouvre pas.
- **Valeurs mesurées sur la `v1.0022`**, les mêmes aux trois paliers :

| pilote | vols | fiables | air | sol | perdus | éjections | ratio | armes | menaces | appareils | carnet | campagnes | blocs (F) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MistyKestrel42 | 2 | 2 | 0 | 8 | 2 | 0 | 4.0 | 1 | 2 | 1 | 2 | 2 | 3 |
| Viper | 22 | 22 | 10 | 2 | 22 | 12 | 0.5 | 4 | 4 | 3 | 22 | 2 | 3 |
| Ghost | 2 | 0 | 8 | 0 | 0 | 0 | `null` | 0 | 1 | 1 | 2 | 2 | 3 |
| Hunter | 0 | 0 | 0 | 0 | 0 | 0 | `null` | 0 | 0 | 0 | 0 | 0 | 3 |

- **Durée** : un passage de trois paliers tient sous 270 s (mesuré : 43 s en clair, 47 s en sombre, sur la `v1.0022`, A absent). **Si une version plus riche
  dépasse la limite, on joue un palier par commande** (`… rendu_a.py <sortie> large`, puis `intermediaire`, puis `compact`) : le `mesures.json` d'une commande
  ne porte que son palier, et chaque commande réécrit le sien — copier `mesures.json` avant la suivante.
- **Éprouver le chemin A sans l'écran** : sur une copie jetable de l'appli dans `/tmp` (jamais dans le banc ni dans une archive), poser `data-nav="pilotes"` sur
  l'onglet, une `.sheet` avec `#pilotes-mount` et trois blocs dans `#view-pilotes`, dont un lien `data-ouvre-membre` vers le pilote connecté (id lu sur `/api/me`).
  Attendu : 3 blocs par pilote et `F:lien` vrai, aux trois paliers.

## Mesurer une racine

```sh
cd /home/claude/rr/harness && bash rituel_reprise.sh <racine absolue>
python3.12 -B /home/claude/rr/harness/mesure_commune.py <base> <mesure>
```

*Le rituel écrit le chemin reçu dans son en-tête CSS : un bloc « base » de cadrage se compare avec le même chemin.*

## Rendre D et E — la recette commune du dev et du CdP

```sh
cp /home/claude/rr/harness/test.env /home/claude/rr/test.env            # une fois
sh /home/claude/rr/harness/prepare_base.sh <appli>
sh /home/claude/rr/harness/servir.sh <appli> python3.12 -B /home/claude/rr/harness/rendu_de.py <sortie>
python3.12 -B /home/claude/rr/harness/compare_px.py <sortie_A> <sortie_B> [inclus] [exclus]
```

- **Toujours `prepare_base.sh` avant un rendu à comparer** : deux rendus d'une même appli sur une base neuve
  sont identiques au pixel (156 images sur 156, éprouvé le 2/10).
- Fichiers produits : `D_<i>-<bloc>_<palier>.png`, `E_<escadrille>_<i>-<bloc>_<palier>.png` (chaque enfant du
  montage de l'écran, `<i>` son rang) et `E_<escadrille>_page_<palier>.png` (la feuille entière, **pour le
  regard, jamais comparée**).
- Paliers : `large` 1 150 × 1 100 en paysage, `intermediaire` 720 × 2 400 et `compact` 393 × 2 400 en portrait,
  densités 2,5 · 2,5 · 2,75. *L'orientation compte : des règles CSS en dépendent.* La barre de l'application est
  masquée pendant les captures (`visibility:hidden` : la mise en page ne bouge pas).
- Colonnes du tableau : `cases` (cases pilote de la section « Organigramme ») · `chef` · `colonnes` (cases par
  colonne sous le chef, de gauche à droite) · `ordre` (lecture colonne par colonne = ordre de la charge, chef ôté) ·
  `larg.chef` et `larg.sous` (px CSS) · `retrait` (bord gauche des cases sous le chef moins celui du chef) ·
  `dessus` (le chef au-dessus de toutes) · `F:clic`, `F:entrée` · `cadre_h`. En tête de palier, **`retrait des
  membres de D`** : la référence du retrait.

## Rendre le Centre — la recette commune du dev et du CdP

```sh
apt-get install -y faketime                                              # une fois, après PostgreSQL 16
cp /home/claude/rr/harness/test.env /home/claude/rr/test.env             # une fois
sh /home/claude/rr/harness/prepare_cc.sh <appli>
sh /home/claude/rr/harness/servir_cc.sh <appli> python3.12 -B /home/claude/rr/harness/rendu_cc.py <sortie>
python3.12 -B -W ignore /home/claude/rr/harness/compare_px.py <sortie_A> <sortie_B> [inclus] [exclus]
```

- **Toujours `prepare_cc.sh` avant un rendu à comparer** ; **un passage de `rendu_cc.py` par commande** : l'état 0 dure ~65 s,
  le scénario des relances ~3 min 15 s ; le bac à sable coupe une commande à 300 s.
- **Horloge** : le 02/10/2026, 12:00 à Paris, côté PostgreSQL (qui avance), côté uvicorn et semis (figée) et côté navigateur
  (`clock.set_fixed_time`) : le rendu ne dépend pas du jour où l'on rend.
- Fichiers produits : `R-<bloc>_<palier>.png` (écran Droits) et `M-<bloc>_<palier>.png` (écran Membres), nommés par leur identifiant —
  **un bloc qui descend garde son nom** — ; `R_page_<palier>.png` et `M_page_<palier>.png` (la page entière, **pour le regard, jamais comparée**) ;
  `S<étape>-…` (le scénario) ; `MP_<n>-e<étape>-<destinataire>-<statut>.png` (chaque MP rendu au téléphone) ; `mesures.json`.
  La `v1.0017` donne **42 images** et `mesures.json`.
- **Le scénario** (seulement si `GET /api/command/rights` porte la clé `relances`) : étape 0 aucun rôle destinataire ; 1 le rôle Officier choisi ;
  2 sans changement ; 3 Rover perd sa seule réponse ; 4 Kerberos répond pour le 29/09 — un appel au bouton `#cc-appel-btn` à chaque étape.
  Sortie complète avec le contrat : 66 images. Une version sans relances le dit (« Relances : absentes de cette version »).
- **Le bandeau `cc-partial`** de l'écran Droits reste : il liste les escadrilles sans chef (`T-SANS`, `T-MEMB` de `semis_e.py`), il ne dépend pas des rôles.

## La réception à froid — la recette du CdP

Préalables : la base déballée à froid dans `/home/claude/dev/base`, ce banc dans `/home/claude/rr/harness`. **PostgreSQL 16 n'est exigé que par les
phases qui rendent** (`centre-base`, `centre`, `de-base`, `de`) ; **libfaketime (v6) ne l'est que par `centre-base` et `centre`** — les seules qui jouent
`pg_faux.sh` et `LD_PRELOAD` (par `prepare_cc.sh` et `servir_cc.sh`). `de-base` et `de` passent par `prepare_base.sh`, `servir.sh` et `pg_up.sh`, qui n'en
appellent jamais ; `statique` et `verdict` s'en passent, et une phase sautée n'exige rien.
Une phase par commande ; chacune tient sous 270 s (mesurées sur la `v1.0017` : `statique` 8 s, `centre-base` 66 s, `centre` 57 s, `de-base` 131 s, `de` 128 s, `verdict` quelques secondes).

```sh
R="sh /home/claude/rr/harness/reception.sh"; A="<livraison.zip> <maquette_validee.zip> <attendu/>"
$R statique $A      # déballage, rituel, mesure commune, pyflakes, node, pytest sur copie, .pyc
$R centre-base $A   # rend le Centre de la base si rendus_cc/base manque (sinon rien)
$R centre $A        # rend le Centre de la livraison
$R de-base $A       # rend D et E de la base si rendus/base manque (PostgreSQL relancé à l'heure réelle)
$R de $A            # rend D et E de la livraison
$R droits $A        # v8 : joue la carte des droits sur une base PostgreSQL neuve, si droits.txt est dans les attendus
$R verdict $A       # réimprime les écarts, compare, rend le verdict ; code 0 sans écart, 1 avec
```

**La réception allégée (v5)** — pour un lot sans maquette ni rendu : `-` prend la place de la maquette, et `verdict` ne la cherche pas.

```sh
R="sh /home/claude/rr/harness/reception.sh"; A="<livraison.zip> - <attendu/>"
$R statique $A; $R verdict $A      # sans PostgreSQL 16 ni libfaketime
```

Avec un zip de maquette et sans `empreinte.txt`, `reception.sh` se comporte comme au v4.

- Chaque phase n'affiche que ses écarts, puis `PHASE <nom> · aucun écart · <n> s` (ou `<k> écart(s)`, ou `sautée`). `verdict` réimprime tous les écarts, puis
  `RÉCEPTION · <livraison> · aucun écart` (ou `ÉCARTS ci-dessus`). **Code 2** : la phase ne peut pas se jouer (banc, base, PostgreSQL 16, libfaketime,
  entrée absente, phase jouée avant celle dont elle dépend).
- `<attendu/>` : `rituel.txt`, `commune.txt`, `pytest.txt` ; facultatif `empreinte.txt` — l'empreinte du code de `mesure` (`app`, `alembic`, `tests`), la commande de
  l'étape 6 du prompt du dev : `statique` la compare et compte un écart si elle diffère (la porte P13) ; facultatifs `rendu_cc.txt` (lignes « === Scénario » à « === Erreurs JS »), `immobiles_cc.txt` (un motif par ligne)
  — leur présence joue `centre-base` et `centre` — et `de_immobile` (fichier vide) — il joue `de-base` et `de` ; v8 : `droits.txt` (le compte attendu du test des droits, ex. `2 passed`) — il joue `droits`. L'en-tête de `reception.sh` les décrit.
- **`rendus_cc/base` et `rendus/base` se gardent** : à supprimer quand la base change. Les chemins reçus peuvent être relatifs.

## Pièges mesurés

- **Le fuseau du processus compte pour libfaketime** (mesuré au v6) : `FAKETIME='2026-10-02 10:00:00'` s'entend dans le fuseau local. Avec `TZ=Europe/Paris` dans l'environnement, le serveur est figé à 08:00 UTC, le cookie du Centre (signé à 09:00 UTC) a un âge négatif, `GET /` rend la page de connexion et `rendu_cc.py` attend en vain `#station-command-open`. Jouer les phases du Centre avec `TZ=UTC` (`unset TZ` ou `export TZ=UTC`).
- **Installer libfaketime** : `apt-get install -y faketime` (le fichier attendu est `/usr/lib/x86_64-linux-gnu/faketime/libfaketimeMT.so.1`). Sans lui, `pg_faux.sh` s'arrête.
  `FAKETIME_DONT_FAKE_MONOTONIC=1` est indispensable : sans lui, les attentes d'asyncio se figent.
- **Le cookie est signé une heure avant l'heure du serveur** : le serveur est figé au 02/10/2026 10:00 UTC et `itsdangerous` refuse un âge négatif ; `rendu_cc.py` signe à 09:00 UTC.
- **Un bloc placé sous un bloc inséré ne se compare pas au pixel** (R199, étendu au Centre) : le papier et le grain sont posés sur la feuille. Les blocs au-dessus d'une insertion restent
  identiques (24 images sur 24 en contre-épreuve) ; ceux qui descendent (`blk-droits`, `blk-ref`, `cc-wrap`) diffèrent, d'au moins la taille de la feuille.
- **Le simulacre du contrat ne va jamais dans le banc** : c'est un outil d'épreuve du CdP (`contre_epreuve/`), pas de valeur de modèle ; `servir_cc.sh` le joue par `LANCEUR=`.
- **PostgreSQL reste sous l'horloge du scénario** après un rendu du Centre : `pg_up.sh` le trouve « en ligne » et ne le relance pas. Avant tout rendu de D et E, le relancer à l'heure
  réelle (`reception.sh`, phases `de-base` et `de`, le fait ; sinon : arrêter le cluster puis `pg_up.sh`).
- **`pyflakes` signale une ligne dans le banc, héritée du v3** : `semis.py:8:1: 'sqlalchemy.text' imported but unused`. `semis.py` est volontairement inchangé (reproductibilité de la recette de D et E) :
  la règle du banc est « rien sur les `.py` neufs ou modifiés ».
- **Un passage du scénario dure plus de 3 minutes, la limite d'une commande est de 300 s** : un passage par commande ; deux rendus dans une seule dépassent la limite.
- **`compare_px.py` du v3 émet un avertissement de dépréciation de Pillow** : lancer en `python3.12 -B -W ignore` quand la sortie sert à autre chose qu'au regard.
- **Le semis du Débrief veut `stats_engine_rev` à jour** : une session semée sans l'`ENGINE_REVISION` de l'appli servie perd ses vols au premier démarrage d'uvicorn (le recalcul les efface).
  `semis_debrief.py` la lit dans `app.debrief.revision` de l'appli d'où il est lancé : toujours `prepare_debrief.sh <appli>`, jamais le semis seul sur une autre version.
- **`pyflakes` ne signale rien** sur `semis_debrief.py`, `rendu_a.py`, ni (v6) sur `deposer_journal.py`, `semis_e.py`, `rendu_de.py`, `rendu_cc.py` ; `sh -n` passe sur tous les `.sh`.
- **Aucun fichier d'exécution dans le zip** : `membres.json`, `mode`, `mode.refus` s'écrivent dans le banc déployé ; on assemble le zip depuis l'arbre propre, jamais depuis `/home/claude/rr/harness`.

- **Une comparaison au pixel ne vaut que pour un bloc dont la position ne change pas** (R199) : le papier (tuile de
  640 px) et le grain (`.sheet::after`, 210 px) sont posés sur la feuille, les cadres n'ont qu'un voile — sous une section
  qui change de hauteur, le fond des blocs change. Leur immobilité se prouve par le diff.
- **La maquette validée se livre en zip et se compare par outil** : les images n'entrent dans aucun contexte.

- **Le bac à sable tue les processus entre deux appels d'outil** : PostgreSQL s'arrête, uvicorn aussi. Tout ce
  qui sert le site se joue dans **une seule commande** — `servir.sh` le fait.
- **PostgreSQL 16** : `apt-get update` exige d'écarter `/etc/apt/sources.list.d/nodesource.sources` ; puis
  `apt-get install -y postgresql-16`. `pg_up.sh` démarre le cluster ; `prepare_base.sh` crée le rôle s'il manque.
- **`pg_dump` 16.15 écrit une clé `\restrict` aléatoire** à chaque sortie : pour comparer deux bases, retirer les
  lignes `\restrict` et `\unrestrict` avant l'empreinte.
- **`app.js` vit dans une IIFE** : aucune fonction n'est globale. L'écran se pilote par les vrais boutons
  (`click()` sur le DOM) ; la tuile d'un module se reclique jusqu'à ce que `/api/me` soit chargé.
- **La session** se forge avec `itsdangerous.TimestampSigner(SESSION_SECRET)` sur `b64(json)` — cookie `session` ;
  champs `id`, `name`, `roles`, `lang`, `avatar`, `squadron`, `exp`.
- **Playwright et Chromium** sont dans `/opt/pw-browsers`.
- **L'appel de démarrage part 60 s après le lancement d'uvicorn** quand un jeton bot est fourni ; `servir.sh` n'en
  fournit pas.
- **Le shell est `dash`** : pas de `<( … )`, passer par des fichiers temporaires.

## Connus, non traités

Fermés **par décision du porteur (15 octobre 2026), sans code** ; à rouvrir sur une gêne vue. Ils sont nommés ici, pas traités.

- les résidus de l'appel ;
- le rendu de l'écran C ;
- la découpe à l'échelle 1 ;
- les armes larguées ;
- les types vus ;
- les appareils des escadrilles au semis ;
- les campagnes closes ou multiples au semis.
