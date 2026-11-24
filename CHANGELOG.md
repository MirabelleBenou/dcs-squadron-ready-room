# Changelog — Ready Room

Ce qui change dans la Ready Room, version par version, pour ceux qui s'en servent. Chaque version publiée sera une release GitHub, sous le tag `RR-V<majeure>.<mineure>.<correctif>` ; la première, `RR-V1.0.0`, se publiera quand l'escadre le décidera.

- Version **majeure** (**x**.0.0) : une refonte, ou un format de fichier qui casse.
- Version **mineure** (1.**x**.0) : un outil, un écran ou une fonction neuve, ou un changement visible partout.
- Version **correctif** (1.2.**x**) : des corrections.

D'ici là, chaque mise à jour installée sur le serveur porte un numéro de développement `v1.0xxx`, affiché au pied de l'accueil, et écrit ses changements sous « Unreleased », dans une section à son numéro.

## Unreleased

### v1.0126 — 2026-11-24
**L'aide des sauvegardes renvoie au guide.**
- À l'écran Archives du Centre de Commandement, l'aide du bloc Sauvegardes indique le chapitre 11 du guide d'installation pour restaurer, au lieu d'un fichier qui n'est plus livré.

### v1.0125 — 2026-11-24
**Le guide d'installation complet, en anglais et en français.**
- Le guide va jusqu'au bout : les premiers réglages, ce qui tourne tout seul, l'agent du serveur DCS, la sauvegarde et la restauration, la mise à jour, le dépannage, la sécurité et la désinstallation, avec les captures de Discord et quatre annexes (fichiers et ports, commandes, glossaire, licence).
- Le guide remplace les notes d'exploitation qui restaient dans le dépôt ; rien de visible ne change dans l'application.

### v1.0124 — 2026-11-24
**Les dossiers du serveur, à la page Configuration.**
- La page Configuration du Centre de Commandement montre les trois dossiers que le serveur branche au démarrage (les suites, les tuiles de la carte DCS, les tuiles gardées) et le nombre de fichiers de chacun : un dossier vide ou introuvable se voit sans ouvrir le serveur.
- À l'écran Droits, l'accès à l'application dit simplement « Géré ici. ».

### v1.0123 — 2026-11-24
**Le Manuel Pilote à jour.**
- Le Manuel décrit le retour et l'adresse de chaque écran, les absents au compteur du jour, une série déplacée, les liens entre la soirée planifiée et son débrief, la page Configuration (fuseau horaire, modèle et effort du Récit, clé de l'escadre) et la page d'entrée en français et en anglais.
- Sa couverture porte la ligne de crédit de la licence, et il se construit aussi sous les numéros de version publiés, comme RR-V1.0.0.

### v1.0122 — 2026-11-24
**Le guide d'installation, premiers chapitres, en anglais et en français.**
- Le guide (site et PDF) se publie avec chaque version : de la préparation du serveur au premier démarrage, et la liste des variables et des réglages, tenue par les tests.
- Deux fichiers pour installer la Ready Room ailleurs : `init-env.sh` écrit le fichier `.env`, `compose.caddy.yml` ajoute un proxy HTTPS ; le projet Docker Compose s'appelle toujours `readyroom`.

### v1.0121 — 2026-11-24
**Les pages d'avant la connexion parlent français et anglais.**
- Les pages de connexion, d'accès refusé et de lien d'entrée suivent la langue du navigateur ; un petit sélecteur FR / EN, sur la page de connexion, garde le choix.
- La commande /readyroom de Discord et ses réponses suivent la langue de Discord de chacun.
- Les messages de démarrage du serveur sont en anglais.

### v1.0120 — 2026-11-23
**Le fuseau horaire de l'escadre se règle.**
- Au Centre, page Configuration, le groupe « Fuseau horaire » des paramètres du serveur fixe le fuseau de l'escadre, Europe/Paris par défaut : les jours de la Planche, les séries, les heures des messages Discord et des rapports, et le passage de 6 h le suivent, sans redémarrage.
- Tant qu'il reste à Europe/Paris, rien ne change.

### v1.0119 — 2026-11-23
**Les fichiers de l'application restent en cache sous un numéro publié.**
- Rien ne change à l'écran : sous un numéro de version publié, comme RR-V1.0.0+3, le navigateur garde les fichiers de l'application en cache jusqu'à la mise à jour suivante, comme aujourd'hui.
- Les fichiers joints à une version publiée, un guide en PDF par exemple, partent avec leur vrai type.

