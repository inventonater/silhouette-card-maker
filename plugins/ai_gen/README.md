# AI Card Generator (`ai_gen`)

Generate custom MTG-style card art with OpenAI's image model, curate the
variations you like, and produce print + cut files — all from a few prompts.

This plugin reproduces the ChatGPT "Pro Extended" workflow ("Turn this into an
MTG card. Give me 8 variations.") using the official **`gpt-image-2`** API, then
hands the approved images to the existing `silhouette-card-maker` layout engine.

The end-to-end flow has three stages:

```
1. generate  ->  candidate images, 8 variations per card
2. curate    ->  you delete the variations you don't want (filesystem)
3. build     ->  print PDF + the cutting template to load in Silhouette Studio
```

## Setup

```bash
pip install -r requirements.txt          # installs the openai SDK
export OPENAI_API_KEY=sk-...              # your OpenAI API key
```

> API billing is separate from your ChatGPT subscription. As a rough guide,
> high-quality images cost ~$0.21 each at 1024px (more at 2K / with thinking),
> so 8 variations of a card is on the order of ~$1.70.

## 1. Write a spec

A spec is a JSON file listing the cards to generate. See
[`game/specs/example.json`](../../game/specs/example.json).

```json
{
  "defaults": { "variations": 8, "size": "1024x1536", "quality": "high", "thinking": "high" },
  "cards": [
    { "id": "ember_drake", "prompt": "Turn this into an MTG card ..." },
    { "id": "tidecaller_mage", "prompt": "...", "variations": 4, "reference": "refs/mage.png" }
  ]
}
```

- **`id`** — unique, used as the folder name (letters, numbers, `-`, `_`).
- **`prompt`** — the text prompt for the card.
- **`reference`** — optional path (relative to the spec file) to a reference
  image, or a list of paths. When present, generation uses image editing so the
  output is conditioned on your reference.
- **`variations` / `size` / `quality` / `thinking`** — optional per-card
  overrides of `defaults`. `thinking` is `off` / `low` / `medium` / `high`.

## 2. Generate candidates

```bash
python plugins/ai_gen/generate.py game/specs/example.json
```

This writes `game/candidates/<id>/<id>-1.png … <id>-N.png`. Re-running skips
cards that already have candidates (use `--overwrite` to regenerate).

Options: `--backend` (default `openai`; a `browser` seam exists but is not yet
implemented), `--out`, `--overwrite`.

## 3. Curate (filesystem)

Open each `game/candidates/<id>/` folder and **delete the variations you don't
want**. Whatever remains is treated as approved. To drop a whole card, delete its
folder (or rename it to start with `_` to keep it around but excluded).

## 4. Build print + cut files

```bash
python plugins/ai_gen/build.py --paper_size tabloid
```

This copies the survivors into `game/front/`, renders `game/output/game.pdf`
(standard card size, **4-corner registration** for the Silhouette Cameo 5 Alpha,
fronts only), and prints the matching `.studio3` cutting template to open in
Silhouette Studio.

Useful options: `--paper_size` (`tabloid` default, also `a3`, `letter`, …),
`--card_size`, `--registration` (default `4`), `--ppi`, `--clean` (clear
`game/front` first), `--output_path`.

## 5. Print & cut

1. Print `game/output/game.pdf` on your Epson ET-8550.
2. Open the named cutting template (e.g. `cutting_templates/tabloid-standard-v5.studio3`)
   in Silhouette Studio.
3. Confirm the printed registration marks align with the template, then cut on
   the Cameo 5 Alpha.

> **Tip:** The Cameo 5 cuts up to ~12 in wide, so `tabloid`/`a3` are the largest
> usable paper sizes. Tabloid/A3 needs the longer 12×24 cutting mat.
