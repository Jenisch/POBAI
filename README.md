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

## Tests

Execute the test suite with:

```bash
python -m pytest
```
