# Style « pixel-rpg-rossini »

Le style pixel-rpg aux couleurs de la charte Rossini Energy. Nicolas, 24 et 26/11/2026 : « Je veux refaire le
template pokemon pour les vidéos pour que ça colle aux couleurs rossini rouge et noir pour ces vidéos et les
futures » ; « on doit garder l'univers des vidéos strictement je veux juste remplacer la dominante verte » ; « rouge
et noir, pas trop non plus. Ça doit juste rappeler notre charte ».

C'est le même univers que `styles/pixel-rpg` (README de ce style) : bureau de Rossini Energy vu du dessus, console,
portrait « VOUS », bulles, sprites en pixel art, Montserrat, rendu 4K à l'échelle 2, animations calées sur la voix.
Seule la dominante verte change :

| Rôle | pixel-rpg | pixel-rpg-rossini |
|---|---|---|
| Fond | #08110E | #0B0909 (noir chaud) |
| Grille (3,5 %) | #5FF2A8 | #E3342F |
| Sol, bord du sol, rayures | #173B2E, #2B5A47, #10291F | #241B1C, #4A2A2C, #1A1314 |
| Accent (étiquettes, clics, puces) | #5FF2A8 | #E3342F, rouge de la charte |
| Panneaux | #11201B, #1D3A30 | #1C1415, #3A2325 |
| Écran de la console | #41604F | #4A3A3C |
| Texte, gris | #EEF4F0, #9CB0A6 | #F2EEEE, #B0A4A5 |

L'or (#F5C56B) reste pour les mises en avant. Le fauteuil, les écrans des ordinateurs, la bibliothèque et la bulle
« note » passent du vert à un rouge éteint ; les plantes gardent leurs feuilles. Le rouge reste un accent : jamais un
fond rouge plein, jamais plus d'un élément rouge vif par plan en dehors des étiquettes et de l'onde des clics.

Pour le motion design (cartes de données, compteurs, schémas), le style peut s'émanciper du pixel art (vectoriel,
lumière, particules, profondeur) à condition de garder des rappels de l'univers : portrait « VOUS » et bulles,
cadre de console, étiquettes, grille, petits sprites, palette ci-dessus.

Il s'utilise comme pixel-rpg : `brief.style = "pixel-rpg-rossini"`, `python3 scripts/studio_style.py pixel-rpg-rossini
<motion>` pour le kit tuto-interface, `lib/` pour les scènes HyperFrames.

