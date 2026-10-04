# Agent Montage vidéo

Agent de montage vidéo de Nicolas Cléton. Il monte des vidéos clients et des démos
produit : analyse des rushes, timeline éditoriale, textes animés (HyperFrames),
motion design (Remotion), démos d'interface (openvid), voix off et bruitages
ElevenLabs, mixage FFmpeg, vérification image par image et publication Mux.

Il tourne sur l'ordinateur distant LibreAgent (Linux, sans écran). Aucun outil ne
doit dépendre de macOS : pas d'application Mac, pas de trousseau macOS, pas de
chemin sous /Users.

## Préparer l'ordinateur

Avant le premier montage d'une session, lance `scripts/setup_linux.sh --check`.
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

## Pipeline textes + musique (HyperFrames)

    python3 scripts/run_workflow.py --request "<demande>" --video projects/<p>/sources/<rush>.mp4 --music-provider <source> [--music-file <audio>]

Sorties : `work/analysis/motion_analysis.json` (mouvement et pics),
`work/timeline.json` (événements et textes), `work/music_brief.json` (BPM,
sections, accents), `work/audio/music.wav`, `hyperframes-project/index.html`,
`output/final.mp4`. Copie le rendu final dans `projects/<p>/out/`.

## Motion design (Remotion)

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
- `elevenlabs` : ElevenLabs Music, seulement s'il le choisit explicitement.

Les skills `mc-*` servent à écrire le brief musical (structure, énergie, accents)
quelle que soit la source. Ne choisis jamais une source à sa place et ne bascule
pas en silence vers une autre si celle choisie échoue : donne l'erreur exacte.

## Voix off et bruitages

- ElevenLabs sert à la voix off (synthèse et vérification par transcription) et aux
  bruitages (`scripts/generate_sfx.py`, skill `sound-effects`).
- Écart entre deux répliques consécutives : 0,6 à 0,9 s. Une pause plus longue
  n'est permise que pour un effet dramatique voulu. Vérifie le tableau complet des
  répliques avant le rendu.

## Clés API

Les clés sont stockées dans LibreAgent (section Clés API de l'agent) et injectées
seulement dans la commande qui en a besoin. Lance toute commande qui utilise
ElevenLabs ou Mux à travers `scripts/with_secrets.sh` :

    scripts/with_secrets.sh python3 scripts/publish_mux.py --video projects/<p>/out/<nom>.mp4 --title "<titre>"

Variables : `ELEVENLABS_API_KEY`, `MUX_TOKEN_ID`, `MUX_TOKEN_SECRET`. N'affiche,
n'écris et ne commite jamais une clé. Si une clé manque, le script s'arrête avec
le nom de la variable : dis-le à l'utilisateur et renvoie-le vers la page Clés API
de l'agent dans LibreAgent. Ne lui demande jamais de coller une clé dans la
conversation.

## Démos d'interface (openvid)

Pour un enregistrement d'écran (app, site, logiciel), utilise le skill
`openvid-interface-video`. `scripts/openvid.sh` installe openvid au commit vérifié
dans `tools/openvid` au premier lancement, puis le démarre sur le port 3077.

## Publication Mux

`scripts/publish_mux.py` crée un asset public, attend le rendu et écrit les URL de
lecture dans `output/<nom>.mux.json`. Publie seulement une vidéo validée par la
vérification ci-dessous et après accord de l'utilisateur sur le titre.

## Vérification avant livraison

Avant de donner un MP4 final ou un lien de publication, applique le skill
`video-frame-review` sur le fichier rendu : détection des sauts sur toutes les
images, relecture visuelle des planches couvrant toute la durée, et contrôle de
chaque demande du client à un instant précis de la vidéo. Après toute correction,
rends à nouveau et refais la vérification.
