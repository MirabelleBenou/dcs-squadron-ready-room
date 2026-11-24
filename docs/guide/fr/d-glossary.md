# D · Glossaire { #glossary }

## D.1 · Les mots du guide { #terms }

| mot | ce qu'il désigne |
|---|---|
| **administrateur fondateur** | un compte Discord nommé dans `ADMIN_IDS` : il entre toujours et ne peut pas s'enfermer dehors |
| **agent** | le hook du serveur DCS et son envoi, qui enregistrent les missions et les envoient à la Ready Room (chapitre 10) |
| **appel** | la lecture des membres du serveur Discord et de leurs rôles, qui tient l'effectif à jour ([§8.4](08-first-settings.md#roll-call)) |
| **archivé** | un membre sorti de l'effectif, dont le profil et l'historique restent |
| **digest** | le message Discord qui annonce le planning des deux semaines à venir, tenu à jour par la Ready Room |
| **écusson** | l'image d'une escadrille ; **emblème** : celle de l'escadre |
| **escadre** | le groupe entier, que la Ready Room sert ; **escadrille** : une de ses unités, rattachée par un rôle Discord |
| **Free Agent** | un membre qui a l'accès sans porter de rôle d'escadrille |
| **fuseau de l'escadre** | le fuseau horaire dans lequel la Ready Room compte les jours et les heures ([§7.5](07-first-start.md#time-zone)) |
| **hook** | un script que DCS charge à son démarrage, depuis `Scripts\Hooks\` |
| **jeton** | une chaîne secrète qui prouve qui parle : celui du bot, celui de l'agent, celui des mises à jour manuelles |
| **migration** | le changement de la structure de la base qu'une release apporte, appliqué au démarrage après une sauvegarde |
| **passage de 6 h** | la mise à jour quotidienne des messages Discord ([§9.2](09-running-on-its-own.md#daily-pass)) |
| **release** | une version publiée de la Ready Room, par exemple `RR-V1.0.0` |
| **`.rrlog`** | le fichier texte d'une mission, écrit par le hook de l'agent |
| **volume** | un espace de stockage géré par Docker, qui survit aux conteneurs (annexe B) |

## D.2 · Les écrans, en français et en anglais { #screen-names }

La Ready Room suit la langue choisie par chacun (**FR · EN**) : un même écran porte deux noms.

| français | anglais |
|---|---|
| **Planification** | **Scheduling** |
| **Escadre** (station) | **Wing** |
| **Centre de Commandement** | **Command Center** |
| **Manuel Pilote** | **Pilot’s Manual** |
| **Escadre** (écran du Centre) | **Wing** |
| **Escadrilles** | **Squadrons** |
| **Membres** | **Members** |
| **Droits** | **Rights** |
| **Campagnes** | **Campaigns** |
| **Référentiels** | **Reference lists** |
| **Archives** | **Archives** |
| **Configuration** | **Configuration** |

Dans le menu du Centre, **Archives**, **Configuration** et **Référentiels** s'affichent en abrégé : **Arch**, **Config**, **Réf**.

## D.3 · Les blocs et les boutons cités { #labels }

| français | anglais | où |
|---|---|---|
| **Identité de l'escadre** | **Wing identity** | Escadre |
| **Créer une escadrille** | **Create a squadron** | Escadrilles |
| **Faire l'appel** | **Call the roll** | Membres |
| **Diagnostic d'accès** | **Access check** | Membres |
| **Lien de connexion de secours** | **Backup sign-in link** | Membres |
| **Émettre un lien** | **Issue a link** | Membres |
| **Accès à l'application** | **Application access** | Droits |
| **Rôle Discord « chef d'escadrille »** | **Discord role "squadron leader"** | Droits |
| **Commandement des escadrilles** | **Squadron command** | Droits |
| **Édition des événements du planning** | **Planning event editing** | Droits |
| **Accès au module Escadre** | **Access to the Wing module** | Droits |
| **Relances de planning** | **Planning reminders** | Droits |
| **Droits sur le contenu** | **Content rights** | Droits |
| **Invités — démonstration** | **Guests — demonstration** | Droits |
| **Inviter pour 30 jours** | **Invite for 30 days** | Droits |
| **Sauvegardes** | **Backups** | Archives |
| **Sauvegarder maintenant** | **Back up now** | Archives |
| **Sauvegarde automatique** | **Automatic backup** | Archives |
| **Manuelle**, **Automatique**, **Migration** | **Manual**, **Automatic**, **Migration** | Archives, colonne d'origine |
| **Membres archivés** | **Archived members** | Archives |
| **Serveur DCS** | **DCS server** | Archives |
| **Émettre un jeton**, **Remplacer le jeton** | **Issue a token**, **Replace the token** | Archives |
| **Derniers fichiers reçus** | **Latest files received** | Archives |
| **En attente de lecture** | **Awaiting reading** | Archives |
| **Administrateurs** | **Administrators** | Configuration |
| **Paramètres du serveur** | **Server settings** | Configuration |
| **Dossiers du serveur** | **Server folders** | Configuration |
| **Fuseau de l'escadre** | **Wing time zone** | Configuration |
| **Discord — le digest**, **Discord — les réponses** | **Discord — digest**, **Discord — replies** | Configuration |
| **Le Récit du Rapport de mission** | **Mission report narrative** | Configuration |
| **Les tuiles de la carte** | **Map tiles** | Configuration |
| **Les suites (Mission Plan)** | **Suites (Mission Plan)** | Configuration |