### v1.0118 — 2026-11-23
**La publication des versions se prépare.**
- Rien ne change à l'écran : la Ready Room sait désormais publier ses versions sous le numéro RR-V, le jour où l'escadre le décidera, et ses tests tournent à chaque modification proposée.

### v1.0117 — 2026-11-23
**La licence et le crédit.**
- La Ready Room est sous licence AGPL-3.0-or-later : une ligne discrète, au pied de l'accueil et de l'écran de connexion, dit d'où elle vient, avec le lien vers son dépôt.
- Le dépôt présente l'application en anglais et en français, et dit l'origine et la licence de chaque image, police et table de données.

### v1.0116 — 2026-11-23
**L'insigne sur la tuile du Manuel Pilote.**
- Sur l'accueil, la tuile du Manuel Pilote porte l'insigne de la Ready Room, comme celles de Mission Plan et de Mission Tools portent le leur.

### v1.0115 — 2026-11-23
**Le Manuel Pilote n'illustre plus notre escadre.**
- Les illustrations du Manuel montrent une escadre d'exemple et des pilotes fictifs ; le texte ne change pas.
- Tant que l'escadre n'est pas renseignée, la couverture et la barre du Manuel portent l'insigne générique. L'onglet du Manuel prend l'insigne de la Squadron Ready Room et s'appelle « Manuel pilote — Squadron Ready Room ».

### v1.0114 — 2026-11-23
**Les essais de la Ready Room ne citent plus de vraies personnes.**
- Les jeux d'essai, les exemples et la consigne de rédaction du Récit ne nomment plus que des pilotes et des escadrilles fictifs. Rien de visible ne change.

### v1.0113 — 2026-11-23
**L'insigne au pied des écrans.**
- Dans la Planification, l'Escadre et le Centre de Commandement, le numéro de version en bas à droite est précédé du petit insigne de la Ready Room.

### v1.0112 — 2026-11-23
**L'insigne de la famille Squadron Ready Room.**
- L'onglet du navigateur et le raccourci posé sur l'écran d'accueil d'un téléphone portent l'insigne ; l'onglet s'appelle désormais « Squadron Ready Room ».
- Sur l'accueil, les tuiles Mission Plan et Mission Tools portent l'insigne de leur outil, et la ligne « Squadron Ready Room · version » sous les autres outils remplace le numéro du coin de l'écran ; la page de connexion signe de même.

### v1.0111 — 2026-11-23
**Une connexion perdue se signale.**
- Si la session a expiré pendant que la Ready Room reste ouverte, un message invite à recharger la page, au lieu d'un écran qui cesse de se mettre à jour sans rien dire. Après une simple coupure, la mise à jour en direct reprend seule.

**Du ménage dans le serveur.**
- Rien d'autre de visible ne change : des réglages restés sans effet depuis que la configuration vit dans l'application sont retirés, et le déclencheur Discord n'accepte plus son jeton dans l'adresse.

### v1.0110 — 2026-11-23
**Une installation neuve ne porte plus les couleurs de notre escadre.**
- Tant que son escadre n'est pas renseignée, une nouvelle Ready Room affiche « Squadron Ready Room » et un insigne générique. Chez nous, rien de visible ne change.

**La clé de l'escadre pour Mission Plan se règle dans la Configuration.**
- Laissée vide, elle se tire de la désignation de l'escadre : la clé d'aujourd'hui ne change pas, et les réglages de HQ gardés par les navigateurs des membres restent en place.

### v1.0109 — 2026-11-23
**La liste des modèles du Récit.**
- La demande de la liste des modèles à Anthropic est corrigée ; si Anthropic ne la donne pas, la page Configuration dit pourquoi, sans jamais montrer la clé.

### v1.0108 — 2026-11-23
**Le modèle et l'effort de rédaction du Récit, au choix.**
- À la page Configuration du Centre de Commandement, le modèle qui rédige le Récit se choisit dans la liste des modèles actifs d'Anthropic, et l'effort de rédaction se règle à côté, de « Faible » à « Maximal » : seuls les efforts que le modèle accepte sont proposés.
- Sans clé de l'API ou si Anthropic ne répond pas, l'identifiant du modèle se saisit à la main, comme avant.

**Annuler une modification en cours.**
- Sur chaque réglage, « Annuler » rend la valeur enregistrée tant qu'on n'a pas enregistré.

