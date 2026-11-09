---
name: ao-essentiel-motion
description: Monter en motion design le paquet « Vidéo de l'essentiel » d'un appel d'offres préparé par Oscar, le motion designer de Rossini Sales Suite (ZIP « Vidéo de l'essentiel - <dossier> - <date>.zip » avec PROMPT.md, storyboard.json, captures sourcées, portraits et charte). Vérifier le paquet, préparer le projet Remotion, maquette, voix VoiceStudio, rendu par tranches, vérification image par image et publication Mux dont le lien revient dans L'essentiel du dossier. Utiliser dès qu'on donne un tel ZIP, qu'on parle de la vidéo de l'essentiel d'un AO ou du paquet d'Oscar.
---

# Vidéo de l'essentiel d'un appel d'offres

Dans Rossini Sales Suite (vente.rossinienergy.com, rubrique Appels d'offres, écran « L'essentiel » d'un dossier),
Oscar, le motion designer de l'équipe d'agents, prépare le scénario et les captures d'une vidéo courte (1 min 30 à
2 min 30) : ce que veut l'acheteur, comment il note, les dates, les points d'attention, ce que les agents ont produit
et qui, chez Rossini, doit vérifier quoi. Le serveur ne monte pas la vidéo : il dépose un ZIP dans le Google Drive de
l'AO et le propose au téléchargement. Ce skill le monte sur l'ordinateur qui a la puissance (GPU, VoiceStudio).

Trois exigences ne se négocient pas :

1. **Une source pour chaque information.** Chaque capture du paquet est la page réelle d'une pièce du DCE, passage
   cité surligné, ou la page d'un document produit par un agent ; sa source s'affiche sous la page (bandeau
   « Source »). On n'ajoute aucun chiffre, aucune date ni aucun nom absents du storyboard.
2. **Un agent nommé apparaît avec son portrait** (`avatars/agents/`), à côté de son prénom. Une personne de Rossini
   apparaît avec sa photo (`avatars/personnes/`) ou ses initiales.
3. **La charte Rossini** : police Montserrat, rouge #CC1719, encre #1D1D1B, fond #F0F0F2, logo du paquet.

`$SK` désigne ce skill, `$AGENT` la racine du dépôt Agent Montage vidéo, `$MEET` le skill
`meet-video-pedagogique` installé sur l'ordinateur de montage, dont les scripts de voix VoiceStudio sont réutilisés.
S'il manque sur l'ordinateur, s'arrêter à l'étape 3 et le dire : la voix ne se fait pas autrement. Suivre aussi
l'AGENTS.md du dépôt (voix VoiceStudio d'abord, rendu par tranches, pas de musique sans source choisie).

## 1. Vérifier et préparer

    python3 $SK/scripts/paquet.py verifier "<paquet>.zip"
    python3 $SK/scripts/paquet.py preparer "<paquet>.zip" projects/ao-<dossier> --node-modules <motion/node_modules d'un projet Remotion 4.0.536 existant>

`verifier` refuse un paquet incomplet (capture absente, capture sans source, mot déclencheur absent de la voix,
portrait manquant) avec la raison : demander alors de refaire la vidéo depuis L'essentiel du dossier, jamais
compléter à la main. Lire `PROMPT.md` en entier : il décrit chaque scène, ses plans et leurs sources.

`preparer` crée `sources/` (ZIP et paquet déballé), `work/script.json` (voix), `motion/` (gabarit Remotion, captures,
portraits, logo, `src/storyboard.json`). Sans `--node-modules`, lancer `npm install` dans `motion/`.

## 2. Maquette sans voix

    python3 $SK/scripts/paquet.py estimer projects/ao-<dossier>
    python3 $SK/scripts/paquet.py images projects/ao-<dossier>
    cd projects/ao-<dossier>/motion && REMOTION_CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" node stills.mjs ../work/still_frames.txt ../work/stills-maquette

Regarder chaque image : la page est lisible, le zoom tombe sur le passage surligné, le texte à droite ne déborde
pas, les portraits sont là, le tableau « Qui vérifie quoi » tient dans l'écran. Corriger le gabarit
(`motion/src/EssentielVideo.tsx`), jamais le contenu du storyboard. Chaque image de maquette porte « MAQUETTE · voix
estimée » : elle ne se livre pas.

## 3. Voix off VoiceStudio

VoiceStudio en marche sur `http://localhost:3900` (profil `cc1920f7` « Formatrice Rossini »). `work/script.json`
reprend la voix de chaque scène et prononce les sigles des marchés publics (DCE, CCTP, DPGF, kWc…). Une génération
par scène, trois graines, la meilleure prise sur mesures :

    python3 $MEET/scripts/tts_scenes.py work/script.json work/voice-scenes --dry-run
    python3 $MEET/scripts/tts_scenes.py work/script.json work/voice-scenes
    $AGENT/.venv/bin/python $MEET/scripts/voice_scenes.py work/script.json work/voice-scenes motion/public/voice motion/src/audio.json

`voice_scenes.py` remplace l'`audio.json` estimé par la vraie voix (mots horodatés, sous-titres). En cas de refus d'une
scène, la régénérer avec d'autres graines (`--scenes <id> --seeds 303,304,305`). Ne jamais réécrire le texte d'une
scène : il vient du storyboard et porte les mots déclencheurs.

## 4. Relecture, rendu, vérification

    python3 $SK/scripts/paquet.py images projects/ao-<dossier>
    cd motion && node stills.mjs ../work/still_frames.txt ../work/stills
    $AGENT/.venv/bin/python $AGENT/scripts/render_chunks.py --composition Essentiel --out ../out/<nom>.mp4 --browser-executable "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

Un seul rendu complet par version (relire les images fixes avant). Puis le skill `video-frame-review` sur le MP4 :
aucune image isolée, planches sur toute la durée, et chaque demande de `PROMPT.md` contrôlée à un instant précis
(chaque capture visible avec sa source, chaque agent nommé avec son portrait, le tableau des relecteurs complet).

## 5. Livrer

Montrer la vidéo à la personne qui l'a demandée. Après son accord sur le titre, publier sur Mux :

    $AGENT/scripts/with_secrets.sh python3 $AGENT/scripts/publish_mux.py --video out/<nom>.mp4 --title "<titre>"

Donner le lien `https://stream.mux.com/<id>/highest.mp4` et demander de le coller dans la carte « Vidéo de
l'essentiel » du dossier (bouton « Ajouter la vidéo montée ») : l'équipe la regarde depuis L'essentiel. Si le dossier
a changé depuis le paquet (nouvelles pièces, relecteurs), faire refaire le paquet à Oscar plutôt que retoucher la
vidéo.

