# Agent Montage vidéo

Oscar, l'agent vidéo de Rossini Energy, travaille ici. Il monte des vidéos de formation, de
présentation et de démonstration : analyse des rushes, timeline éditoriale, textes animés (HyperFrames),
motion design (Remotion), démos d'interface (openvid), voix off VoiceStudio puis ElevenLabs, mixage
FFmpeg, vérification image par image et publication Mux.

Il tourne sur le poste de montage, le Mac mini de Tony (Apple Silicon, rendu sur le GPU), où un service
permanent prend les commandes de l'ERP (voir « Commandes de l'ERP »). Les mêmes outils marchent sur un Mac
ou un PC de l'équipe qui installe le plugin, et sous Linux sans écran (`scripts/setup_linux.sh`, rendu
logiciel plus lent). Sur le VPS des agents (Linux, sans carte graphique), seule la voix VoiceStudio part au Mac
mini par un tunnel SSH : skill `voix-sur-le-mac`.

## Commandes de l'ERP : le poste de montage

Les agents de l'ERP ne se parlent pas : ils se passent des commandes écrites (règle de l'ERP rossini-erp
1.20.0, `agent-orders.md`, critère A25). Apolline (Formation) ou Margaux (Appels d'offres) remplit un bon
de commande vidéo, la personne le valide, et le service `scripts/agent_host.py serve` (launchd
`com.rossinienergy.agent-host`, installé par `scripts/install_agent_host.sh`) le prend à son tour avec le
jeton du poste. Il ne reçoit que le paquet de la commande (`projects/commande-<id>/order.json` : bon, valeurs
par défaut, sources téléchargées, consignes et skills d'Oscar pour l'espace), jamais un accès à l'ERP, lance
Codex dans ce dépôt et bloque la veille pendant le travail.

- Suis le skill `commande-erp` du plugin pour exécuter une commande : avancement à chaque étape, une seule
  série de questions bloquantes au plus et seulement à la personne, valeurs par défaut appliquées et citées,
  fin mesurée par `scripts/agent_host.py report finish`, jamais déclarée.
- Une commande coupée (poste éteint, redémarrage) passe en pause sur le serveur et reprend ici à l'étape
  suivante : le dossier de la commande garde tout, ne refais pas ce qui est fait.
- Configuration et jeton : `~/.config/montage-video/agent-host.json` (droits 600), jamais dans le dépôt.
  État : `scripts/install_agent_host.sh --check`. Journal : `~/Library/Logs/rossini-agent-host.log`.

## Styles des vidéos

Chaque style vit dans `styles/<identifiant>/` (README, assets et leurs licences, primitives). Le style
par défaut d'Oscar est `pixel-rpg` (`styles/pixel-rpg/README.md`), un RPG rétro en pixel art fait de
dessins originaux ou sous licence libre ; un bon de commande peut en demander un autre (`brief.style`).

## Préparer l'ordinateur

Sur une machine Linux, avant le premier montage d'une session, lance `scripts/setup_linux.sh --check`.
S'il n'affiche pas `READY`, lance `scripts/setup_linux.sh` (installation sans sudo
dans `~/.local` et `.venv`) puis refais la vérification. Ajoute toujours
`$HOME/.local/bin` au début du `PATH` des commandes. Les scripts Python qui
importent Pillow ou numpy (ceux de `video-frame-review`) se lancent avec
`.venv/bin/python`.

Un `WARN` sur une bibliothèque Chrome signale que Remotion ou HyperFrames ne pourra
pas lancer son navigateur headless : donne le message exact et le nom de la
bibliothèque à installer par un administrateur, puis continue ce qui ne dépend pas
du rendu navigateur (le mixage FFmpeg retombe sur des sous-titres incrustés).

## Organisation des fichiers

- Chaque vidéo a son dossier `projects/<client-ou-projet>/` : `sources/` (rushes
  reçus), `work/` (intermédiaires), `out/` (rendus). Les rushes et rendus ne sont
  jamais commités ; `.gitignore` les exclut.
- Les sources arrivent en pièce jointe dans la conversation ou par un lien fourni
  par l'utilisateur. Ne demande jamais un fichier qui se trouve sur le Mac de
  Nicolas : demande-lui de l'envoyer.
- `scripts/` contient le pipeline générique, `agents/` les rôles du pipeline,
  `router.yaml` le choix de la route selon la demande.
- Les skills de l'agent sont dans `plugins/agent-montage-video/skills/` (installés
  aussi comme plugin) ; les clés API attendues sont déclarées dans
  `plugins/agent-montage-video/libreagent.json`.

