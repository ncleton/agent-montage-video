---
name: openvid-interface-video
description: Turn a screen recording of an app, website or software interface into a polished product demo with the local openvid editor (tools/openvid) - wallpaper or gradient background, padding, rounded corners, shadows, device mockups, automatic and manual zooms, 3D camera motion, text and image overlays, 16:9 / vertical formats, MP4/WebM/GIF export. Use whenever the video shows an interface, including "vidéo d'interface", "démo de l'app", "screencast", "capture d'écran vidéo", "walkthrough", "tutoriel logiciel", "présenter le site", "mettre la capture dans un mockup", "zoom sur le bouton", or an existing screen recording that needs to look like a product demo. Not for camera footage, the HyperFrames workflow, or scripted motion-design scenes built in Remotion.
---

# Interface videos with openvid

openvid (github.com/CristianOlivera1/openvid) is cloned into tools/openvid by
scripts/openvid.sh on first start. It is a Next.js app that edits and renders entirely
in the browser, so the agent drives it with a browser it controls (the Codex browser
tools, or headless Chromium through Playwright on the remote computer). No account or
API key is needed for the video editor.

## When to route here

- Use openvid when the main material is a recording of a screen: app, website, SaaS,
  dashboard, iPhone screen mirror, Codex/terminal session. It gives the "product demo"
  look quickly: background, frame, shadow, zoom on the action, device mockup.
- Keep Remotion (projects/<p>/motion/) for scripted motion design with animated copy and
  scene transitions; an openvid export can be used there as a source clip.
- Keep the HyperFrames workflow (scripts/run_workflow.py) for camera footage.
- Music follows AGENTS.md: ask the user which source to use before adding any music in
  openvid's Audio panel. Voice-over gaps stay at 0.6–0.9 s as in AGENTS.md.

## Start

1. Start the server in a persistent tty session: `scripts/openvid.sh` (port 3077 by
   default, installs dependencies if node_modules is missing).
2. Open http://localhost:3077/en/editor in the browser. Use `localhost`:
   on 127.0.0.1 the Next dev server refuses its scripts and the page never becomes
   interactive. There is no French locale (en, es, ru, ko only), and /fr/editor falls
   into the Supabase login check and crashes.

## Import

- Existing recording: start `waitForEvent("filechooser")`, click the "Select file"
  button (or the toolbar "Upload"), then `setFiles(<absolute path>)`. MP4, WebM, MOV and
  MKV are accepted. The clip appears on the VIDEO track and openvid usually adds two
  automatic zoom clips on the ZOOM track.
- New recording: the "Record" button uses the browser screen-capture prompt, which needs
  the user's approval and cannot work on the remote computer. Ask the user to send a
  recording, then import the file.

## Edit

Left toolbar panels: Background (wallpapers, gradients, solid color, blur, padding,
rounded corners, shadows), Mockup (device frames), Motion (3D tilt and camera
movement), Zoom (zoom fragments: level, duration, easing, position), Video (speed,
trim), Elements (text, shapes, SVG, images), Audio. The bottom bar has Mask, Crop and
the output format menu (Auto, YouTube 16:9, vertical formats...). Timeline zoom
fragments can be dragged and resized.

House style for demos: one calm background (desktop wallpaper or soft gradient),
padding around 8–12, rounded corners and a soft shadow, zooms only on the action the
viewer must see (click, typed text, result), 1.3–1.6x, 2–3 s, smooth easing. Check every
zoom by scrubbing the playhead and taking screenshots before exporting.

## Export

1. Click "Export", then one of the quality buttons: "Export as 1080P 1920 × 1080"
   (default for the web), "Export as 4K 3840 × 2160", "Export as 2K 2560 × 1440",
   "Export as 720P 1280 × 720" (quick review), "Export as 480P 854 × 480" or
   "Export as GIF 1280 × 720".
2. Wait for the "Export completed!" dialog by polling the page every few seconds
   (single Playwright waits time out after about 5 s). Rendering runs roughly at 2x the
   clip duration at 720p; plan longer for 1080p/4K.
3. Save the exported file into the project right away, as
   projects/<p>/work/openvid/<name>.mp4. In the Codex in-app browser openvid wrote it
   to ~/Documents/openvid-<width>x<height>.mp4 without a download event; with Playwright,
   wait for the download event and save it. If neither happens, look for
   ~/Documents/openvid-*.mp4 and move it. The next export of the same size overwrites it.
4. Verify with ffprobe (codec, size, duration) and look at a few frames before using it.

openvid keeps its project state in the browser (IndexedDB), not in a file. Write the
settings you chose (background, padding, zoom times, format) in
projects/<p>/work/openvid_settings.md so the video can be rebuilt.

## Maintenance and limits

- Update: stop the server, then in tools/openvid run `git checkout -- claude.md`
  (Next regenerates it at every start), `git pull` and
  `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install`.
- tools/openvid/.env.local only sets the local site URL and disables telemetry. Online
  background search (Unsplash, Pexels, Pixabay) needs API keys that are not configured;
  use the bundled wallpapers or upload an image instead. Do not add keys to the repo.
- License: PolyForm Noncommercial 1.0.0. Before using an openvid export in a paid or
  commercial deliverable, tell Nicolas so he can decide (or get a license from the author).
