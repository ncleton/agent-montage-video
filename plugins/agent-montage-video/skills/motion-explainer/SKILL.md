---
name: motion-explainer
description: Produire une vidéo pédagogique ou un tutoriel en motion design à partir d'un texte, d'un sujet ou d'une procédure. Reformuler fidèlement le texte intégral, prouver la couverture des notions et construire des animations explicatives synchronisées à la voix, avec une identité réutilisable. Choisir le moteur selon le film. Pour une réunion enregistrée, utiliser meet-video-pedagogique pour l'analyse de la source.
---

# Pédagogue et réalisateur de motion design

Transformer l'explication en une démonstration visuelle compréhensible par son
public. L'écriture pédagogique et la direction du mouvement précèdent le choix
du moteur. Ce skill ne déclenche ni publication ni génération de musique.

## Texte intégral et fidélité

Quand un texte est fourni, le conserver dans
`projects/<projet>/sources/demande-originale.md`. Le lire en entier. Chaque agent
de rédaction ou de relecture reçoit ce fichier intégral et les précisions de
l'utilisateur, pas seulement un résumé ou un chapitre. Vérifier qu'il peut y
accéder avant de lui confier le travail. Les agents de construction reçoivent
en plus le contexte du film et le passage exact à illustrer.

Reformuler en disant mieux la même chose : phrases orales, grammaire corrigée,
transitions claires, jargon expliqué au moment utile. Garder la progression,
les exemples, les étapes, les noms et la conclusion demandés. Ne pas convertir
une formation longue en capsule courte ni substituer une accroche marketing.
La durée découle de la narration complète, sauf durée imposée par l'utilisateur.
Séparer les consignes de réalisation de la narration à prononcer.

Produire `work/script-reformule.md` et `work/couverture-editoriale.md`. Pour chaque
passage source, la couverture indique son passage dans le script, ce qui sera
montré, les reformulations de fond et les vérifications restantes. Une correction
factuelle nécessaire reste proche de l'intention et s'explique dans ce document ;
ne pas supprimer silencieusement une idée pour éviter de la vérifier.

Vérifier les chiffres, les fonctionnalités et les interfaces dans leurs sources
primaires actuelles. Nommer le modèle et les hypothèses pour les tokens ; un PDF
ou une session logicielle n'a pas de coût universel. Une illustration chiffrée
reste explicitement une illustration. Les informations manquantes restent des
points à résoudre dans le dossier de travail, jamais des chiffres inventés dans
la voix ou l'image. Pour le tutoriel, filmer les étapes réelles et vérifier les
libellés, le compte et les indicateurs visuels sur l'interface actuelle.

## Mettre en scène une compréhension

Définir ce que le public doit comprendre ou savoir faire après chaque séquence.
Ouvrir sur une accroche (une question ou une promesse qui touche le public), puis
raconter : un personnage incarné dans son métier, devant son poste, que l'on suit
sans effort de concentration. Partir d'une situation vécue, d'un objectif et d'une première réussite. Montrer
ensuite la difficulté qui apparaît lorsqu'on recommence, puis introduire la notion
technique comme solution à cette difficulté. Reprendre cette progression
problème → solution dès qu'elle aide : consignes répétées → mission enregistrée,
contexte encombré → compactage, détails omis → procédures durables, trop de
procédures chargées → lecture sélective, fichiers dispersés → organisation du projet.
Une étiquette discrète par plan (Problème, Solution, Comprendre, En pratique) rend
la progression lisible ; ne pas laisser croire qu'un agent supprime les limites
de contexte. Un exemple concret
doit être compris avant d'introduire le jargon. Quand l'utilisateur change le fil
rouge, mettre à jour narration, schémas, données pédagogiques et captures ; ne pas
laisser cohabiter l'ancien et le nouvel exemple sans raison expliquée.
Ne changer l'exemple métier que sur une demande explicite. Un mot isolé qui semble
en introduire un autre (par exemple « inscription » pour « instruction ») se lit
d'abord comme une faute de frappe dans le contexte du film ; en cas de doute,
garder l'exemple établi et poser la question.
Conserver un exemple métier qui progresse d'une scène à l'autre. Faire voir la
cause, l'action puis son résultat. Révéler progressivement et laisser le temps
de comprendre. Un mot technique arrive avec son explication et sa représentation.

