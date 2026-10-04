<p align="center">
  <img src="plugins/agent-montage-video/assets/icon.png" alt="Logo Montage vidéo" width="120">
</p>

<h1 align="center">Agent Montage vidéo</h1>

<p align="center">
  Montage vidéo par agent, sur un ordinateur distant LibreAgent : textes animés, motion design, démos d'interface, voix off, mixage, vérification image par image et publication Mux.
</p>

## Ce que fait l'agent

- analyse les rushes et construit une timeline éditoriale ;
- ajoute des textes animés (HyperFrames) ou un motion design complet (Remotion) ;
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

## Organisation

- `AGENTS.md` : mission et règles de l'agent ;
- `plugins/agent-montage-video/skills/` : skills (installation, vérification image par image, openvid, voix et bruitages, écriture musicale) ;
- `scripts/` : pipeline (analyse, timeline, musique, HyperFrames, mixage, vérification, Mux) ;
- `projects/` : un dossier par vidéo, jamais versionné.

## Licence

MIT. Les skills `mc-*` viennent de [jtydhr88/music-composition-skills](https://github.com/jtydhr88/music-composition-skills)
(MIT), `music` et `sound-effects` de [elevenlabs/skills](https://github.com/elevenlabs/skills) (MIT),
`elevenlabs-music-generation` de [agentspace-so/runcomfy-agent-skills](https://github.com/agentspace-so/runcomfy-agent-skills) (MIT).
openvid n'est pas inclus : il est téléchargé au premier usage et reste sous sa propre licence
(PolyForm Noncommercial 1.0.0).
