# Style « pixel-rpg »

Le style par défaut des vidéos d'Oscar, l'agent vidéo de Rossini Energy : un jeu vidéo rétro en pixel art, vu du
dessus, comme un RPG des années 1990. Il a été construit pour les films « agents IA » et « process HubSpot »
(projets agents-ia et hubspot-process) et se réutilise tel quel. Il est **interchangeable** : un bon de commande
choisit son style (brief.style), et un autre dossier de styles/ se crée sur le même modèle.

Ce style s'inspire de l'esprit des RPG rétro, sans aucun personnage, décor, logo ni son tiré d'un jeu existant :
ses dessins sont originaux (portraits et bulles générés par lib/gen_pixel_portraits.py) ou sous licence libre
(Pixel Agents, MIT ; personnages MetroCity, CC0), avec leurs licences dans assets/licenses et assets/THIRD_PARTY_NOTICES.md.

## Ce qui le compose

- **Décor** : le bureau de Rossini Energy vu du dessus (béton, ferme bois, îlot, établi), puis un zoom dans un grand
  écran façon console où se joue le contenu (écran intérieur 1280 × 720 posé à (320, 168) sur 1920 × 1080).
- **Personnage** : un seul humain, la personne qui regarde (« VOUS »), en portrait pixel aux expressions neutre,
  perplexe, compris, content, fatigue, agacé, cligne ; des bulles question, exclamation, points, colère, note, cœur.
  Aucun agent n'est dessiné en pixel art : un agent nommé apparaît avec son avatar en feutrine (règle de l'ERP).
- **Couleurs** (lib/scene_common.py, COLORS) : fond #0A1411, panneau #11201B, ivoire #EEF4F0, gris #9CB0A6,
  menthe #5FF2A8, or #F5C56B, vert #2FBF83, orange #F5B97A, rouge #FF8A7A. Grille menthe à 3,5 % sur le fond.
- **Texte** : Montserrat 600 ; chaque scène a un titre, un chapitre et une étiquette (TUTORIEL, COMPRENDRE,
  PROBLÈME, SOLUTION, EN PRATIQUE, À RETENIR).
- **Rendu** : sprites en image-rendering: pixelated, jamais lissés ; composition dessinée en 1920 × 1080, rendue en
  4K à l'échelle 2 (AGENTS.md, « toujours en 4K »).
- **Mouvement** : toute animation part d'un mot réellement prononcé par la voix (calage mot à mot de timing.json).

## Utiliser le style

1. Copier assets/ dans motion/assets/pixel/ du projet (les compositions HyperFrames y lisent assets/pixel/<fichier>).
2. Importer lib/scene_common.py (primitives : label, path, paper, node, box, reveal) et lib/pixel_frame.py (décor :
   frame_background, bezel, facecam, office, zoom_in_js, zoom_out_js, wrap_scene) depuis les scripts de production du
   projet, comme projects/hubspot-process/work/production/scenes_hubspot.py.
3. Nouveaux portraits ou bulles : lib/gen_pixel_portraits.py (Pillow), sortie dans assets/generated/.
4. Vérifier à la fin, comme pour toute vidéo, avec le skill video-frame-review.

## Créer un autre style

Un dossier styles/<identifiant>/ avec ce README (ce qui compose le style, ses couleurs, ses règles de texte et de
mouvement), ses assets et leurs licences, et ses primitives. L'identifiant est celui que le bon de commande donne
dans brief.style ; Oscar le prend par défaut dans ses consignes du registre.