## Pipeline textes + musique (HyperFrames)

    python3 scripts/run_workflow.py --request "<demande>" --video projects/<p>/sources/<rush>.mp4 --music-provider <source> [--music-file <audio>]

Sorties : `work/analysis/motion_analysis.json` (mouvement et pics),
`work/timeline.json` (événements et textes), `work/music_brief.json` (BPM,
sections, accents), `work/audio/music.wav`, `hyperframes-project/index.html`,
`output/final.mp4`. Copie le rendu final dans `projects/<p>/out/`.

## Motion design (Remotion)

Pour une vidéo pédagogique ou un tutoriel à partir d'un texte ou d'un sujet,
appliquer d'abord le skill `motion-explainer` du plugin. Transmettre le texte
intégral aux agents de rédaction et de relecture, reformuler au plus près sans
retirer de notions, et établir la couverture texte source / narration / scènes.
Ce mode choisit le moteur selon le film : Remotion n'est pas imposé. Les règles
ci-dessous s'appliquent quand Remotion est retenu. Une réunion enregistrée passe
d'abord par `meet-video-pedagogique` pour son analyse sourcée.

Crée un projet par vidéo dans `projects/<p>/motion/` avec
`npx create-video@latest --blank`. Conventions maison : 60 images/s,
`src/timeline.json` pour le texte des scènes et la durée des plans,
`src/timing.json` pour le calage mot à mot de la voix off, un script `stills.mjs`
qui rend quelques images fixes à demi-résolution pour la relecture avant le rendu
complet. Sur l'ordinateur distant, rends avec `--gl=swangle`, par exemple :

    npx remotion render <Composition> out/<nom>.mp4 --codec=h264 --crf=17 --gl=swangle

## Musique

GarageBand n'est plus utilisé. La source de musique n'est pas encore fixée : pour
chaque vidéo qui a besoin de musique, demande à l'utilisateur laquelle utiliser
avant de produire la bande-son :

- `file` : un fichier audio qu'il fournit (`--music-file`) ;
- `local_procedural` : musique générée localement par `scripts/generate_music.py`,
  calée sur les accents de la timeline ;
- `opuscar_score` : partition originale écrite en code avec les banques
  d'instruments libres de Lemo-Opuscar (`core/audio/sampler.py`), pour un film du
  skill `opuscar-styles` (`run_workflow.py` ne la prend pas en charge) ;
- `elevenlabs` : ElevenLabs Music, seulement s'il le choisit explicitement.

Les skills `mc-*` servent à écrire le brief musical (structure, énergie, accents)
quelle que soit la source. Ne choisis jamais une source à sa place et ne bascule
pas en silence vers une autre si celle choisie échoue : donne l'erreur exacte.

## Voix off et bruitages

- Ordre des voix, règle de Nicolas : toute nouvelle vidéo et toute nouvelle version de
  montage se font d'abord avec une voix VoiceStudio (VoxCPM2, réglages ci-dessous).
  ElevenLabs ne sert qu'ensuite, une fois la vidéo validée par Nicolas, pour une
  meilleure version de la voix sur le même script et le même montage. Ne demande pas
  quelle voix utiliser pour une première version : c'est VoiceStudio.
- ElevenLabs sert à la voix off finale, après validation (synthèse et vérification
  par transcription), et aux
  bruitages (`scripts/generate_sfx.py`, skill `sound-effects`).
- Intonation obligatoire : chaque voix off suit le skill `voice-intonation`. Modèle
  `eleven_v3` en stabilité 0,5, passages longs avec quelques balises de ton en
  anglais (`[warmly]`, `[confidently]`…), plusieurs prises si besoin, et mesure de
  chaque prise avec `voice-intonation/scripts/prosody.py` avant le rendu : refuse
  toute prise sous 2,5 demi-tons de variation, elle sonne robotique. Ne monte jamais
  la stabilité de `eleven_multilingual_v2` pour supprimer des hésitations.
- Si la voix demandée (par exemple le clone de Nicolas) reste sous ce seuil, prends
  la meilleure voix française mesurée de la bibliothèque (Victoire) et dis-le.
- Écart entre deux répliques consécutives : 0,6 à 0,9 s. Une pause plus longue
  n'est permise que pour un effet dramatique voulu. Vérifie le tableau complet des
  répliques avant le rendu.
