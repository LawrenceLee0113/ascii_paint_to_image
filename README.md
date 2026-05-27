# ASCII Paint To Image

Standalone terminal drawing experiment that converts the current ASCII canvas into a pure-text prompt, backs up that prompt, and sends it to `auth2api` image generation.

## Requirements

- Python 3.9+
- A terminal with mouse reporting support
- Node.js and `npm`
- A local `auth2api` checkout if you want real image generation

By default, the app expects `auth2api` at:

```text
/Users/lawrencelee0113/workspace/auth2api
```

Use `--auth2api-root` if your checkout is somewhere else.

## Install

You can run directly from this folder:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image
```

Or install the package in editable mode to use the console script:

```bash
python3 -m pip install -e .
ascii-paint-to-image
```

This also installs a prompt-only host command:

```bash
ai-image "a luminous terminal-born ink landscape"
ai-image --prompt-file prompt.txt
printf "a quiet mountain at sunrise" | ai-image
```

## Run

From this folder:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image
```

Draw with the mouse, then generate with either path:

- `g`: analysis prompt path. The app summarizes composition, density, strokes, and colors before image generation.
- `i`: simple ASCII prompt path. The app sends the ASCII sketch with only minimal instructions and no analysis layer.

The app writes each run into `runs/<timestamp>/`:

- `ascii.txt`: trimmed ASCII snapshot
- `analysis.json`: density, region, stroke, and color analysis
- `prompt.txt`: the exact pure-text prompt sent to image generation
- generated PNG from `auth2api`

## Dry Run

Use dry-run while tuning prompts without calling `auth2api`. Demo mode creates a sample drawing and exits:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image --demo --dry-run
```

Compare the simple ASCII prompt path without calling `auth2api`:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image --demo --dry-run --prompt-mode simple
```

You can also use dry-run in the interactive UI. It will still write `runs/<timestamp>/ascii.txt`, `analysis.json`, and `prompt.txt`, but it will skip image generation:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image --dry-run
```

## Auth2api

The default image command is equivalent to:

```bash
cd /Users/lawrencelee0113/workspace/auth2api
npm run image -- --out /path/to/run "<generated prompt>"
```

Change the auth2api location with `--auth2api-root`. If `npm` is not on the normal `PATH`, pass an explicit binary with `--npm-bin`.

For direct prompt-to-image use without the ASCII drawing UI, use `ai-image`. It writes a run backup and then calls the same `auth2api` image script:

```bash
ai-image --runs-dir runs "a clean product render on white background"
ai-image --dry-run "test prompt without calling auth2api"
```

## Options

Run `--help` to see the current CLI surface:

```bash
PYTHONPATH=src python3 -m ascii_paint_to_image --help
```

Common options:

- `--runs-dir`: output directory for saved runs. Defaults to `runs`.
- `--auth2api-root`: local `auth2api` checkout. Defaults to `/Users/lawrencelee0113/workspace/auth2api`.
- `--npm-bin`: npm executable path. Defaults to the first detected `npm`.
- `--demo`: create a sample run without opening the interactive UI.
- `--dry-run`: write backups but skip `auth2api`.
- `--prompt-mode analysis|simple`: choose the prompt style for demo mode. Interactive mode uses `g` for analysis and `i` for simple.
- `--brush-size`: brush radius for mouse painting. Defaults to `3`.
- `--char-resolution`: subpixel resolution per terminal cell. Defaults to `9`.
- `--char-gamma`: density-to-character curve. Defaults to `1.6`.
- `--char-ramp`: ASCII density ramp from light to dark.
- `--sgr-coordinate-mode auto|pixel|cell`: mouse coordinate interpretation. Defaults to `auto`.
- `--pixel-cell-width` and `--pixel-cell-height`: pixel-to-cell conversion values for terminals reporting pixel mouse coordinates.
- `--vx-fast-speed` and `--vx-min-ink`: speed-sensitive ink controls. Faster strokes can lay down lighter ink.

## Controls

- Mouse click / drag: paint ASCII ink
- `0`: use the eraser
- `1`-`8`: choose foreground color
- `z`: undo the previous stroke or clear action
- `y`: redo the last undone action
- `g`: generate with analysis prompt and back up files
- `i`: generate with simple ASCII prompt and back up files
- `c`: clear canvas
- `q`: quit

Color keys map to ANSI foreground colors:

- `1`: black
- `2`: red
- `3`: green
- `4`: blue
- `5`: yellow
- `6`: magenta
- `7`: cyan
- `8`: white

## Output

Each generation creates a unique run directory. If a timestamp already exists, the app appends a numeric suffix.

```text
runs/<timestamp>/
  ascii.txt
  analysis.json
  prompt.txt
  *.png
```

The `runs/` directory is treated as generated output and is ignored by git.

## Testing

Run the unit tests with explicit discovery:

```bash
python3 -m unittest discover -s tests
```

## Troubleshooting

- If no PNG is produced, first run with `--dry-run` and inspect `prompt.txt`.
- If `auth2api` is in a different folder, pass `--auth2api-root /path/to/auth2api`.
- If `npm` is not found from the app, pass `--npm-bin /path/to/npm`.
- If mouse drawing lands in the wrong place, try `--sgr-coordinate-mode cell` or `--sgr-coordinate-mode pixel`.
