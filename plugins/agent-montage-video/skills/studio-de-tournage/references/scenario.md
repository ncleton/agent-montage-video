# Scénario d'un tournage

`work/scenario.json` décrit la page de départ et les gestes. `scripts/studio_record.mjs` les joue avec une vraie
souris et un vrai clavier (Playwright), en 1920 x 1080 CSS à la densité 2 (film 3840 x 2160, 60 i/s).

    {
      "url": "http://127.0.0.1:4100/?onglet=home",
      "waitFor": { "role": "heading", "name": "Prospects" },
      "theme": "light",
      "headers": {},
      "steps": [
        { "action": "mark", "label": "intro" },
        { "action": "pause", "ms": 1200 },
        { "action": "mark", "label": "filtrer" },
        { "action": "click", "target": { "role": "button", "name": "Filtres" } },
        { "action": "type", "target": { "placeholder": "Rechercher" }, "text": "Lyon" },
        { "action": "press", "key": "Enter" }
      ]
    }

Gestes : `click`, `type` (clique la cible puis tape, `charDelay` 55 ms), `press`, `hover`, `scroll` (`y` en pixels),
`select` (`value`), `wait` (`target` ou `ms`), `pause`, `goto`, `mark` (repère pour la voix), `screenshot`
(`name`). Chaque geste attend `delay` après lui (650 ms par défaut, `defaultDelay`).

Cibles, de la plus solide à la plus fragile : `role` + `name` (rôle d'accessibilité et libellé visible), `label`,
`placeholder`, `testId`, `text`, `selector`. `within` restreint à un conteneur, `nth` choisit parmi plusieurs,
`at: {x, y}` vise un point de la boîte (0 à 1). Préférer le libellé que la voix prononce : le scénario se lit
alors comme le tutoriel.

Options : `theme` (light ou dark), `viewport`, `density`, `settleMs` (attente après l'ouverture),
`cursorStart`, `tailMs`, `hideScrollbars` (vrai par défaut), `locale` et `timezone` (fr-FR, Europe/Paris).
Les images ne sont émises par Chrome que quand l'écran change ; l'assemblage tient la dernière image, la durée du
film est exactement celle du journal.
