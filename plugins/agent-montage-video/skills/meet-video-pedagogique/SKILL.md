---
name: meet-video-pedagogique
description: Transformer l'enregistrement d'une réunion Google Meet (formation, point technique, démonstration avec partage d'écran) en vidéo pédagogique motion design qui n'oublie aucune notion - récupération de la vidéo et des notes Gemini sur Drive, transcription vérifiée, inventaire des notions avec preuves horodatées, choix des moments d'écran partagé, script réécrit, voix off open source VoiceStudio (VoxCPM2) ou ElevenLabs, rendu Remotion avec captures citées à la seconde, contrôle de couverture et vérification image par image. Utiliser dès qu'on fournit un lien Meet, des « Notes by Gemini », un enregistrement de réunion ou de formation à transformer en vidéo, tutoriel, capsule ou formation.
---

# Vidéo pédagogique à partir d'un enregistrement Meet

Le but est une vidéo qu'un collègue absent peut regarder pour apprendre tout ce qui a
été enseigné, sans regarder la réunion. Trois exigences ne se négocient pas :

1. **Aucune notion oubliée.** Chaque notion évoquée dans la réunion est dite ou montrée
   dans la vidéo. `check_coverage.py` le prouve.
2. **Rien d'inventé.** Chaque notion repose sur une preuve horodatée de l'enregistrement.
   Les notes Gemini servent de sommaire, jamais de source : elles se trompent sur les
   noms, les normes et les chiffres.
3. **Références strictes aux captures.** Une capture montrée vient de l'enregistrement,
   avec son horodatage affiché (« Réunion · 00:23:41 »). Pas de capture recomposée ni
   retouchée, à part le recadrage sur l'écran partagé et le flou d'une donnée personnelle.

Le script appartient à l'agent : il réécrit la réunion en cours clair, dans l'ordre qui
facilite l'apprentissage, plutôt que dans l'ordre de la conversation.

Projet : `projects/<nom>/` avec `sources/`, `work/`, `out/`, `motion/`. Les scripts sont
dans `scripts/` de ce skill (appelés `$SK/scripts` ci-dessous) ; le gabarit Remotion est
dans `template/`.

## 1. Récupérer la réunion

Le document « Notes by Gemini » contient l'onglet de notes, parfois un onglet
Transcription, et les liens « Enregistrement » (vidéo) et « Notes par Gemini (Anglais) ».

- Lire le document avec le plugin Google Drive (`get_document` avec l'**ID** du document,
  pas l'URL), parcourir tous les onglets et relever les liens `richLink`.
- Télécharger la vidéo avec `fetch` (`download_raw_file: true`, `include_base64: false`).
- Meet ne partage l'enregistrement qu'avec les **invités** de la réunion. Si le compte
  connecté au plugin n'en faisait pas partie, Drive répond 404 « File not found » même
  quand la personne qui envoie le lien y a accès dans son navigateur. Le dire tel quel,
  avec le compte utilisé et la liste des invités, et demander l'une de ces options : partager
  la vidéo avec le compte du plugin, ou envoyer le MP4. Ne jamais contourner avec des
  cookies de navigateur.
- Ranger la vidéo dans `sources/` sans la commiter.

## 2. Transcrire et analyser avec l'agent vidéo Gemini (obligatoire)

La transcription et l'analyse détaillée passent **toujours** par l'agent vidéo Gemini de
RossiniEnergy, conçu pour cela : transcription intégrale horodatée par extraits de
10 minutes, locuteurs, textes à l'écran, timeline des étapes, captures d'écran choisies et
décrites (contenu et données lisibles). Ne pas refaire ce travail avec un autre outil.

- Avec le plugin ChatGPT « Vidéos RossiniEnergy » (skill `videos-rossinienergy`) quand ses
  outils sont branchés : `create_upload_link` ou `submit_video_link`, suivi par `get_job`,
  lecture par `get_video` et `read_transcript`.
- Sinon en local, sur le Mac qui porte `Gestion projet Rossini` :

      cd ~/Documents/"Gestion projet Rossini"
      /usr/bin/python3 scripts/rossini_video.py ingest <video.mp4> --title "<titre>" --note "<contexte>"
      /usr/bin/python3 scripts/rossini_video.py show <vid-…>

  Les sorties sont dans `data/videos/<vid-…>/` : `transcript.json` / `transcript.md`,
  `analysis.json` (timeline), `screenshots.json` et les captures décrites, `insights.json`.
  `ingest` ne publie rien ; ne pas lancer `plane-sync` sans demande explicite.
- Whisper local (`transcrire`, skill `transcription-audio-fr`) sert seulement de seconde
  écoute pour trancher un passage douteux, jamais de transcription principale.

Relire **toute** la transcription, pas un résumé. Pour chaque passage technique,
confronter : transcription, notes Gemini, et ce que montre l'écran partagé au même
instant. Corriger les erreurs d'écoute avec l'écran (un tableur ou un document affiché fait
foi pour un chiffre ou un nom) et avec une source officielle pour les normes et les
produits. Refaire les calculs énoncés à l'oral. Un point qui reste incertain est marqué
`doubtful` et doit être tranché avant le script ; s'il ne peut pas l'être, le formuler
sans l'affirmer et le signaler à la livraison.

## 3. Inventaire des notions (`work/concepts.json`)

Une entrée par notion enseignée, y compris les règles pratiques, les chiffres, les
analogies, les outils, les consignes de sécurité et les actions décidées :

    {"id": "chute-tension", "title": "Chute de tension inférieure à 5 %",
     "evidence": [{"tc": "00:41:12", "quote": "il faut que ce soit inférieur à 5 %"}],
     "screen": ["k-004118.jpg"], "must_say": ["chute de tension", "5 %"],
     "status": "confirmed", "note": "16 mm² : 2,99 % ; 25 mm² : 1,91 % (écran)"}

`must_say` liste les termes qui doivent être dits ou affichés pour que la notion soit
couverte. Viser l'exhaustivité : un passage de deux minutes contient souvent trois ou
quatre notions. Comparer la liste avec chaque paragraphe des notes Gemini **et** avec la
transcription minute par minute ; ajouter ce que Gemini a manqué.

## 4. Moments d'écran (`work/keyframes/`)

    .venv/bin/python $SK/scripts/keyframes.py sources/reunion.mp4 work/keyframes --crop x,y,w,h

Regarder d'abord une image pleine résolution pour mesurer la zone d'écran partagé
(`--crop`) et exclure les vignettes des participants. Le script découpe la vidéo en
segments d'écran stables, enregistre une image par segment (`k-HHMMSS.jpg`) et des
planches horodatées. Ouvrir toutes les planches. Pour chaque notion, choisir l'instant où
l'écran la montre le mieux (cellule remplie, résultat affiché, courbe complète) ; au
besoin extraire une image plus précise :

    ffmpeg -ss 00:41:18 -i sources/reunion.mp4 -frames:v 1 -vf crop=w:h:x:y work/keyframes/k-004118.jpg

Les coordonnées des encadrés (`hl.box`) se mesurent sur l'image recadrée, en pixels.
Pour les mesurer, superposer une grille tous les 50 px sur chaque capture et la regarder.
Flouter avant usage toute donnée personnelle visible (e-mail, téléphone, adresse d'un
particulier).

Une valeur dite à l'oral mais absente de l'écran partagé (par exemple saisie sur le poste
d'un autre participant) ne s'incruste jamais sur une capture : la montrer en motion design
avec la mention « valeurs saisies hors partage d'écran », et montrer sur la capture ce que
l'écran affichait réellement à ce moment-là.

## 5. Script (`work/script.json`, copié dans `motion/src/`)

- Plan pédagogique : du plus concret au plus technique, un chapitre par grande question
  (« quelle puissance ? », « quel câble ? », « que vérifier sur place ? »). Ouvrir sur
  l'enjeu, finir sur un récapitulatif des règles à retenir et des prochaines étapes.
- Une scène = une idée. Chaque scène porte `concepts` (ids), `narration`, `passage`
  (lettre du passage de voix) et soit `shots` (captures), soit `visual`
  (`chapter`, `checklist`, `figures`, `formula`, `diagram`).
- Alterner capture réelle et motion design : la capture prouve (« voici l'outil, voici le
  résultat ») ; le schéma animé explique (analogie, formule, comparaison). Toute valeur
  affichée dans un schéma vient de `concepts.json`.
- Les animations se déclenchent sur un mot de la voix (`at: "chute"`, `"cinq#2"` pour la
  deuxième occurrence) : l'élément apparaît quand il est nommé, jamais avant.
- Écrire pour l'oreille : phrases courtes, nombres en toutes lettres (« sept virgule
  quatre kilowatts »), sigles épelés une fois (« le TGBT, tableau général basse tension »).
- Diriger la voix (VoiceStudio) : chaque scène peut porter `spoken`, le texte tel qu'il
  doit être dit. Il garde **exactement les mots** de `narration` (les animations et les
  sous-titres en dépendent ; `tts_scenes.py` refuse tout écart) et ne change que la
  ponctuation, pour l'oreille : une énumération devient une suite de phrases courtes, un
  point-virgule devient un point, une virgule marque chaque respiration voulue. Jamais de
  parenthèses ni de crochets. Une forme orale différente (« Renault 4 » → « Renault
  quatre ») va dans `voice.pronounce`, pas dans `spoken`.
- ElevenLabs seulement : passages de 300 à 700 caractères (deux ou trois scènes, champ
  `passage`), balises de ton en anglais rares (`[warmly]`, `[seriously]`), selon le skill
  `voice-intonation`.

Contrôle avant toute voix :

    python3 $SK/scripts/check_coverage.py work/concepts.json work/script.json --keyframes work/keyframes

## 6. Voix off

`script.json` → `voice.provider` choisit le moteur :

### VoiceStudio (par défaut, open source, local, sans quota)

Application VoiceStudio (github.com/debpalash/VoiceStudio) sur le Mac, moteur **VoxCPM2**
(Apache-2.0, français, 48 kHz ; éviter OmniVoice dont les poids sont CC BY-NC). API sur
`http://localhost:3900`. Profil existant : `cc1920f7` « Formatrice Rossini ». Pour une
nouvelle voix, enregistrer un profil (`POST /profiles`, `kind=clone`) à partir de 15 à 20 s
d'une vraie voix humaine, avec l'accord de la personne et la transcription exacte de
l'extrait : une voix créée par description reste plus lisse qu'une voix humaine clonée.

Réglages (`voice` dans `script.json`, voir `template/script.example.json`) :
`num_step` 20, `guidance_scale` 1,7, `seeds` [300, 301, 302], `pronounce` pour les sigles
(TGBT → T-G-B-T, DC → D-C, kVA → kilovoltampères ; les sous-titres gardent la graphie
normale). **Pas d'`instruct` ni de `tempo`** : une consigne de ton fait quitter à VoxCPM2
le clonage fidèle (mélodie aplatie, voix moins ressemblante) et l'étirement temporel abîme
la parole ; les scripts refusent ces deux champs. Le rythme vient de `spoken` et des
respirations ajoutées à l'assemblage.

Une génération **par scène** (jamais un passage redécoupé ensuite : la coupe sur la
transcription créait des trous d'une seconde en pleine phrase et des syllabes répétées),
trois graines par scène, la meilleure prise retenue sur mesures :

    python3 $SK/scripts/tts_scenes.py work/script.json work/voice-scenes --dry-run
    python3 $SK/scripts/tts_scenes.py work/script.json work/voice-scenes
    .venv/bin/python $SK/scripts/voice_scenes.py work/script.json work/voice-scenes motion/public/voice motion/src/audio.json

Compter environ 40 s de calcul par prise de 20 s, soit un peu plus de 2 h pour 15 minutes
de vidéo. `voice_scenes.py` :

- refuse une prise si moins de 93 % des mots sont entendus ou si la fin manque, si une
  pause de 0,35 s tombe hors ponctuation, si l'intonation est sous 2,5 demi-tons, si la
  ressemblance avec la voix du profil (ECAPA) est sous 0,85 ou si des mots sont ajoutés ;
  classe les prises valides (ressemblance, intonation, respirations, fidélité) ;
- allonge les respirations trop courtes **à la ponctuation de `spoken`, repérée par la
  position du mot** (point 0,55 s, deux-points 0,34 s, virgule 0,2 s) en dupliquant le
  silence de la prise ; jamais au milieu d'une expression, jamais en étirant la parole ;
- applique un seul gain à toute la séquence (-16 LUFS), écrit les fichiers par scène et
  `audio.json` ;
- retranscrit chaque fichier final et refuse tout silence de 0,2 s hors ponctuation, un
  texte incomplet ou une intonation plate.

En cas de refus, régénérer la scène citée avec d'autres graines
(`--scenes dc --seeds 303,304,305`), puis relancer `voice_scenes.py`. La ressemblance se
mesure avec un Python qui a torch, librosa et speechbrain : `VOICE_EVAL_PYTHON`, sinon le
Python embarqué de VoiceStudio. Les choix et le journal des respirations restent dans
`work/voice-scenes/report.json` et `work/voice-scenes/_shaped/`. Avec `gapSec` 0,55, l'écart
entre deux scènes est d'environ 0,9 s.

### ElevenLabs (seulement si l'utilisateur le demande)

Le script vérifie le solde de caractères **avant** de synthétiser et s'arrête s'il ne
suffit pas (offre Starter : 40 000 caractères par mois, pas d'achat de caractères
supplémentaires). Voix par passages :

    python3 $SK/scripts/tts_passages.py work/script.json work/voice --dry-run
    python3 $SK/scripts/tts_passages.py work/script.json work/voice
    .venv/bin/python $SK/scripts/check_takes.py work/script.json work/voice

`check_takes.py` refuse une prise sous 2,5 demi-tons d'écart type ou 8 d'amplitude, sous
95 % des mots du script entendus (nombres et unités ignorés, la transcription les écrit en
chiffres) ou avec un silence de plus de 1,2 s. Lire la liste « extra » : un mot inattendu
peut signaler une tournure ambiguë à l'oral, qu'il vaut mieux reformuler. Refaire une prise
avec `--passages L --take c`. Générer d'emblée deux prises par passage (`--take a` puis
`--take b`) fait gagner un aller-retour : la moitié des premières prises échouent de peu.
Renseigner `takes`, raccourcir les silences de plus de 0,6 s (ElevenLabs v3 en laisse de 1 à
1,5 s entre certaines phrases), puis découper :

    .venv/bin/python $AGENT/scripts/cap_pauses.py work/voice work/voice-tight 0.6 '{"A": "b", "B": "a"}'
    python3 $SK/scripts/split_voice.py work/script.json work/voice-tight motion/public/voice motion/src/audio.json

## 7. Motion design (Remotion)

Copier `template/` (`package.json`, `remotion.config.ts`, `tsconfig.json`, `stills.mjs`,
`src/`) dans `motion/` puis `npm install` ; `script.example.json` montre un script complet
(48 scènes, 9 chapitres). Captures recadrées en PNG dans `motion/public/captures/`, logo
dans `motion/public/brand/rossini-re.png`, `script.json` et `audio.json` dans
`motion/src/`. `FormationVideo.tsx` gère cartons de chapitre, captures avec badge
« Réunion · hh:mm:ss » et légende, zooms (`cam`), encadrés légendés (`hl`, étiquettes
toujours gardées dans le cadre), listes, chiffres clés, formules et sous-titres.
`diagrams.tsx` contient les schémas animés (un composant par schéma, déclenché par
`ctx.at("mot")`) ; ceux de la formation IRVE (AC/DC, bidirectionnel, baignoire,
minimum, cos φ, pilotage, chute de tension, filiation) servent d'exemples à adapter.

Captures d'écran animées : enregistrer avec `$AGENT/scripts/cast.mjs` (`$AGENT` : racine du dépôt Agent Montage vidéo) (screencast Chrome horodaté, fenêtre
1920x1080), fabriquer le clip à 60 i/s calé sur la voix avec `$AGENT/scripts/retime_cast.py`, puis le transformer
en séquence d'images avec `$AGENT/scripts/clip_frames.py` et l'afficher image par image avec `<Img>` (jamais
`<OffthreadVideo>`, qui insère des images parasites sur un long rendu).

Relire des images fixes avant le rendu complet, puis rendre par tranches :

    node stills.mjs ../work/still_frames.txt ../work/stills    # une image par scène, demi-résolution
    .venv/bin/python $AGENT/scripts/render_chunks.py --composition Formation --out ../out/<nom>.mp4

`render_chunks.py` rend sur le GPU par tranches avec préroulage, relance une tranche bloquée,
rend l'audio à part, normalise à -16 LUFS et refait seulement les images isolées détectées. Sur le
Mac, ajouter `--browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"` ;
sur l'ordinateur distant Linux, `--gl=swangle`. Jamais `--gl=swiftshader` sur le Mac (trois fois
plus lent, images blanches). Pas de musique sans que
l'utilisateur ait choisi sa source (règle de l'agent).

## 8. Vérifier et livrer

1. Transcrire le rendu final par tranches de 60 s (un fichier long dégrade la
   reconnaissance) et relancer le contrôle : chaque terme `must_say` dit doit s'entendre.

       python3 $SK/scripts/transcribe_mix.py out/<nom>.mp4 work/final.stt.json
       python3 $SK/scripts/check_coverage.py work/concepts.json work/script.json --final-transcript work/final.stt.json

   Un terme signalé absent se vérifie en transcrivant seul l'extrait concerné avant de
   régénérer quoi que ce soit : la reconnaissance écorche parfois un nom propre.
2. `prosody.py` sur le mix final ; skill `video-frame-review` sur le MP4 (sauts, planches,
   demandes).
3. Livrer avec : durée, chapitres, tableau notion → instant de la vidéo → instant de la
   réunion, corrections apportées aux notes Gemini, points restés incertains.

