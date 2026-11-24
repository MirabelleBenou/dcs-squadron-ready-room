# 5 · Configurer { #configure }

La Ready Room lit sa configuration de démarrage dans un fichier, **`.env`**, à la racine de son dossier. Il ne porte
que ce qu'il faut pour démarrer : l'adresse, l'application Discord, les administrateurs fondateurs, trois secrets et la
base. **Tout le reste se règle ensuite dans la Ready Room**, à l'écran.

## 5.1 · Écrire le `.env` { #write-env }

Le plus simple est le script fourni : il pose les questions, fabrique les secrets et écrit le fichier avec les bons
droits. Il ne touche à rien d'autre.

```sh
cd /opt/readyroom
sh init-env.sh
```

Répondez avec les valeurs relevées aux chapitres 2 et 3 ; à la question *Option A or B*, répondez **A** pour votre nom de domaine avec Caddy, **B** pour tout autre moyen (Tailscale, Cloudflare, votre propre proxy). À la fin, il affiche **une fois** la clé des réglages
(`CONFIG_KEY`) : copiez-la dans votre gestionnaire de mots de passe ([§5.4](#config-key)).

!!! note "À la main"
    Vous pouvez aussi copier le modèle et le remplir avec `nano`, en suivant le [§5.2](#required-variables) :
    ```sh
    cp .env.example .env
    chmod 600 .env
    nano .env
    ```

!!! failure "Si ça ne marche pas"
    `init-env.sh` refuse de remplacer un `.env` qui existe : renommez l'ancien (`mv .env .env.ancien`) si vous voulez
    recommencer.

## 5.2 · Les variables obligatoires { #required-variables }

| variable | ce qu'elle contient | d'où elle vient |
|---|---|---|
| `BASE_URL` | l'adresse HTTPS de la Ready Room, sans `/` final | [§2.5](02-prepare-the-server.md#address) |
| `DISCORD_CLIENT_ID` | l'*Application ID* | [§3.2](03-discord-application.md#create-application) |
| `DISCORD_CLIENT_SECRET` | le *Client Secret* | [§3.2](03-discord-application.md#create-application) |
| `DISCORD_GUILD_ID` | l'identifiant de votre serveur Discord | [§3.1](03-discord-application.md#developer-mode) |
| `ADMIN_IDS` | les administrateurs fondateurs | [§5.3](#founders) |
| `SESSION_SECRET` | le secret qui signe les sessions des membres | à fabriquer, ci-dessous |
| `CONFIG_KEY` | la clé qui chiffre les secrets gardés en base | à fabriquer, ci-dessous |
| `POSTGRES_USER`, `POSTGRES_DB` | l'utilisateur et le nom de la base | `readyroom` convient |
| `POSTGRES_PASSWORD` | le mot de passe de la base | à fabriquer, ci-dessous |

Les secrets se fabriquent avec `openssl`, une commande par secret ; collez chaque résultat dans `.env` :

```sh
openssl rand -base64 48 | tr -d '\n' ; echo      # SESSION_SECRET
openssl rand -base64 32 | tr '+/' '-_'           # CONFIG_KEY
openssl rand -hex 24                             # POSTGRES_PASSWORD
```

!!! warning "Attention"
    `SESSION_SECRET` doit faire au moins 32 caractères et ne jamais garder la valeur d'exemple : sinon, la Ready Room
    refuse de démarrer. Les identifiants Discord s'écrivent en chiffres seuls, sans espaces ni guillemets.

!!! note "La base"
    `POSTGRES_USER`, `POSTGRES_PASSWORD` et `POSTGRES_DB` créent la base au premier démarrage, et l'application s'en
    sert pour la joindre. Les changer **après** le premier démarrage ne change pas la base déjà créée : la Ready Room
    ne pourrait plus s'y connecter.

## 5.3 · Les administrateurs fondateurs { #founders }

`ADMIN_IDS` nomme **les administrateurs fondateurs** : un identifiant Discord au moins, plusieurs séparés par des
virgules, sans espaces :

```text
ADMIN_IDS=<votre identifiant>,<identifiant d'un autre fondateur>
```

Un fondateur entre toujours et ouvre tout, quels que soient ses rôles Discord : c'est le garde-fou qui vous empêche de
vous enfermer dehors. Il doit tout de même être **membre du serveur Discord** de l'escadre. Les autres administrateurs
se nomment ensuite dans la Ready Room (**Centre de Commandement › Configuration › Administrateurs**) ; un fondateur ne
s'y retire pas : il se retire en éditant `ADMIN_IDS`.

## 5.4 · La clé des réglages { #config-key }

`CONFIG_KEY` chiffre les secrets que vous saisirez à l'écran (jeton du bot, webhook, clé Anthropic…).

!!! warning "Attention"
    **Gardez `CONFIG_KEY` à part des sauvegardes**, dans votre gestionnaire de mots de passe : une sauvegarde de la base
    avec sa clé à côté rend ces secrets lisibles à qui la trouve. **Perdue ou changée**, la clé rend ces secrets
    illisibles : ils sont à ressaisir à l'écran **Configuration** ; rien d'autre n'est perdu.

## 5.5 · Facultatif : les dossiers de l'hôte { #host-folders }

Trois dossiers du serveur sont branchés dans l'application. Par défaut, ils sont sous `data/` dans le dossier de la
Ready Room ; pour les mettre ailleurs (un disque de données, par exemple), ajoutez ces lignes à `.env` :

| variable | défaut | ce qu'on y met |
|---|---|---|
| `SUITES_HOST_DIR` | `./data/suites` | `dcs_mission_plan.html` et `dcs_mission_tools.html`, si la Ready Room doit servir Mission Plan et Mission Tools |
| `TILES_HOST_DIR` | `./data/tiles` | facultatif : des tuiles de la carte DCS que vous avez déjà, servies d'abord (lues seulement) |
| `TILES_CACHE_HOST_DIR` | `./data/tiles-cache` | les tuiles venues d'Olympus, gardées par la Ready Room |

Sans ces fonctions, laissez les défauts : rien ne casse si les dossiers sont vides.

## 5.6 · Ce qui ne va pas dans `.env` { #not-in-env }

Tout le reste se règle **dans la Ready Room**, sans redémarrer, par un administrateur :

| réglage | où | quand |
|---|---|---|
| le fuseau de l'escadre | **Configuration** : *Fuseau horaire* | chapitre 7 |
| le nom, le sigle, le tag et l'emblème de l'escadre | **Centre de Commandement › Escadre** | chapitre 8 |
| les escadrilles, qui entre, qui crée les évènements | **Escadrilles**, **Droits** | chapitre 8 |
| la commande `/readyroom`, les boutons de présence | **Configuration** : *Discord — les réponses* | chapitre 7 |
| le digest hebdomadaire | **Configuration** : *Discord — le digest* | chapitre 7 |
| le récit des rapports de mission | **Configuration** : *Le Récit du Rapport de mission* | chapitre 8 |
| un autre serveur de tuiles | **Configuration** : *Les tuiles de la carte* | — |

La liste complète des variables et des réglages est à l'[annexe A](a-environment.md).

## 5.7 · Vérifier { #check-env }

```sh
ls -l .env
grep -n -E 'changeme|change_this|^[A-Z_]+=$' .env
```

!!! success "Vérifier"
    `ls -l` montre `-rw-------` (lisible par vous seul) ; `grep` n'affiche **rien** (plus aucune valeur d'exemple ni
    variable vide). Sinon : `chmod 600 .env`, et complétez chaque ligne affichée.
