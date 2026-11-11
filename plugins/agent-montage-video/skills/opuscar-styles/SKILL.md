---
name: opuscar-styles
description: Réaliser un court film entièrement dessiné en code dans l'un des 66 styles de la bibliothèque Lemo-Opuscar (aquarelle, ukiyo-e, blueprint, keynote sombre, infographie isométrique, briefing satellite, éclaté produit, carte de métro, rendu verre 3D, news télé, montage d'archives…) ou dans un style personnel dérivé, par exemple aux couleurs d'un client. Utiliser quand l'utilisateur demande une vidéo, un film, une animation, un teaser ou une explication dans un style visuel nommé, veut savoir quels styles existent, veut un style à lui, ou demande un film sans rushes sur son sujet. Ne pas utiliser pour monter des rushes (HyperFrames), habiller une capture d'écran (openvid) ou un tutoriel pédagogique long (motion-explainer).
---

# Films en code, styles Lemo-Opuscar

La bibliothèque Lemo-Opuscar (github.com/lemomo-ai/lemo-opuscar, code MIT) fournit pour
chaque style un `STYLE.md` (les invariants du style), un film de démonstration et un
outillage commun : une page web `render(t)` capturée image par image dans Chrome headless,
une partition originale jouée par des banques d'instruments libres, des bruitages
procéduraux et un mastering FFmpeg. Elle se réalise selon ses propres guides. Ce skill
fixe où elle s'installe et ce qui change pour respecter les règles de l'agent.

## Installer

    scripts/setup_linux.sh --check        # READY attendu (ffmpeg 7+, Node 20+, git)
    scripts/opuscar.sh deps                # bibliothèque au commit vérifié + paquets de rendu

La bibliothèque vit dans `tools/lemo-opuscar` (hors Git), épinglée par `OPUSCAR_COMMIT`
dans `scripts/opuscar.sh`. La dernière ligne affiche `LIB=<chemin>`. Ajouter
`scripts/opuscar.sh deps music` seulement pour des cordes pincées (`pluck.py`). Ne pas
installer `deps voice` : la voix suit les règles maison ci-dessous. Python 3.11 à 3.13 ou
`uv` est nécessaire ; s'il manque, donner l'erreur exacte à l'administrateur.

Pour mettre la bibliothèque à jour : lire le diff amont depuis le commit épinglé, changer
`OPUSCAR_COMMIT`, puis rendre une image d'un style 2D et d'un style 3D avant de commiter.

## Choisir le style

La liste est dans `$LIB/styles/README.md`, la galerie de démonstration sur
https://lemomo-ai.github.io/lemo-opuscar/ . Si l'utilisateur n'a pas choisi, proposer deux
ou trois styles adaptés à son sujet, puis donner la liste complète par catégorie avec les
noms anglais et le lien de la galerie, et lui demander d'écrire le nom. Ses styles
personnels (`~/lemo-my-styles/README.md`) passent en premier. Pour un style aux couleurs
d'un client ou un style partant de zéro, suivre `$LIB/MY-STYLES.md`.

## Réaliser

Lire `$LIB/AGENTS.md`, puis `$LIB/DIRECTOR.md`, `$LIB/TECHNIQUE.md` et
`$LIB/styles/<slug>/STYLE.md`, et suivre leur déroulé : brief en une seule série de
questions, `TREATMENT.md` avec trois structures avant d'ouvrir la démo, images de style
rendues avec le vrai code, production, revue, une seule passe de corrections.

