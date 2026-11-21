# Mettre l'interface en valeur

Le spectateur doit toujours savoir où regarder. Le studio filme l'écran entier, net ; le montage choisit le cadre.

## Réalisation

- **Un objectif par vidéo** (« créer un prospect », « préparer sa semaine »), 1 à 3 minutes. Un outil complet = une
  courte vidéo d'ouverture puis une vidéo par tâche, rangées en leçons par Apolline.
- **Ouvrir sur l'écran entier** 1 à 2 s pour situer, puis zoomer sur le geste. Revenir à l'écran entier quand le
  résultat se voit ailleurs (une liste qui se met à jour, une carte).
- **Rien n'est coupé** : le cadre montre en entier l'élément touché et ce qu'il ouvre (fiche, panneau, fenêtre). Le
  tournage enregistre leurs boîtes et la caméra s'y ajuste ; un ensemble de plus des deux tiers de l'écran se
  montre sans zoom. Une fiche qui dépasse du cadre est un défaut, pas un effet.
- **Le zoom arrive avant le clic** (0,9 s, `--lead`) : on voit où va la souris. 1,6x au plus ; un plan qui couvre
  plusieurs zones zoome moins (le calcul le fait). Gestes proches = un seul plan, la caméra glisse sans repasser
  par l'écran entier.
- **Gestes lents et lisibles** : pas de clic sans pause avant ; la frappe à 55 ms par caractère ; une pause de 1 à
  1,5 s sur chaque résultat avant le geste suivant.
- **Données de vitrine choisies** : une entreprise connue de la région, un logo net, un score vert, une carte avec un
  parking dessiné, des recherches terminées. Jamais d'erreur, de réglage manquant, d'état vide ni de chargement à
  l'image (règle 6 du studio) : studio_check.mjs les bloque et studio_record.mjs refuse de filmer sans son accord.
- **Thème clair par défaut**, le sombre si la commande le demande ; jamais de fenêtre, notification ou outil de
  développement à l'image.

## Montage (kit tuto-interface)

- Fenêtre arrondie avec ombre sur le fond de la charte (`theme`, `accent` de l'Administration ; marge 5 %).
- Curseur dessiné d'après le journal, net en 4K, grossi avec le zoom ; onde à la couleur principale à chaque clic.
- Sous-titres dans la fenêtre, une phrase de la voix à la fois, calés sur les repères `mark`.
- Voix VoiceStudio par phrase (skill meet-video-pedagogique, scripts de voix) ; la durée d'une phrase règle les
  pauses du scénario : si la voix est plus longue que le geste, rallonger la pause et retourner, ne pas accélérer
  la voix.
- Pas de musique sans source choisie (AGENTS.md).

## Contrôles avant livraison

`video-frame-review` sur tout le film, puis une planche toutes les 2 s : chaque geste annoncé par la voix est à
l'image au moment où il est dit, aucun texte coupé par un zoom, aucune donnée personnelle réelle, le menu est celui
du rôle filmé.
