# Moteur vidéo verrouillé

Installer depuis la racine du dépôt avec `scripts/hyperframes.sh --install`.
Ce lanceur installe les versions exactes du lockfile avec `npm ci`, puis Chrome
headless. Il fonctionne avec Node.js >= 22 sous Linux et macOS.

- HyperFrames 0.9.33 : moteur HTML/SVG, licence Apache-2.0.
- GSAP 3.15.1 : animations et MorphSVG ; voir la licence livrée avec le paquet.
- @fontsource/montserrat 5.3.0 : fichiers locaux, licence SIL OFL livrée avec le paquet.

Copier les licences avec les actifs distribués. Les paquets et leurs binaires ne
sont pas versionnés. Aucun compte HeyGen ni service cloud n'a été utilisé pour
le test de rendu local. Le moteur amont possède ses propres options de télémétrie,
consultables via `scripts/hyperframes.sh telemetry --help`.

Validation effectuée le 11 novembre 2026, Mac mini de Tony :

- `check --json` : réussi ;
- export local H.264/AAC de 9 secondes : 1920 × 1080, 60/1 i/s, 540 images ;
- Montserrat locale, accents français, morphing SVG via MorphSVG ;
- voix VoiceStudio existante du projet `demo-outil-ao-v2`, scène `fin` ;
- décodage intégral sans erreur, zéro saut isolé, zéro image parasite ;
- lecture visuelle des planches couvrant les 9 secondes ;
- rendu en 12,5 secondes, 2 workers, capture screenshot, GPU matériel.

Preuves locales non versionnées : `projects/hyperframes-validation/work/`
(`check.json`, `probe.json`, `render.log`, `stills/`, `review/`).
Fichier : `projects/hyperframes-validation/out/validation.mp4`.
Ce test est technique : il ne constitue pas la formation demandée ni une preuve
de synchronisation mot à mot de ce futur film. La reprise d'un long film en scènes
et le fonctionnement sur LibreAgent Linux restent à vérifier sur leurs rendus réels.
