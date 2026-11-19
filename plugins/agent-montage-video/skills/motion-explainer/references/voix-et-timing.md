# Voix réelle et données d'animation

## Préconditions

Lire les scripts `tts_scenes.py` et `voice_scenes.py` du skill
`meet-video-pedagogique` avant leur première utilisation. Dans le `script.json`
du projet, `voice.endpoint` doit désigner une API VoiceStudio joignable et
`voice.profile` un profil réellement disponible via `GET /profiles`. Ne pas
supposer que `localhost:3900` sur Linux désigne le Mac ou qu'un profil d'exemple
existe. Si le service manque, donner l'URL à connecter et le profil manquant ;
ne pas passer à une autre voix. L'installation Linux générique n'installe pas
ce service. Vérifier aussi les imports requis par `voice_scenes.py` avec le
Python du dépôt avant les générations.

Définir `AGENT` comme la racine absolue du dépôt et `MEET` comme le chemin du
skill. Employer `"$AGENT/.venv/bin/python"` même depuis le dossier `motion/`.
Générer une scène par prise, trois prises par scène, puis choisir et aligner
avec les scripts existants conformément à l'AGENTS.md.

## Contrat réellement produit

`voice_scenes.py` produit `audio.json` de la forme suivante (structure, sans
données fictives) : l'objet `voice` est indexé par identifiant de scène ; chaque
entrée possède `file`, `durationSec`, `words` et `cues`. Un mot contient `t`
(texte), `s` (début) et `e` (fin), en secondes locales au fichier audio. Une cue
contient `text`, `start` et `end`. Le WAV de `file` doit exister dans le dossier
d'actifs effectivement servi au rendu.

Cette sortie n'est pas le `voTiming.ts` du gabarit amont. Ne pas lancer son film
en espérant un raccord automatique. Adapter le projet retenu explicitement :

1. Fixer la correspondance des identifiants entre script, audio et scènes. Refuser
   toute scène narrée absente ou tout fichier audio manquant.
2. Calculer les débuts des scènes à partir des durées réelles, des pauses voulues
   et des recouvrements de transition. Conserver ce planning en secondes dans
   `src/timeline.json` et les vrais mots dans `src/timing.json`. Ne pas ajouter
   deux fois une pause déjà présente dans les WAV.
3. Convertir un mot local vers le film par `sceneStart + s`, puis vers une image
   avec `round(time * fps)`. Ne pas répartir les mots uniformément sur la durée
   lorsqu'un horodatage réel existe.
4. Sous HyperFrames, placer chaque `<audio id>` au début réel de sa scène et
   déclencher la timeline GSAP avec ces mêmes secondes. Garder les chemins
   d'actifs locaux, la durée racine et les durées de sous-compositions cohérents.
5. Si le gabarit Remotion amont est retenu, adapter ses lecteurs ou générer
   `voTiming.ts` et `lines.ts` depuis ces données : `src` reprend `file`,
   `clipAt` est l'offset du WAV dans le chapitre, chaque ligne correspond à une
   cue et ses débuts de mots sont issus de `words`. Les valeurs de `VoLine`
   sont locales au chapitre, pas au film. Conserver le texte français exact,
   vérifier la correspondance des mots et inclure l'offset une seule fois.

Le raccord est du code propre au projet et au moteur choisi. Le gabarit amont
est une ressource optionnelle ; son installation ne signifie pas que ce code a
déjà été écrit ni testé. Avant le rendu complet, vérifier les fichiers, les
bornes des mots, le texte, les pauses et un extrait avec la vraie voix. En cas
d'écart, arrêter et corriger les données plutôt que repasser au timing estimé.
