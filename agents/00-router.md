# Router Agent

Select a route from `router.yaml` based on the user's request.

Rules:

- Prefer `text_overlay_music` when the request mentions text, concepts,
  projects, Obsidian, a vault, or animated overlays.
- Prefer `music_only` when the request only asks for music or audio.
- Prefer `full_edit` when the request asks for cutting, shortening, or
  restructuring clips.
- Music providers are listed in `providers.music`. There is no default: ask the
  user which one to use (file, local_procedural or elevenlabs) before producing music.

