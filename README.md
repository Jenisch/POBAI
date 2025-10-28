# Path of Building Assistant

This repository contains a lightweight Path of Exile build advisor that can
suggest curated Path of Building profiles tailored to your preferred playstyle.

## Features

- Opinionated library of well-rounded league-friendly builds.
- Scoring engine that matches your preferences for damage type, budget, and
  defensive layers.
- CLI for querying recommendations with either direct flags or a JSON config
  file.
- Optional JSON output (now with PoB import codes and pobb.in share links) for
  piping results into other tooling.
- Dual-phase planner that surfaces both a league-start-friendly pick and a
  high-ceiling endgame option.
- One-shot integration that opens recommended builds directly inside Path of
  Building (Path of Exile 1) by uploading to pobb.in and invoking the
  registered `pob://` protocol handler, or by launching the desktop
  executable.

## Getting Started

The project uses standard Python tooling. Install dependencies (only the
standard library is required) and run the CLI using Python 3.9+.

```bash
python -m pob_build_planner.cli --describe "daggers, fast attacker, melee, tanky"
```

The planner will interpret the free-form description and translate common
keywords like "tanky", "fast", or "league starter" into the structured filters
it needs. You can still use explicit flags when you prefer complete control:

```bash
python -m pob_build_planner.cli --damage-type chaos --combat-range ranged \
  --damage-source attack --budget league_start --content-focus mapping bossing
```

Alternatively, specify a configuration file:

```json
{
  "damage_type": "fire",
  "combat_range": "aoe",
  "damage_source": "damage_over_time",
  "budget": "league_start",
  "defense_layers": ["life_regen", "max_res"],
  "content_focus": ["mapping", "bossing"],
  "mobility_priority": true
}
```

Run the CLI with the config:

```bash
python -m pob_build_planner.cli --config my_playstyle.json --top 1
```

For machine-readable output, add `--json` to emit the recommendations as JSON.
Each entry contains the matched tags, PoB import code, and a shareable
`https://pobb.in/<slug>` link. When pobb.in is unavailable the planner falls back
to embedding the import code directly in the URL fragment so you can still open
the build by visiting `https://pobb.in/#code:<import-code>`.

### Conversational prompts

Launching the CLI without any filters now starts with a simple question: "What do
you want to play?". Type the skill gem you have in mind (for example
`Kinetic Blast`) and the planner will automatically switch into skill-focused
matching, returning ready-to-import PoB codes and pobb.in links (or embedded
fallback URLs when pobb.in cannot be reached). This behaviour
is enabled both when running the CLI directly and when using the Windows batch
launcher.

### Quick skill gem lookup

When you already know the active skill you want to play, supply it directly via
`--skill`. The planner will surface builds from the curated library that use the
gem in their main setup and emit ready-to-import PoB codes and pobb.in links (or
embedded fallbacks when necessary):

```bash
python -m pob_build_planner.cli --skill "Cyclone" --open
```

This bypasses the broader preference scoring so you can jump straight from a
single skill idea to a ready-to-import Path of Building profile. When none of
the curated or synced libraries include your requested gem, the planner now
generates a fresh Path of Building configuration on the fly using PoEDB
metadata to choose the ascendancy, support gems, gear direction, and defensive
layers before emitting the import code and pobb.in link (falling back to an
embedded URL fragment if the upload fails). The generated builds
are hydrated with the Path of Building Community sample trees and items so the
client opens to a complete baseline rather than an empty profile.

### Dual-phase planning

When you want a guided path from day one to pinnacle bossing, use the dual-phase
mode to receive a league-starter and an endgame build in one pass:

```bash
python -m pob_build_planner.cli --config my_playstyle.json --dual-phase
```

The league-start recommendation prioritises characters marked as `league_start`
in the curated library. The endgame pick gravitates toward high-budget or
non-league-start profiles so you have a plan for the final upgrades. Combine the
`--json` or `--open` flags to consume the structured payload or launch both
builds immediately.

### Syncing with PoEDB and Path of Building

If you keep a local checkout of the [PoEDB data](https://github.com/poedb) or the
[Path of Building Community fork](https://github.com/PathOfBuildingCommunity/PathOfBuilding),
the planner can merge those sources into its library automatically.

```bash
python -m pob_build_planner.cli --describe "poison bow" \
  --poedb-path /path/to/poedb_export \
  --path-of-building /path/to/PathOfBuilding
```

`--poedb-path` should point at a directory containing the JSON exports from PoEDB
(any `ActiveSkillGem*.json` or `SkillGem*.json` files are detected). `--path-of-building`
expects a git checkout of the community fork; the planner scans the bundled
`spec/TestBuilds` XML files, converts them into its internal format, and enriches each
build with the PoEDB metadata. The additional builds are merged with the curated
library so subsequent invocations share the same expanded catalogue. When no builds
meet the requested filters the planner now retries with a relaxed score threshold so
you still receive a close match instead of an empty result. If your requested skill
is still missing, the CLI will assemble a brand-new build tailored to that gem and
print the PoB import code alongside a pobb.in link.

### Opening builds in Path of Building

Pass `--open` to automatically launch the top recommendation inside Path of
Building after it is printed:

```bash
python -m pob_build_planner.cli --damage-type fire --combat-range aoe --open
```

If you already know the build identifier you would like to inspect, call the
CLI with `--open-build` and skip the recommendation phase entirely:

```bash
python -m pob_build_planner.cli --open-build toxic_rain_pathfinder
```

The CLI now opens builds through the native `poe://build/<code>` protocol so the
Path of Building client imports the profile immediately without relying on
pobb.in. Share links are still generated for convenience and printed in the
terminal output, but launching the client no longer requires an active
connection to pobb.in. If the protocol handler is not registered or you prefer
to hand the desktop executable the exported XML directly, switch the launch mode
to `file` and optionally supply the path to `PathOfBuilding.exe` (or the
installation directory—the planner will look for `Path of Building Community.exe`
automatically):

```bash
python -m pob_build_planner.cli --open --open-mode file \
  --pob-executable "C:/Games/Path of Building/PathOfBuilding.exe"
```

When you provide an installation directory or executable path the planner now
inspects the bundled `TreeData` folder to discover which passive tree versions
are available. Generated and curated builds automatically adopt the detected
version so Path of Building no longer opens them as empty profiles requesting a
download when your client is behind the latest patch. The import codes printed
to the terminal and pobb.in links use the same version to keep everything in
sync.

#### Windows one-click launcher

If double-clicking the CLI shortcut closes immediately, use the bundled
`run_pob_planner.bat` helper:

1. Install [Python 3.9+](https://www.python.org/downloads/windows/) and ensure
   it is added to your `PATH`.
2. Place `PathOfBuilding.exe` in the default location or note the installation
   directory or full path to the executable.
3. Double-click `run_pob_planner.bat` from this repository.
4. When prompted, confirm the Path of Building location (or paste it if you
   installed it elsewhere).
5. Choose whether to open the top recommendation or a specific build id.

The script keeps the console window open after running so you can review any
errors instead of the window closing immediately. It automatically runs the CLI
in `file` launch mode and will fall back to issuing a `poe://build/<code>` import
if Windows blocks the direct executable launch. When that happens the planner
also prints the raw import code and the pobb.in share link so you can paste
either value manually.

## Tests

Execute the test suite with:

```bash
python -m pytest
```