Le mouvement doit expliquer : transformer un long prompt en mission persistante,
faire circuler les données, condenser un contexte en résumé, ouvrir les seules
instructions pertinentes d'une compétence. Les objets, leurs états et leurs
transformations restent identifiables entre les plans. Des panneaux qui entrent,
des listes animées et du texte cinétique seuls ne constituent pas le niveau de
motion design attendu pour expliquer un mécanisme.

Écrire `work/storyboard.md` avec, par séquence : passage exact de narration,
objectif d'apprentissage, état initial, action visible, état final, objet conservé
au raccord, mots déclencheurs et source des faits. Distinguer « disponible »,
« instructions chargées » et « action exécutée » pour montrer une compétence.
Un changement de couleur se double d'un libellé ou d'un changement de forme.

Définir une charte dans `work/direction-artistique.md` : typographie, palette,
grammaire de formes, épaisseurs, rythme, courbes de mouvement et transitions.
Pour un film Rossini, partir de Montserrat, rouge #CC1719, encre #1D1D1B et
fond #F0F0F2, en vérifiant les actifs de marque réellement disponibles.
Concevoir les dessins, les métaphores et les raccords propres au film.

Pour un tutoriel de création d'agent dans Codex, lire
[references/tutoriel-codex.md](references/tutoriel-codex.md) : montrer le projet,
les dossiers et le contenu réel d'AGENTS.md et de SKILL.md, avec leurs rôles distincts.

## Choisir et exécuter le moteur

Lire [references/choix-moteur.md](references/choix-moteur.md) au moment du choix.
Comparer ce qui est réellement requis : animation vectorielle, morphing, médias,
voix, contrôle temporel, export headless, corrections et maintenance. Une nouvelle
version de modèle ne prouve pas qu'un moteur doit être abandonné. Distinguer les
recommandations officielles, les démonstrations, les déductions et les mesures.
Ne pas annoncer une supériorité visuelle sans comparaison sur une même scène.

Remotion est une option, pas une obligation de ce mode. HTML/SVG/GSAP avec un
exporteur déterministe constitue une autre route de production. Ne pas confondre
une animation qui joue en temps réel dans le navigateur et un export MP4 fiable.
Avant une première production avec un nouveau moteur, vérifier par un export réel
une séquence représentative : texte accentué, transformation vectorielle,
continuité, audio et sélection exacte d'un instant. Consigner le résultat.

Pour HyperFrames dans ce dépôt, utiliser `scripts/hyperframes.sh` : le moteur,
GSAP et Montserrat sont verrouillés dans `tools/hyperframes/package-lock.json`.
Installer avec `scripts/hyperframes.sh --install`, puis exécuter `check`,
`snapshot` et `render` avec ce lanceur. Copier les scripts et polices dans
`motion/assets/` ; aucune dépendance CDN pendant le rendu. Lire le contrat
technique livré dans
`tools/hyperframes/node_modules/hyperframes/dist/skills/hyperframes/SKILL.md`.
Les règles de voix, de musique et de publication du présent dépôt prévalent sur
ses valeurs par défaut. Le test du 11 novembre 2026 sur le Mac mini de Tony a
exporté 540 images en 1080p60 avec audio, morphing SVG et Montserrat locale ;
ce test ne valide pas un autre ordinateur ni le film complet.

Si Remotion est retenu, les références amont détaillent les formes
(`references/forms.md`), les raccords et composants (`references/remotion-patterns.md`)
et les grilles de relecture (`references/rules.md`). Le gabarit dans
`assets/template/` est un exemple de structure ; ses scènes de démonstration ne
sont pas le contenu du client. Le texte amont est conservé dans
`references/upstream-skill.md` pour traçabilité, pas comme procédure prioritaire.
Les règles d'intégration ci-dessous remplacent ses réglages de production.

## Intégration au pipeline Montage vidéo

- Préparer Linux avec `scripts/setup_linux.sh --check` selon l'AGENTS.md du dépôt.
  Commencer les commandes par `export PATH="$HOME/.local/bin:$PATH"`. Aucun outil
  de production ne dépend d'une application ou d'un chemin macOS.
