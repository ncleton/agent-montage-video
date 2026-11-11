# Router Agent

Select a route from `router.yaml` based on the user's request.

Rules:

- Prefer `text_overlay_music` when the request mentions text, concepts,
  projects, Obsidian, a vault, or animated overlays.
- Use `code_film_style` when the user asks for a film without rushes in a named
  visual style (watercolor, ukiyo-e, blueprint, isometric, dark keynote, 3D glass…),
  asks which film styles exist, or wants a style of their own: read
  `plugins/agent-montage-video/skills/opuscar-styles/SKILL.md`.
- Prefer `music_only` when the request only asks for music or audio.
- Prefer `full_edit` when the request asks for cutting, shortening, or
  restructuring clips.
- Music providers are listed in `providers.music`. There is no default: ask the
  user which one to use (file, local_procedural or elevenlabs) before producing music.

