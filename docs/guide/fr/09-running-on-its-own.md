# 9 · Ce qui tourne tout seul { #running-on-its-own }

La Ready Room n'a besoin d'aucune tâche planifiée sur le serveur : ni `cron`, ni minuteur. Trois travaux tournent dans
l'application elle-même, tant que le conteneur `app` est en marche. Ce chapitre dit lesquels, quand, et comment
vérifier qu'ils ont tourné.

## 9.1 · L'appel { #roll-call-schedule }

L'appel ([§8.4](08-first-settings.md#roll-call)) part **une minute après chaque démarrage**, puis **toutes les 24
heures**. Il compte par intervalle, pas à heure fixe : un redémarrage le décale. À la fin de chaque appel réussi, les
**relances de planning** ([§8.5](08-first-settings.md#rights)) partent à leurs destinataires.

## 9.2 · Le passage quotidien de 6 h { #daily-pass }

Chaque jour à **6 h dans le fuseau de l'escadre** ([§7.5](07-first-start.md#time-zone)), heure d'été comprise, la Ready
Room remet à jour ses messages dans Discord : le digest, ou les messages de présence si **Réponses dans Discord** est
allumé ([§7.6](07-first-start.md#discord-settings)). Elle le fait aussi à chaque démarrage, et le digest suit chaque
changement du planning sans attendre le lendemain.

## 9.3 · Les sauvegardes automatiques { #automatic-backups }

**Centre de Commandement › Archives**, bloc **Sauvegardes**, ligne **Sauvegarde automatique**, deux listes :

1. la fréquence : **Toutes les 24 h** par défaut ; aussi 6, 12 ou 48 heures, **Tous les 7 jours**, ou **Désactivée** ;
2. la rétention : **Garder les 7 dernières** par défaut ; aussi 3, 14 ou 30.

Le choix s'enregistre aussitôt. La Ready Room contrôle toutes les heures l'âge de la dernière sauvegarde automatique,
et en prend une quand l'intervalle est passé ; la plus ancienne au-delà de la rétention s'efface. Une sauvegarde prend
**la base et les écussons**, comme le bouton **Sauvegarder maintenant** ; ce qu'elle ne prend pas est au
[§11.1](11-backup-and-restore.md#what-a-backup-holds).

!!! warning "Attention"
    **Désactivée** ne laisse que les sauvegardes que vous prenez à la main et celles d'avant chaque migration. Ne
    désactivez pas sans une autre sauvegarde de la machine.

## 9.4 · Vérifier qu'ils ont tourné { #check-tasks }

| travail | à l'écran | dans le journal |
|---|---|---|
| l'appel | **Membres** : « Dernier appel · *date* · *heure* » | `Appel (demarrage) : …`, puis `Appel (quotidien) : …` |
| le passage de 6 h | vos messages Discord, à jour au matin | `roll: … posted, … edited, … deleted` (messages de présence seulement) |
| les sauvegardes | **Archives** : « Dernière : *date* · *heure* », et une ligne d'origine **Automatique** dans la liste | `Sauvegarde automatique : …` |

Pour lire le journal :

```sh
cd /opt/readyroom
docker compose logs --since 48h app | grep -E "Appel \(|roll:|Sauvegarde automatique"
```

!!! failure "Si ça ne marche pas"
    - **Archives** affiche « Échec de la dernière tentative (…) : … » : la raison suit ; le plus souvent, le disque est
      plein (`df -h`).
    - Aucune ligne `Appel (…)` depuis plus d'un jour : `docker compose ps` — `app` doit être `Up` ; sinon, le
      [§7.2](07-first-start.md#logs).
    - Le journal porte `Passage quotidien Discord : erreur non bloquante` : le passage a échoué ce jour-là ; la raison
      suit, sur les lignes d'après. Le passage du lendemain se joue normalement.

## 9.5 · Les déclencher à la main { #manual-triggers }

Les trois travaux se lancent aussi à la main :

- **l'appel** : **Membres › Faire l'appel** ;
- **une sauvegarde** : **Archives › Sauvegarder maintenant** ;
- **les messages Discord**, sans attendre 6 h : une commande, depuis le serveur, protégée par un jeton.

Le jeton se règle une fois : **Configuration › Paramètres du serveur**, groupe **Discord — le digest**, **Jeton des
mises à jour manuelles**, **Saisir**, une longue chaîne aléatoire que vous gardez (par exemple
`openssl rand -hex 32`), **Enregistrer**. Vide, les mises à jour manuelles sont refusées ; le passage de 6 h n'en a pas
besoin. Les deux commandes sont à l'[annexe C](c-commands.md#discord-triggers).

!!! success "Vérifier"
    La commande affiche `204` et les messages Discord sont à jour. `403` : le jeton n'est pas celui enregistré.

## 9.6 · Où vous en êtes { #where-you-are }

- [ ] **Membres** montre un dernier appel de moins de 24 heures.
- [ ] **Archives** montre la fréquence et la rétention voulues, et une première sauvegarde **Automatique**.
- [ ] *(facultatif)* Le jeton des mises à jour manuelles est enregistré et gardé.

Le chapitre 10 branche votre serveur DCS.
