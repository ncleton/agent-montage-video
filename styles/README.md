# Styles des vidéos d'Oscar

Un style est un dossier `styles/<identifiant>/`. L'identifiant est celui que le bon de commande donne dans
`brief.style` ; sans choix, le bon prend `pixel-rpg`.

| Style | Pour quoi | Dossier |
|---|---|---|
| pixel-rpg | Style par défaut : RPG rétro en pixel art, portrait « VOUS », bulles | styles/pixel-rpg |
| charte | Sobre, aux couleurs de la charte Rossini Energy, sans personnage | styles/charte |

## Ce que contient un style

- `README.md` : ce qui le compose (décor, personnage, couleurs, texte, mouvement) et ses règles.
- `kit.json` : l'habillage des tutoriels d'interface (kit tuto-interface) : `frame` (`rounded` ou `pixel`),
  couleurs (`background`, `window`, `ink`, `muted`, `accent`, `accent2`, `onAccent`), `grid`, `floor`,
  `bezel` (cadre pixel), `dialog` (sous-titres), `label` et `closingLabel`, `portraits` (images de l'ouverture
  et de la fermeture, avec leurs bulles) et `assets` (dossier de ces images dans le style).
- Ses images, sous licence libre ou générées, avec leurs licences.
- Au besoin, ses primitives pour les films motion design (comme `styles/pixel-rpg/lib`).

## Créer un style

1. Copier `styles/charte` (sans images) ou `styles/pixel-rpg` (avec portraits) sous le nouvel identifiant.
2. Écrire son README, régler ses couleurs et son cadre dans `kit.json`, générer ses images (outil image de Codex,
   skill generer-image-codex) et les placer dans le dossier `assets` nommé par `kit.json`.
3. Vérifier : `python3 scripts/studio_style.py <identifiant> <dossier motion d'un projet>` doit passer, puis une
   image de l'ouverture, du tour et de la fermeture rendue avec `npx remotion still` se relit avant le premier film.