### v1.0107 — 2026-11-22
**Des liens entre la Planification et l'Escadre.**
- Le bouton « Portail » des messages Discord ouvre directement la fiche de l'évènement, et le résumé de la semaine ouvre le Tableau hebdo.
- La fiche d'un évènement passé montre les missions déposées ce jour-là, et une mission montre la soirée planifiée du même jour : un toucher passe de l'une à l'autre, et le retour ramène d'où l'on vient.

### v1.0106 — 2026-11-21
**La page Configuration du Centre de Commandement.**
- Les administrateurs ont un nouvel onglet « Configuration » au Centre de Commandement : les réglages de Discord, de la rédaction du Récit et du serveur de tuiles s'y modifient sans toucher au serveur, et chaque changement est inscrit au journal des Archives.
- Les clés secrètes n'y apparaissent jamais : la page dit seulement si elles sont renseignées, quand et par qui, et permet de les remplacer ou de les vider.

**Nommer d'autres administrateurs.**
- La même page montre les administrateurs fondateurs, choisis à l'installation, et permet de nommer d'autres administrateurs parmi les membres, ou de les retirer.

### v1.0105 — 2026-11-21
**La configuration du serveur passe dans l'application.**
- Les réglages de Discord, de la rédaction du Récit et du serveur de tuiles sont désormais gardés par la Ready Room elle-même, les clés secrètes chiffrées ; le fichier de configuration du serveur ne garde que ce qu'il faut pour démarrer et se connecter la première fois.
- Les valeurs en place ont été reprises telles quelles : rien de visible ne change. La page pour les modifier viendra avec le Centre de Commandement.

**Des administrateurs nommés dans l'application.**
- Aux administrateurs fondateurs, choisis à l'installation, pourront s'ajouter des administrateurs nommés depuis l'application, sur la même page à venir.

**La mise à jour quotidienne des messages Discord.**
- Chaque matin à 6 h (heure de Paris), la Ready Room met elle-même à jour ses messages de réponse dans Discord.

### v1.0104 — 2026-11-21
**Une série déplacée repart à zéro.**
- Quand on change la date de début, les jours ou le rythme d'une série, ou le jour d'un évènement unique, ses réponses à venir et ses dates modifiées ou annulées à venir s'effacent ; une note sous « Enregistrer » dit combien, avant de confirmer.
- Changer l'heure seule n'efface rien ; avancer la fin d'une série n'efface que les dates qu'elle retire.

**Deux personnes sur le même évènement.**
- Si quelqu'un l'a modifié pendant que vous l'éditiez, l'enregistrement est refusé et vous invite à le rouvrir : rien n'est écrasé.

**Des tests pour la Planification.**
- La répétition des séries, changements d'heure du printemps et de l'automne compris, et les droits de créer et de modifier un évènement sont vérifiés automatiquement. Rien de visible ne change.

### v1.0103 — 2026-11-21
**Les absents au compteur du jour.**
- Au bas de chaque case de la Planche, le compteur montre aussi les absents : présents ✓, peut-être ~ et absents ✗, sans avoir à survoler la case.

**Enregistrer un évènement, sans doublon.**
- Un double clic sur « Enregistrer » ne crée plus deux évènements : le bouton attend la réponse du serveur.
- La durée d'un évènement s'efface : un champ vidé retire la durée.
- Une date passée en jeu libre ne garde plus la carte DCS de sa série.
- Le titre ne peut plus être fait que d'espaces ; le titre, le jeu et la description ont une longueur maximale ; une série ne peut plus finir avant son premier jour.

**Une Planche plus légère.**
- Le calendrier ne charge plus les évènements passés qu'il n'affiche pas. Rien de visible ne change.

### v1.0102 — 2026-11-21
**Le journal des nouveautés.**
- Ce fichier dit désormais ce qui change pour ceux qui se servent de la Ready Room, sans détails techniques ; l'historique technique des versions précédentes passe dans `JOURNAL_TECHNIQUE.md`. Rien de visible ne change dans l'application.

### v1.0101 — 2026-11-21
**Le retour et l'adresse.**
- Le retour d'Android ou du navigateur ne quitte plus la Ready Room : il remonte d'un niveau, exactement comme la flèche ‹ — une fiche se ferme, un vol revient à sa session, un onglet revient aux stations.
- Chaque écran a son adresse : un rechargement garde l'écran affiché, et une adresse copiée ouvre le même écran, même s'il faut d'abord se connecter. Une adresse qui ne mène plus nulle part ouvre l'écran le plus proche et le dit.