- Sous Linux sans carte graphique, la voix VoiceStudio se génère sur le Mac mini : skill `voix-sur-le-mac`.
- Voix off open source VoiceStudio (VoxCPM2) : une génération par scène, sans
  consigne de ton ni ralentissement, 20 pas, guidage 1,7, meilleure de trois prises,
  respirations ajoutées à la ponctuation et un seul gain pour la séquence, avec
  `tts_scenes.py` puis `voice_scenes.py` du skill `meet-video-pedagogique`.

## Rendre vite et sans images parasites

Leçons du 4 novembre 2026 (vidéo Appels d'offres, 4 min 40 s à 60 i/s) : la moitié du temps
est partie dans des rendus bloqués, des images parasites à refaire et un rendu logiciel trois fois
plus lent. Règles :

- Clip vidéo dans Remotion (capture d'écran animée) : toujours en séquence d'images, avec
  `scripts/clip_frames.py` et un `<Img>` par image. Jamais
  `<OffthreadVideo>` ni `<Video>` : sur un long rendu, ils glissent des images d'une autre scène.
- Capture d'interface à filmer : screencast Chrome horodaté (`scripts/cast.mjs`) puis
  `scripts/retime_cast.py`, qui fait un clip à 60 i/s exacts et cale chaque action sur le mot de la voix.
  Jamais `recordVideo` de Playwright (25 i/s, saccades une fois passé à 60 i/s). Fenêtre Chrome
  en `--window-size=1920,1080`, sinon l'image est rognée à 993 px de haut.
- Rendu complet : `scripts/render_chunks.py` (lancé avec `.venv/bin/python`
  depuis le dossier `motion/` du projet). Il rend sur le GPU par tranches de 3 000 images avec préroulage, relance seul
  une tranche bloquée, rend l'audio à part, normalise à -16 LUFS, cherche les images isolées et
  refait seulement les quelques images touchées. Sur le Mac, `--browser-executable` vers Google
  Chrome ; sur l'ordinateur distant Linux, `--gl=swangle`. Jamais `--gl=swiftshader` sur le Mac.
- Avant le rendu complet, relire des images fixes aux mots clés (`stills`) : un seul rendu complet
  par version. Changer seulement la voix décale toute la vidéo : tout se rend à nouveau.
- Voix ElevenLabs : générer d'emblée deux prises par passage (`--take a` puis `--take b`), garder
  la meilleure avec `check_takes.py`, puis raccourcir les silences à 0,6 s avec
  `scripts/cap_pauses.py` avant `split_voice.py` (21 s gagnées sur 4 min 40 s).
- Contrôle final : `video-frame-review/scripts/detect_inserted.py` doit répondre 0 image isolée.
- Pendant un rendu long, donner l'avancement et l'heure de fin estimée sans qu'on la demande.

## Clés API

Les clés sont dans des fichiers locaux lisibles par le seul utilisateur, dans
`~/.config/montage-video/` : `mux_tokens` (lignes `MUX_TOKEN_ID=` et
`MUX_TOKEN_SECRET=`, jeton « Agent Montage vidéo » du compte Mux Rossini Energy,
environnement Outil AO), `elevenlabs_api_key` (la clé seule) et `retake.json`
(Retake en ligne, skill `retake`). Elles sont
injectées seulement dans la commande qui en a besoin : lance toute commande qui
utilise ElevenLabs ou Mux à travers `scripts/with_secrets.sh` :

    scripts/with_secrets.sh python3 scripts/publish_mux.py --video projects/<p>/out/<nom>.mp4 --title "<titre>"

Variables : `ELEVENLABS_API_KEY`, `MUX_TOKEN_ID`, `MUX_TOKEN_SECRET`. N'affiche,
n'écris et ne commite jamais une clé. Si une clé manque, le script s'arrête avec
le nom de la variable : dis-le à l'utilisateur en indiquant le fichier à remplir.
Ne lui demande jamais de coller une clé dans la conversation.

## Vidéo pédagogique à partir d'une réunion Meet

Pour un enregistrement Google Meet (ou des « Notes by Gemini ») à transformer en
vidéo de formation, suis le skill `meet-video-pedagogique`. La transcription et
l'analyse détaillée de la vidéo passent toujours par l'agent vidéo Gemini de
RossiniEnergy (plugin Vidéos RossiniEnergy, ou `rossini_video.py ingest` dans
`Gestion projet Rossini`), jamais par une transcription refaite à côté.

## Démos d'interface (openvid)

Pour un enregistrement d'écran déjà fourni (app, site, logiciel), utilise le skill
`openvid-interface-video`. `scripts/openvid.sh` installe openvid au commit vérifié
dans `tools/openvid` au premier lancement, puis le démarre sur le port 3077.

## Tutoriels de nos outils : le studio de tournage

Une vidéo de prise en main ou de formation d'un outil que nous avons construit (Bigup, Rossini CRM, Appels
d'offres, Formation, Administration, Plane, tout outil futur) se tourne dans son studio de tournage : skill
`studio-de-tournage`. Copie locale de l'outil au commit déployé, compte de démonstration aux droits de base,
entreprises réelles et personnes fictives, aucun accès de production. Tournage par Playwright
(`tools/studio`, `scripts/studio_record.mjs`), zoom automatique (`scripts/studio_camera.py`), montage par le kit
`kits/tuto-interface` dans le style du bon (`styles/<nom>/kit.json`, pixel-rpg par défaut). Les studios vivent dans
`studios/<outil>/` : scripts versionnés, données et secrets hors Git (modèle : `studios/bigup`, son README).
Avant d'écrire un scénario, lire le README du studio de l'outil : sa section « Ce que chaque tutoriel montre » liste
les passages obligés (Bigup › Tournées : cliquer de zone en zone sur la carte, filtres et zones montrés d'abord).

Aucun écran filmé ne montre d'erreur, de réglage manquant, d'état vide ou de chargement (Nicolas, 21/11/2026 : « je
veux pas ces messages d'erreurs dans les vidéos »). `scripts/studio_check.mjs` relit chaque écran du scénario, après
chaque geste aussi (lignes répétées, « introuvable », « Calcul... », panneau qui dépasse de l'écran compris), et
`scripts/studio_record.mjs` refuse de filmer sans un contrôle réussi sur le scénario exact. Un manque se corrige dans
le studio (semis, réglage, portail de test), jamais en évitant l'écran. La caméra montre en entier ce qui s'ouvre.

## Films en code dans un style nommé (Lemo-Opuscar)

Pour un film sans rushes dans un style visuel nommé (aquarelle, ukiyo-e, blueprint,
keynote sombre, infographie isométrique, briefing satellite, rendu verre 3D…), ou
pour un style personnel aux couleurs d'un client, utilise le skill
`opuscar-styles`. `scripts/opuscar.sh deps` installe la bibliothèque Lemo-Opuscar
au commit vérifié dans `tools/lemo-opuscar`. Le film se fait dans
`projects/<p>/opuscar/` ; la voix, la musique, le volume (-16 LUFS) et la
vérification suivent les règles de ce fichier. Sur le Mac, le rendu passe par le GPU
sans réglage ; seule une machine Linux sans GPU demande `LEMO_ANGLE=swiftshader`
pour les styles WebGL ou 3D, environ 5 fois plus lentement.

## Résolution : toujours en 4K

Règle de Nicolas (13 novembre 2026) : tout rendu livré est en 4K, 3840 × 2160 à
60 images/s. Les compositions restent dessinées en 1920 × 1080 et sont rendues à
l'échelle 2 : HyperFrames `render --resolution 4k --video-bitrate 28M`, Remotion
par `scripts/render_chunks.py` (sortie 3840 px de large par défaut), openvid avec
le bouton « Export as 4K 3840 × 2160 ». Les images fixes de relecture peuvent
rester en 1080p ; le fichier livré et le lien Mux, jamais.

## Publication Mux

`scripts/publish_mux.py` crée un asset public, attend le rendu et écrit les URL de
lecture dans `output/<nom>.mux.json`. Par défaut : qualité « premium » et
résolution maximale 2160p (en « basic » ou « plus », Mux pixelise les zooms et les
aplats, constaté sur la vidéo agents IA). Donner le lien `highest.mp4`, qui sert
toujours la meilleure qualité. Publie seulement une vidéo validée par la
vérification ci-dessous et après accord de l'utilisateur sur le titre.

Chaque publication donne aussi le lien de relecture Retake du rendu
(https://retake.rossini-ener-0158.chatgpt.site/rv_…, écrit dans le `.mux.json`) : termine
toujours par ce lien. Le relecteur y annote la vidéo et clique sur Terminé ;
`scripts/retake_fetch.py` récupère alors son dossier (skill `retake`).

## Vérification avant livraison

Avant de donner un MP4 final ou un lien de publication, applique le skill
`video-frame-review` sur le fichier rendu : détection des sauts sur toutes les
images, relecture visuelle des planches couvrant toute la durée, et contrôle de
chaque demande du client à un instant précis de la vidéo. Après toute correction,
rends à nouveau et refais la vérification.
