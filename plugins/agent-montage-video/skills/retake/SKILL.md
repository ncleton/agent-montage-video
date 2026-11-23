---
name: retake
description: Faire relire un rendu dans Retake en ligne (https://retake.rossini-ener-0158.chatgpt.site, lien court créé à chaque publication Mux), récupérer le dossier envoyé quand le relecteur clique sur Terminé, puis traiter la revue - rapport.md, rapport.json, images annotées (zones, flèches, points) et commentaires vocaux WAV. Vérifier la version relue, transcrire les vocaux, relier chaque commentaire à la scène et à la voix off, corriger, rendre une nouvelle version et répondre point par point. Utiliser dès qu'une vidéo est publiée sur Mux, qu'on parle de relecture, de lien Retake, d'une revue terminée, d'un identifiant rv_…, d'un fichier « Retake … .zip » ou de retours horodatés sur une vidéo.
---

# Retake, revue vidéo

**Retake en ligne** (https://retake.rossini-ener-0158.chatgpt.site, ouvert à l'espace Rossini Energy avec la connexion
ChatGPT) montre un rendu Mux au relecteur, qui commente à l'image près en écrivant, en entourant une zone, en traçant
une flèche, en pointant un endroit ou en parlant. Le bouton **Terminé** envoie le dossier de la revue au Site, où tu le
récupères. L'application de bureau Retake ([ncleton/retake](https://github.com/ncleton/retake), Mac et Windows) produit
le même dossier en archive `Retake <vidéo> - <prénom> - <date>.zip`. Ce skill transforme ce dossier en corrections.

## 1. Donner le lien de relecture, toujours

Chaque publication Mux finit par le lien Retake du rendu : `scripts/publish_mux.py` déclare la revue au Site
(`scripts/retake_link.py`), écrit `retake.id` et `retake.url` dans le `.mux.json` et affiche
« Lien de relecture Retake : https://retake.rossini-ener-0158.chatgpt.site/rv_… ». Termine toujours ta réponse ou ton
résumé par ce lien, à côté du lien Mux. Pour une commande de l'ERP, `report finish` l'ajoute au résumé et refuse un
`.mux.json` sans lien.

- Nouvelle version d'une vidéo déjà relue : publie avec `--revue-precedente out/<version précédente>.mux.json`. Le
  relecteur retrouve alors chaque point de la revue précédente et le marque Corrigé ou Pas corrigé.
- Lien manquant (publication faite avant, ou erreur affichée par `publish_mux.py`) :
  `python3 scripts/retake_link.py --mux out/<film>.mux.json [--precedente …] [--video out/<film>.mp4]`.
- Configuration : `~/.config/montage-video/retake.json` (droits 600) avec `url`, `secret` (variable `RETAKE_SECRET` du
  Site) et `sites_token` (jeton de service du Site). Ne l'affiche ni ne le commite jamais. S'il manque sur un poste,
  dis-le à l'utilisateur : Nicolas Cléton le copie depuis le VPS des agents.
- La vidéo relue est le MP4 `highest.mp4` de Mux. Le rapport porte l'empreinte SHA-256 du rendu local publié, et les
  images du relecteur sont comparées à ce rendu.

## 2. Recevoir la revue

Quand le relecteur a cliqué sur Terminé (il te le dit, ou la personne te demande de traiter sa revue) :

    python3 scripts/retake_fetch.py out/<film>.mux.json            # ou l'identifiant rv_… de la revue
    python3 scripts/retake_fetch.py out/<film>.mux.json --attendre 60   # attendre jusqu'à 60 min qu'elle soit terminée
    python3 scripts/retake_fetch.py --liste                         # les revues terminées, les plus récentes d'abord

Le dossier arrive dans `output/retake/<Retake … - prénom - date>/`. Si le relecteur renvoie sa revue, la dernière
remplace la précédente. Traite ensuite ce dossier (ou une archive .zip de l'application de bureau) :

Un relecteur peut aussi coller un lien Mux sur la page d'accueil de Retake en ligne. Il retombe sur ta dernière revue
de cette vidéo, ou, pour une vidéo publiée avant Retake, sur une revue sans empreinte : `--liste` la montre comme les
autres, et `ingest_review.py` retrouve le rendu par le `.mux.json` qui porte son identifiant Mux.

    .venv/bin/python plugins/agent-montage-video/skills/retake/scripts/ingest_review.py "<Retake ….zip>" --vocabulaire "noms propres du projet"

Le script :

- retrouve le rendu relu par son empreinte SHA-256 et s'arrête si aucun fichier ne correspond ;
- extrait la revue dans `projects/<p>/work/reviews/<nom>/` ;
- compare chaque image du relecteur aux images n-2 à n+2 du rendu avec ffmpeg (« identique au rendu ») ;
- transcrit les commentaires vocaux avec `transcrire` (skill `transcription-audio-fr`, Mac mini de Tony) ;
- relie chaque commentaire à la scène, au chapitre et aux mots de voix off prononcés à cet instant
  pour les projets Remotion maison (`work/layout.json`, `motion/src/script.json`, `audio.json`).

Il écrit `corrections.md` et `corrections.json`. Lis `corrections.md` en entier et ouvre chaque
`images/*-annotee.jpg` avant de modifier quoi que ce soit.

## 3. Interpréter

- Un commentaire vocal sans repère est dit après avoir vu le problème : regarde aussi les 3 secondes
  qui précèdent (ligne « regarde aussi »).
- Les repères sont en pixels de la vidéo, origine en haut à gauche.
- Une flèche pointe vers ce qu'il faut regarder : la pointe (`toPx` dans rapport.json) désigne l'endroit, le départ
  n'a pas de sens.
- Une transcription peut déformer un nom propre ou un chiffre : en cas de doute, écoute le WAV.
- Si une remarque est ambiguë, pose la question au relecteur en citant l'instant, plutôt que de deviner.

## 4. Corriger et répondre

Corrige dans les sources du projet (script, timeline, scènes), rends à nouveau, applique
`video-frame-review`, puis réponds commentaire par commentaire : corrigé (et comment), ou non corrigé
(et pourquoi). Publie la nouvelle version avec `--revue-precedente` et donne son lien Retake : le relecteur y
retrouve chaque point et le marque Corrigé ou Pas corrigé. Sa nouvelle revue porte ces statuts dans `rapport.json`
(`summary.fixed`, `summary.notFixed`).

## 5. Maintenir Retake

- Retake en ligne : Site Sites `appgprj_6b0464c2b9e8819195682af0e3e0bc90` (source dans son dépôt Sites, README à la
  racine), un Worker et le stockage R2 du Site, sans base de données.
- Application de bureau : dépôt [ncleton/retake](https://github.com/ncleton/retake) ; lis son `AGENTS.md` avant toute
  modification. La CI y teste chaque changement sur Windows et sur Mac, et un tag `vX.Y.Z` publie les installateurs.
