# Third-party notices

## Pixel Agents — MIT

Source: https://github.com/pixel-agents-hq/pixel-agents
Pinned source: b1bafd02896d90d83457266575a1e8e5011ce997 (v1.5.0).
Copyright (c) 2026 Pablo De Lucca.

All source under `vendor/pixel-agents/`, embedded adapted engine code, original furniture/floor/wall PNGs and their manifests are distributed under the upstream repository's MIT license. Retain the complete text in `licenses/Pixel-Agents-MIT.txt`. Upstream does not provide a separate per-furniture license. Its original open-source furniture migration (commit add749a20443e56aa70abba9918fb11d874b1106, PR #117) explicitly replaced privately licensed art with original open-source assets. The full commit message is preserved in `licenses/UPSTREAM-ASSET-MIGRATION.txt` as provenance. This is based on the upstream license declaration, not an independent rights guarantee.

- https://github.com/pixel-agents-hq/pixel-agents/blob/b1bafd02896d90d83457266575a1e8e5011ce997/LICENSE
- https://github.com/pixel-agents-hq/pixel-agents/commit/add749a20443e56aa70abba9918fb11d874b1106

Only current tracked open-source art is bundled; no pre-migration or external Donarg tileset is used.

## MetroCity character base — CC0-1.0

Creator: JIK-A-4.
Source: https://jik-a-4.itch.io/metrocity-free-topdown-character-pack

Upstream credits its six character PNGs as based on MetroCity. The creator's primary page declares “Creative Commons Zero v1.0 Universal” in the Asset license field and explicitly confirms commercial-project use in the creator's comments. Checked 2026-10-25. The complete CC0 text is retained in `licenses/MetroCity-CC0-1.0.txt` (downloaded from https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt). Upstream modifications remain covered by Pixel Agents' MIT notice, so character entries retain both notices (`MIT AND CC0-1.0`). Credit is retained even though CC0 does not require it.

## AO adapter and folder pattern

The integration wrapper, office arrangement, build script and small folder pixel pattern were created for this AO integration. They are distributed under this package's MIT license. No new third-party artwork or fonts were added. Browser text uses the host system font.

## Rossini office scenery

The concrete floor, carpet colours, OSB-style desks and benches, timber braces,
black-framed glass partitions, wooden charging-point display and workshop accents
in `src/rossini-scenery.ts` are original pixel drawings interpreted from office
photographs supplied by Rossini Energy on 26 October 2026. The photographs are not
bundled. These drawings are covered by this package’s MIT license. They are
applied as a static scenery layer and depth-sorted furniture; the pinned original
PNG assets, movement geometry and upstream notices are retained.
