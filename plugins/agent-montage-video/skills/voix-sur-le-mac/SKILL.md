---
name: voix-sur-le-mac
description: Générer la voix off VoiceStudio (VoxCPM2) d'une vidéo sur le Mac mini de Tony quand Oscar travaille sur un poste sans carte graphique (VPS des agents) - seules les requêtes de voix et de transcription partent au Mac par un tunnel SSH, tout le reste (Codex, studio, rendu, Mux) reste sur le poste. Utiliser dès qu'une voix VoiceStudio est à produire sur le VPS, que tts_scenes.py ou tts_passages.py doit tourner sous Linux, ou que VoiceStudio ne répond pas sur 127.0.0.1:3900.
---

# Voix off sur le Mac mini

Oscar travaille sur le VPS des agents (Linux, sans carte graphique). VoxCPM2 y met plus de 15 minutes pour une
phrase courte, contre environ 30 s sur le Mac mini de Tony (Apple M4 Pro). Règle de Nicolas (22/11/2026) : seule la
voix part au Mac ; Codex, studio de tournage, rendu, vérification et publication Mux restent sur le VPS.

## Comment la voix part au Mac

- Le service systemd `voix-mac-tunnel` du VPS ouvre un tunnel SSH (`macmini-tony`, par Tailscale) :
  `127.0.0.1:3900` du VPS mène au VoiceStudio du Mac (`127.0.0.1:3900` du Mac). Installé par
  `scripts/install_voice_tunnel.sh`.
- Les scripts de voix gardent leur adresse habituelle (`script.json` › `voice.endpoint` = `http://127.0.0.1:3900`) :
  `tts_scenes.py`, `voice_scenes.py` et `tts_passages.py` du skill `meet-video-pedagogique` marchent tels quels.
- Ne passent par le tunnel que le texte de chaque réplique, les réglages de voix et l'audio rendu (synthèse
  `/v1/audio/speech`, transcription `/v1/audio/transcriptions`). Aucun fichier de la commande, aucune source ni
  aucun secret n'est copié sur le Mac.

## Avant la voix

```bash
curl -s -m 5 http://127.0.0.1:3900/health
```

- `{"status":"ok","device":"mps",…}` : c'est le Mac, la voix peut partir.
- Pas de réponse : `systemctl restart voix-mac-tunnel`, attendre 10 s, recommencer. Toujours rien : le Mac est éteint,
  hors Tailscale ou VoiceStudio est fermé. `report fail --error "VoiceStudio du Mac mini injoignable depuis le VPS
  (tunnel voix-mac-tunnel) : allumer le Mac et ouvrir VoiceStudio, puis relancer la commande"`.
- `"device":"cpu"` : un VoiceStudio local répond à la place du Mac. Ne pas s'en servir (trop lent) ; arrêter le
  service local (`systemctl stop voicestudio`) puis relancer le tunnel.
- Le profil vient du VoiceStudio du Mac (`GET /profiles`, « Formatrice Rossini » = `cc1920f7`).

## Pendant la voix

- Le Mac rend aussi ses propres travaux : une génération peut attendre son tour. Une erreur 503 ou un délai dépassé se
  relance une fois après 60 s ; les prises déjà rendues ne sont pas refaites (les scripts sautent les fichiers
  présents).
- Garder les réglages d'AGENTS.md (VoxCPM2, 20 pas, guidage 1,7, trois graines, meilleure prise), et l'avancement par
  `report progress` au moins toutes les 10 minutes.

## Jamais

- Jamais le moteur OmniVoice du VoiceStudio local : sa licence (CC-BY-NC) interdit l'usage commercial.
- Jamais ElevenLabs pour un premier jet en remplacement d'un Mac injoignable : seulement quand le bon le demande
  (`brief.voice` = `elevenlabs`).
- Jamais une voix ou une image fabriquée pour contourner un échec : `report fail` avec la raison exacte.