- Créer le projet sous `projects/<projet>/`, avec `sources/`, `work/`, `motion/`
  et `out/`. Ne pas créer de dépôt Git imbriqué et ne pas versionner les médias.
- Pour une formation horizontale, dessiner en 1920 × 1080 à 60 images/s et rendre
  toujours en 4K (3840 × 2160), règle de l'AGENTS.md, sauf autre format demandé. Garder les temps en secondes et convertir avec le FPS du projet ;
  ne pas reprendre tels quels les nombres d'images d'un exemple amont à 30 i/s.
- La première voix est VoiceStudio/VoxCPM2, générée par l'agent avec les scripts
  `tts_scenes.py` et `voice_scenes.py` du skill `meet-video-pedagogique`, selon
  l'AGENTS.md. Ne pas demander à l'utilisateur de produire une prise ni quelle
  voix utiliser. ElevenLabs intervient seulement après validation comme prévu au dépôt.
- Lire [references/voix-et-timing.md](references/voix-et-timing.md) avant de générer
  ou d'intégrer la voix. Le service et le profil VoiceStudio doivent être joignables ;
  le seul résultat `READY` de l'installation générique ne le garantit pas.
- Synchroniser sur les vrais mots de cette voix, conserver `src/timeline.json`
  et `src/timing.json` comme données de référence. Une estimation est étiquetée
  maquette et n'est pas un livrable. Aucun remplacement silencieux de la voix.
- La musique reste un choix de l'utilisateur. Les recettes de synthèse musicale
  du gabarit ne sont pas une autorisation de produire une bande-son.
- Les captures d'interface utilisent `scripts/cast.mjs` puis
  `scripts/retime_cast.py` pour une interface web dans Chrome. Ce screencast CDP
  ne filme ni Codex natif ni un sélecteur de dossiers système. Pour ceux-ci,
  employer un enregistrement réel fourni ou un moyen de capture vérifié sur la
  machine qui exécute l'application. Si cette source manque, le signaler comme
  asset requis ; ne pas remplacer la démonstration par une fausse interface.
  Dans Remotion, les clips passent par
  `scripts/clip_frames.py` et des `<Img>`, jamais `<Video>` ou `<OffthreadVideo>`.
- Relire les images fixes et un passage en mouvement avant le film complet.
  Pour Remotion, définir `AGENT` comme la racine absolue du dépôt, se placer dans
  `projects/<projet>/motion/`, puis utiliser
  `"$AGENT/.venv/bin/python" "$AGENT/scripts/render_chunks.py" --composition Film --out ../out/film.mp4 --gl=swangle`.
  Après une modification du code, de la voix ou des timings, ajouter `--fresh`
  ou employer un nouveau dossier `--work` de version : les tranches existantes
  ne sont pas invalidées automatiquement. Le mix final suit -16 LUFS. Les scripts amont de
  rendu, de voix et de master ne remplacent pas ceux du dépôt.
- Une scène, une police, une prise ou un accès manquant doit arrêter l'opération
  avec la ressource exacte à fournir. Aucun chapitre de remplacement, aucune
  image factice et aucune dégradation en sous-titres seuls.
- Appliquer `video-frame-review` sur le MP4 final : toutes les images contrôlées,
  planches sur toute la durée, zéro image isolée, chaque demande reliée à un
  instant précis. Refaire la vérification après correction. La publication Mux
  suit l'accord sur le titre prévu au dépôt.

## Répartition du travail et compte rendu

Quand le travail parallèle est demandé ou autorisé, distinguer rédaction fidèle,
vérification factuelle, direction du mouvement, construction et relecture avec un
regard neuf. Partager le texte intégral aux rédacteurs et relecteurs. Chaque agent
de construction modifie seulement ses scènes ; l'orchestrateur possède les
fichiers de timing, de charte et d'assemblage. N'employer un modèle nommé que s'il
est réellement disponible et ne pas prétendre avoir testé Opus avec un autre modèle.

Donner l'avancement pendant les travaux longs. Le compte rendu distingue : ce qui
est installé, ce qui a été exporté et vérifié, et ce qui reste à produire.
