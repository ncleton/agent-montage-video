# Kit tuto-interface

Gabarit Remotion 4.0.536 du montage d'un tutoriel tourné au studio (skill studio-de-tournage).

    cp -R kits/tuto-interface/template projects/<p>/motion && cd projects/<p>/motion && npm ci || npm install
    cp ../work/rec/raw.mp4 public/raw.mp4
    # props.json : { "video": "raw.mp4", "timeline": <timeline.json>, "camera": { "keyframes": <camera.json keyframes> },
    #               "theme": "light", "audio": "voix.wav", "captions": [{ "startMs", "endMs", "text" }] }
    npx remotion render src/index.ts InterfaceTour ../out/<film>.mp4 --props=props.json --codec=h264 --crf=16

La durée vient du journal (une image du film = une image du journal). `accent` reprend la couleur principale de la
charte de l'Administration ; `padding` règle la marge autour de la fenêtre (0,05 par défaut).

Validation du 21/11/2026, Mac mini de Tony : tournage Playwright 1.65.1 d'un formulaire (frappe, clic, transition),
film 3840 x 2160 à 60 i/s, 580 images et journal de 580 images, un plan de caméra, rendu en 48 s, contrôle image par
image sans image isolée (projects/studio-validation, non versionné).
