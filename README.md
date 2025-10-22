# Path of Building Assistant

This repository contains a lightweight Path of Exile build advisor that can
suggest curated Path of Building profiles tailored to your preferred playstyle.

## Features

- Opinionated library of well-rounded league-friendly builds.
- Scoring engine that matches your preferences for damage type, budget, and
  defensive layers.
- CLI for querying recommendations with either direct flags or a JSON config
  file.
- Optional JSON output for piping results into other tooling.
- One-shot integration that opens recommended builds directly inside Path of
  Building (Path of Exile 1) using the registered `poe://` protocol or by
  invoking the desktop executable.

## Getting Started

The project uses standard Python tooling. Install dependencies (only the
standard library is required) and run the CLI using Python 3.9+.

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

The CLI uses the `poe://build/<code>` URI handler by default. On systems where
the protocol is not registered or if you prefer the desktop executable directly,
switch the launch mode to `file` and optionally supply the path to
`PathOfBuilding.exe`:

```bash
python -m pob_build_planner.cli --open --open-mode file \
  --pob-executable "C:/Games/Path of Building/PathOfBuilding.exe"
```

#### Windows one-click launcher

If double-clicking the CLI shortcut closes immediately, use the bundled
`run_pob_planner.bat` helper:

1. Install [Python 3.9+](https://www.python.org/downloads/windows/) and ensure
   it is added to your `PATH`.
2. Place `PathOfBuilding.exe` in the default location or note the full path to
   the executable.
3. Double-click `run_pob_planner.bat` from this repository.
4. When prompted, confirm the Path of Building location (or paste it if you
   installed it elsewhere).
5. Choose whether to open the top recommendation or a specific build id.

The script keeps the console window open after running so you can review any
errors instead of the window closing immediately. It automatically falls back to
the `file` launch mode and points Path of Building at a temporary XML profile,
avoiding issues with unregistered `poe://` handlers on Windows.

## Tests

Execute the test suite with:

```bash
python -m pytest
```