| Dans les guides | Pour l'agent |
|---|---|
| `films/<nom>/` | `projects/<projet>/opuscar/` (minuscules, chiffres, tirets) ; les sources reçues restent dans `projects/<projet>/sources/` |
| Lancer un outil | depuis `$LIB` avec le chemin absolu du projet : `cd "$LIB" && node core/render/still.mjs "<projet>" 1.5 3` |
| Fichiers de la bibliothèque dans la page | URL absolues : `/core/lib.js`, `/node_modules/three/…` |
| `build.sh` | `LIB=${LIB:-$(cd "$HERE/../../../tools/lemo-opuscar" && pwd)}` en tête, toujours entre guillemets (le dossier de l'agent contient une espace) |
| Démo du style | `scripts/opuscar.sh demo <slug>` après `TREATMENT.md`, pour lire ses techniques ; un style « Edit & Documentary » peut utiliser plus tôt les outils de matériau de `demo/tools/` cités par son `STYLE.md` |
| Questions | en français, avec l'outil de questions s'il est disponible, sinon en texte simple ; pas de question de langue |
| Images par seconde | celles du `STYLE.md`, 24 i/s par défaut : l'animation en pas de deux fait partie du style, la règle des 60 i/s vaut pour Remotion |

Ne rien modifier dans `core/` ni `styles/` pour un film : copier dans le projet.

## Règles maison qui remplacent la bibliothèque

**Brief.** Ajouter à la série de questions la source de musique (ci-dessous) et, si le
film a une voix, le texte ou le sujet de la narration. Storyboard seulement si
l'utilisateur le demande.

**Voix off.** Première version avec VoiceStudio (VoxCPM2), jamais Kokoro ni edge-tts :
écrire `work/script.json` (une scène par réplique de la timeline, `narration` et
`spoken`), puis `tts_scenes.py` et `voice_scenes.py` du skill
`meet-video-pedagogique` avec ses réglages. Diriger la sortie vers le projet :

    SK=plugins/agent-montage-video/skills/meet-video-pedagogique
    python3 $SK/scripts/tts_scenes.py projects/<p>/work/script.json projects/<p>/work/voice-scenes
    .venv/bin/python $SK/scripts/voice_scenes.py projects/<p>/work/script.json projects/<p>/work/voice-scenes projects/<p>/opuscar/voice projects/<p>/opuscar/audio.json

`audio.json` donne pour chaque scène le fichier, la durée et les mots horodatés : la
timeline du film (`timeline.js`), les sous-titres et les déclenchements visuels en
dérivent. ElevenLabs remplace la voix seulement après validation du film par Nicolas,
selon `voice-intonation` ; tout se rend alors à nouveau. Un enregistrement fourni par
l'utilisateur passe avant tout.

**Musique.** Demander la source et ne jamais en changer en silence :

- `opuscar_score` : partition originale écrite pour ce film avec `core/audio/sampler.py`,
  dans les instruments de la palette sonore du `STYLE.md` ; télécharger les banques
  nommées par l'erreur avec `scripts/opuscar.sh instruments <banque>` (70 à 420 Mo
  chacune) ;
- `file`, `local_procedural` ou `elevenlabs`, comme dans `AGENTS.md`.

Les skills `mc-*` servent au brief musical. La grille musicale précède l'animation
(DIRECTOR.md §7).

**Bruitages.** `core/audio/sfx.py` (procédural, local) piloté par `window.EV`, ou
`scripts/generate_sfx.py` pour un son que la synthèse ne rend pas.

**Volume.** `core/render/mux.sh` masterise à -14 LUFS ; les livrables de l'agent sont à
-16 LUFS. Après `mux.sh`, appliquer un gain mesuré, qui garde le mastering et copie
l'image (un second `loudnorm` en une passe manque la cible d'environ 0,6 LU) :

    python3 scripts/normalize_loudness.py projects/<p>/opuscar/out/<nom>-14.mp4 projects/<p>/out/<nom>.mp4

**Rendu.** Sur le Mac mini de Tony, la bibliothèque utilise le GPU (Metal) sans réglage :
mesuré 1,7 s par image pour un style 3D (Glass Product), moins de 0,1 s pour un style 2D
(Swiss Motion, 44 s de film rendues en 11 s). Ne pas y mettre `LEMO_ANGLE=swiftshader`.
Seule une machine Linux sans GPU en a besoin pour les styles WebGL ou three.js, avec une
image identique environ 5 fois plus lente. Avant le rendu complet, mesurer deux images,
annoncer la durée estimée, puis donner l'avancement et l'heure de fin pendant le rendu.
Lancer `video.mjs` avec `--workers` adapté aux cœurs disponibles (3 par défaut, 6 au plus).

**Cartes.** Garder la sobriété de DIRECTOR.md §13 : pas de frontières sauf si le sujet
l'exige, cadrage régional, données de carte citées dans `CREDITS`. Les tracés imposés
pour certains territoires relèvent des choix éditoriaux de l'auteur de la bibliothèque :
suivre la demande du client et des données de référence citées.

## Vérifier et livrer

1. La revue de la bibliothèque : planches, `readcheck.mjs` si la page expose
   `window.TEXTS`, contrôle de la voix, comparaison avec la démo (DIRECTOR.md §11).
2. Le skill `video-frame-review` sur le MP4 normalisé : 0 image isolée avec
   `detect_inserted.py`, planches sur toute la durée, chaque demande vérifiée à un instant
   précis. Après toute correction, rendre à nouveau et refaire la vérification.
3. Livrer dans `projects/<p>/out/` : `<nom>.mp4`, `poster.jpg`, `<nom>.srt` si le film
   parle ; garder dans `projects/<p>/opuscar/` `TREATMENT.md`, `CREDITS` (banques
   d'instruments, polices, voix, données) et le `build.sh` qui reconstruit tout.
4. Publication Mux selon `AGENTS.md`, après accord sur le titre.

Les films produits appartiennent à l'utilisateur, sans mention LemoLab. Les films de
démonstration sont sous CC BY 4.0 et ne se réutilisent pas dans un livrable ; six pistes
de voix de démos sont exclues de toute réutilisation (README de la bibliothèque).
