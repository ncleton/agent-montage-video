# Choix du moteur pour une formation motion design

Analyse documentaire du 11 novembre 2026. Revérifier les versions, les modalités
d'accès et les licences avant une nouvelle production. Aucun comparatif de
vitesse ou de qualité sur notre machine n'a été exécuté pour cette analyse.

## Ce qu'Opus 5.5 change et ce qui n'est pas établi

Les sources primaires consultées n'établissent aucune recommandation officielle
d'Anthropic demandant d'abandonner Remotion depuis Opus 5.5. Le guide du modèle
porte sur la programmation, la conduite des tâches et les instructions visuelles,
pas sur un classement des moteurs vidéo :
https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5

Claude Motion est une offre officielle distincte, pour des animations courtes
éditables et exportables en MP4, en bêta Team/Enterprise. Ce produit n'est pas une
preuve de remplacement de Remotion dans un pipeline autonome Linux :
https://support.claude.com/en/articles/17454997-get-started-with-claude-motion

HyperFrames figure au catalogue Claude comme plugin HeyGen. Ce référencement
n'est pas une recommandation comparative d'Anthropic :
https://claude.com/marketplace/plugins/hyperframes

## Comparaison pour ce projet

| Route | Intérêt | Point à vérifier avant le film complet |
|---|---|---|
| HTML/SVG + GSAP, export HyperFrames | Dessins, flux, morphing et raccords continus avec une timeline positionnable | Export réel 1080p60, polices locales, audio, séquences longues et reprise par scènes |
| Remotion + SVG, éventuellement GSAP | Montage déterministe par image, synchronisation et reprise ciblée déjà intégrés au dépôt | Compatibilité des versions, conditions de licence, même exigence de direction artistique |
| Motion Canvas | Langage d'animation explicative et repères de narration naturels | Voie officielle de rendu headless moins directe ; intégration supplémentaire |
| Manim Community | Transformations géométriques et démonstrations quantitatives | Cohérence graphique avec documents métier et tutoriel d'interface |

Pour la vidéo « agents, contexte et compétences », la piste prioritaire est
HTML/SVG + GSAP avec HyperFrames : elle correspond aux transformations à raconter.
C'est une décision de réalisation, pas une supériorité visuelle mesurée. Les mêmes
intentions sont réalisables avec Remotion ; un changement de moteur ne remplace
pas une direction artistique précise.

HyperFrames positionne les animations pour chaque image avant capture dans Chrome
headless et encodage avec FFmpeg. Ne pas dépendre d'une lecture temps réel, de
timers ou de ressources chargées pendant le rendu :
https://hyperframes.heygen.com/concepts/determinism
https://hyperframes.heygen.com/guides/gsap-animation
https://hyperframes.heygen.com/guides/rendering

Le morphing est documenté par GSAP :
https://gsap.com/docs/v3/Plugins/MorphSVGPlugin/

Remotion dispose aussi d'une intégration GSAP qui positionne la timeline sur
l'image courante. L'alternative « GSAP ou Remotion » est donc mal posée ; les
versions des paquets Remotion doivent rester identiques :
https://www.remotion.dev/docs/gsap
https://www.remotion.dev/docs/renderer/render-media

Motion Canvas :
https://motion-canvas.io/docs/time-events/
https://motion-canvas.io/docs/rendering/
https://github.com/motion-canvas/motion-canvas/issues/415

Manim :
https://docs.manim.community/en/stable/guides/configuration.html
https://voiceover.manim.community/en/stable/quickstart.html

## Avant de retenir définitivement une route

Faire un export d'une séquence représentative de production, avec les vrais
actifs et la voix du projet : un objet qui se transforme, du texte français,
un raccord conservant l'objet, des déclencheurs sur des mots et une fin stable.
Contrôler des images demandées dans un ordre arbitraire, les mêmes images dans le
MP4, la durée, les 60 i/s, la synchronisation, les polices et les ressources locales.
Mesurer le temps seulement à contenu et qualité identiques si la vitesse devient
un critère. Une capture de navigateur en temps réel ne remplace pas cet export.

Documenter un échec exact et corriger ou revoir le choix explicitement. Ne pas
basculer en silence vers l'ancien pipeline d'overlays ou des sous-titres seuls.
Le script `scripts/run_workflow.py` actuel sert ce pipeline d'overlays : il ne
constitue pas le moteur de ce nouveau mode pédagogique.

Vérifier les licences séparément avant intégration commerciale, notamment
Remotion et GSAP :
https://www.remotion.dev/docs/license/pricing
https://gsap.com/community/standard-license/
https://github.com/heygen-com/hyperframes/blob/main/LICENSE
