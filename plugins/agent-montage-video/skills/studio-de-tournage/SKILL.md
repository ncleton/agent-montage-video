---
name: studio-de-tournage
description: Créer le studio de tournage d'un outil web que nous avons construit (copie locale avec compte de démonstration aux droits de base, entreprises réelles, personnes et rendez-vous fictifs, aucun accès de production), puis tourner et monter un tutoriel d'interface 4K qui met l'interface en valeur - Playwright, zoom automatique sur chaque geste, curseur, sous-titres, voix. Utiliser pour toute vidéo de prise en main ou de formation d'un outil de l'ERP Rossini (Bigup, Rossini CRM, Appels d'offres, Formation, Administration, Plane, outil futur), pour une commande « tutoriel d'interface » d'Apolline, ou quand on demande de « filmer » un outil. Pas pour un enregistrement d'écran déjà fourni (openvid-interface-video) ni pour un film sans interface (motion-explainer).
---

# Studio de tournage

Un tutoriel d'interface se tourne toujours dans un studio : une copie locale de l'outil, sur le poste de montage,
où l'on peut tout cliquer sans risque. On ne filme jamais l'outil en production ni avec un vrai compte.

## Les règles du studio, les mêmes pour chaque outil

1. **Même code que la production** : le commit déployé de l'outil, construit et lancé en local. Ce que voit la
   vidéo est ce que l'équipe verra.
2. **Un compte de démonstration aux droits de base** du rôle visé (commercial, technicien AO…), réglés comme pour
   un collègue. Jamais un compte administrateur, sauf pour un tutoriel de l'administration. Il porte un nom fictif
   et n'existe que dans le studio.
3. **Données de vitrine** : des entreprises réelles tirées au hasard, avec leurs données publiques (nom, logo,
   adresse, score, cartes, sources) ; des personnes fictives (nom, e-mail, téléphone inventés) ; des rendez-vous,
   tournées et échanges fictifs. Aucune donnée personnelle réelle à l'image.
4. **Aucun accès de production** : le studio ne reçoit ni jeton HubSpot, Google, Slack, Nextcloud ou d'enrichissement
   payant, ni le secret de passerelle de la production. Une action qui sortirait du studio échoue ou part vers un bac
   à sable (compte de test HubSpot), jamais vers les vraies données. C'est une garantie par construction : on ne
   compte pas sur la prudence d'un agent.
5. **Local seulement** : tout écoute sur 127.0.0.1, sur le poste de montage.
6. **Aucun manque à l'écran** : chaque écran filmé est complet, comme chez un commercial bien installé. Pas de message
   d'erreur, de réglage manquant (« HubSpot n'est pas configuré »), d'état vide (« Aucun secteur n'est prévu »), de
   chargement sans fin (« Calcul... », « Recherche en attente »), de valeur « À valider » ou « introuvable », de ligne
   répétée (six fois la même source), d'image cassée, de couverture ou de logo vide (une icône à la place de l'image)
   ni de fiche ou de panneau qui sort de l'écran. Le studio n'a pas internet : une image de démonstration est un
   fichier du studio (`studios/<outil>/assets`) servi par le Site local. Un manque se corrige dans le studio
   (semis, réglage, secteur de tournée, portail de test), jamais en évitant l'écran ni en le recadrant ; un défaut de
   l'outil lui-même (étiquettes en double) se corrige dans l'outil et se publie. Les volumes sont ceux de la
   production : la case Prospects de Bigup montre toujours 25 prospects, dont quelques ajouts manuels.

Avant de tourner, vérifier et noter dans le dossier du projet (`work/studio-check.md`) : commit de l'outil, compte
et rôle filmés, absence de chaque secret de production (variables lues, pas supposées), échantillon d'entreprises,
et une capture de la page de départ relue.

## Le déroulé

1. **Studio** : s'il n'existe pas encore pour l'outil, le construire selon [references/studio-erp.md](references/studio-erp.md),
   puis le garder dans `studios/<outil>/` (scripts versionnés, données et secrets hors Git). Sinon le mettre au
   commit déployé et le relancer.
2. **Scénario** : écrire le parcours (`work/scenario.json`) d'après le bon de commande : un objectif par vidéo, les
   gestes du rôle filmé, un repère `mark` par phrase de la voix, et chaque passage obligé de la section « Ce que
   chaque tutoriel montre » du README du studio pour les écrans filmés. Format et cibles :
   [references/scenario.md](references/scenario.md).
3. **Contrôle des écrans** : `node scripts/studio_check.mjs work/scenario.json work/check` rejoue le scénario sans filmer et lit
   chaque écran : ouverture, chaque repère, **après chaque geste** (le panneau qu'un clic ouvre est relu) et fin. Un
   constat bloquant arrête tout : corriger le studio, relancer, et noter le résultat dans `work/studio-check.md`.
   Après le rendu, la revue image par image (`video-frame-review`) vérifie encore que rien n'est coupé par le cadre.
4. **Tournage** : `node scripts/studio_record.mjs work/scenario.json work/rec` -> `raw.mp4` (4K, 60 i/s) et
   `timeline.json` (curseur, clics, frappes, repères). Une étape introuvable arrête le tournage avec la cible
   exacte : corriger le scénario, jamais la page.
5. **Caméra** : `python3 scripts/studio_camera.py work/rec/timeline.json work/rec/camera.json`.
6. **Montage** : kit `kits/tuto-interface` (Remotion) dans le style du bon (`python3 scripts/studio_style.py <style> motion`,
   pixel-rpg par défaut, styles/README.md pour en créer un) : ouverture et fermeture du style, zooms, curseur, onde
   au clic, sous-titres, voix. Règles de réalisation : [references/mise-en-valeur.md](references/mise-en-valeur.md).
7. **Voix, vérification, publication** comme toute vidéo du dépôt (AGENTS.md) : voix VoiceStudio calée sur les
   repères, `video-frame-review` sur le rendu, 4K, publication Mux ; pour une commande de l'ERP, fin par le skill
   `commande-erp`.
