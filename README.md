<p align="center">
  <img src="plugins/agent-montage-video/assets/icon.png" alt="Logo Montage vidéo" width="120">
</p>

<h1 align="center">Agent Montage vidéo</h1>

<p align="center">
  Montage vidéo par agent, sur un ordinateur distant LibreAgent : textes animés, motion design, démos d'interface, voix off, mixage, vérification image par image et publication Mux.
</p>

## Ce que fait l'agent

- analyse les rushes et construit une timeline éditoriale ;
- ajoute des textes animés ou un motion design complet (HyperFrames, ou Remotion
  selon le film) ;
- transforme un texte complet en formation ou tutoriel motion design, avec le
  mode pédagogue `motion-explainer` : reformulation fidèle, couverture des notions,
  identité visuelle et choix du moteur selon les animations ;
- habille les enregistrements d'écran en démos produit (openvid) ;
- place la voix off et les bruitages ElevenLabs, mixe avec FFmpeg ;
- vérifie chaque rendu image par image avant de le livrer ;
- publie les vidéos validées sur Mux.

La source de la musique est choisie avec vous pour chaque vidéo : un fichier que vous
fournissez, une musique générée localement, ou ElevenLabs Music.

## Installation

**Avec LibreAgent** : ajoutez l'agent depuis le lien
`https://github.com/ncleton/agent-montage-video` (Ajouter un agent), choisissez
l'ordinateur où il travaille, puis renseignez les clés ElevenLabs et Mux dans la
section **Clés API** de l'agent.

**Avec Codex** :

```text
Installe ce plugin puis installe l'agent Montage vidéo sur cette machine : https://github.com/ncleton/agent-montage-video
```

**Avec Claude Code** :

```text
/plugin marketplace add ncleton/agent-montage-video
/plugin install agent-montage-video@agent-montage-video
```

L'agent prépare lui-même l'ordinateur sans droits administrateur
(`scripts/setup_linux.sh` : ffmpeg, Node.js 22, Python avec Pillow et numpy).
Il fonctionne sous Linux et macOS.

### HyperFrames : moteur local

Le moteur et GSAP sont verrouillés dans `tools/hyperframes/package-lock.json`
(Node.js 22 ou plus). Depuis la racine du dépôt :

```bash
export PATH="$HOME/.local/bin:$PATH"
scripts/hyperframes.sh --install
scripts/hyperframes.sh --version
scripts/hyperframes.sh check projects/<projet>/motion --json
scripts/hyperframes.sh snapshot projects/<projet>/motion --at 1,3,5
scripts/hyperframes.sh render projects/<projet>/motion --fps 60 --quality delivery --output projects/<projet>/out/film.mp4
```

`--install` utilise `npm ci`, puis installe le Chrome headless du moteur. Le
lanceur conserve le dossier courant, vérifie les versions et s'arrête si une
dépendance manque. Aucun téléchargement implicite via `npx`. Les fichiers GSAP
et les polices nécessaires sont à copier dans les actifs locaux de chaque film.
Les binaires et les médias restent exclus de Git. La vérification générique
`setup_linux.sh --check` ne valide pas à elle seule ce moteur : faire un export
sur chaque nouvelle machine avant production.

## Organisation

- `scripts/agent_host.py` : le service du poste de montage, qui prend les commandes vidéo des agents de l'ERP
  Rossini (installé par `scripts/install_agent_host.sh`, skill `commande-erp`) ;
- `styles/` : les styles des vidéos, `pixel-rpg` par défaut ;
- `kits/ao-essentiel` : le gabarit de la vidéo de l'essentiel d'un appel d'offres ;

- `AGENTS.md` : mission et règles de l'agent ;
- `plugins/agent-montage-video/skills/` : skills (installation, vérification image par image, openvid, voix et bruitages, écriture musicale, vidéo de l'essentiel d'un appel d'offres à partir du paquet préparé par Rossini Sales Suite) ;
- `scripts/` : pipeline (analyse, timeline, musique, HyperFrames, mixage, vérification, Mux) ;
- `projects/` : un dossier par vidéo, jamais versionné.

## Licence

Le skill `motion-explainer` adapte
[Marwanenoudouar10/motion-explainer](https://github.com/Marwanenoudouar10/motion-explainer)
(MIT) ; sa provenance et ses adaptations sont indiquées dans son `UPSTREAM.md`.

MIT. Les skills `mc-*` viennent de [jtydhr88/music-composition-skills](https://github.com/jtydhr88/music-composition-skills)
(MIT), `music` et `sound-effects` de [elevenlabs/skills](https://github.com/elevenlabs/skills) (MIT),
`elevenlabs-music-generation` de [agentspace-so/runcomfy-agent-skills](https://github.com/agentspace-so/runcomfy-agent-skills) (MIT).
openvid n'est pas inclus : il est téléchargé au premier usage et reste sous sa propre licence
(PolyForm Noncommercial 1.0.0).
