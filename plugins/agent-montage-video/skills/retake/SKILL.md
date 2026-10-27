---
name: retake
description: Traiter une revue vidéo envoyée par un relecteur (Tony, un client) avec l'application Retake - archive .zip contenant rapport.md, rapport.json, images annotées et commentaires vocaux WAV. Vérifier la version relue, transcrire les commentaires vocaux, relier chaque commentaire à la scène et à la voix off, corriger, rendre une nouvelle version et répondre point par point. Utiliser dès qu'une « revue », un fichier « Retake … .zip » (ou « Revue … .zip » pour les premières revues), un rapport.json de Retake ou des retours horodatés sur une vidéo arrivent, et pour envoyer l'application Retake à un relecteur.
---

# Retake, revue vidéo

L'application **Retake** (`tools/retake/`, Mac et Windows) permet à un relecteur de regarder un rendu et de
commenter à l'image près en écrivant, en entourant une zone ou en parlant. Elle produit une archive
`Retake <vidéo> - <prénom> - <date>.zip`. Ce skill transforme cette archive en corrections.

## 1. Envoyer une vidéo à relire

Envoie au relecteur le MP4 exact du rendu (H.264 + AAC), jamais une version recompressée par une
messagerie : l'empreinte SHA-256 du fichier relu doit être celle de `projects/<p>/out/`. Si le relecteur
n'a pas encore l'application, envoie l'installateur de `tools/retake/dist/` et la notice
`tools/retake/LISEZMOI-Tony.md`.

## 2. Recevoir la revue

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
- Une transcription peut déformer un nom propre ou un chiffre : en cas de doute, écoute le WAV.
- Si une remarque est ambiguë, pose la question au relecteur en citant l'instant, plutôt que de deviner.

## 4. Corriger et répondre

Corrige dans les sources du projet (script, timeline, scènes), rends à nouveau, applique
`video-frame-review`, puis réponds commentaire par commentaire : corrigé (et comment), ou non corrigé
(et pourquoi). Envoie la nouvelle version : le relecteur l'ouvre dans Retake, importe la revue précédente
(menu Fichier > Importer la revue précédente) et marque chaque point Corrigé ou Pas corrigé. Sa nouvelle
archive porte ces statuts dans `rapport.json` (`summary.fixed`, `summary.notFixed`).

## 5. Maintenir l'application

Code dans `tools/retake/` (Electron). Tests :

    cd tools/retake
    REVUE_TEST_VIDEO=<rendu.mp4> REVUE_TEST_VIDEO2=<autre.mp4> REVUE_TEST_VOICE=test/fixtures/voix.wav node test/e2e.mjs
    REVUE_TEST_VIDEO=<rendu.mp4> REVUE_TEST_FRAMES=828,1574,1859 node test/precision.mjs && ../../.venv/bin/python test/check_frames.py

Installateurs : `npm run dist:mac` (DMG Apple Silicon et Intel, signature ad hoc) et `npm run dist:win`.
Le dépôt public `ncleton/retake` est une copie de `tools/retake` : à chaque envoi, son workflow
GitHub Actions rejoue ces tests sur une machine Windows réelle et y fabrique l'installateur Windows natif
(artefact `installateur-windows`). Recopie le dossier dans ce dépôt après chaque modification de l'application.
