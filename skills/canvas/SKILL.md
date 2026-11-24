---
name: canvas
description: Opens a minimal browser canvas so the user can hand-draw a sketch (UI wireframe, layout, architecture diagram, flowchart, visual note), waits until they press Done, and returns the PNG path for you to view. Use this whenever the user would explain something faster by drawing than by typing — e.g. "let me sketch it", "I'll draw what I mean", "can I show you the layout", "here's roughly how the screen should look", or when you're stuck on an ambiguous visual or spatial description and a quick sketch would settle it.
---

# Canvas

Lets the user draw something and hands you the image. Good for wireframes, rough layouts, box-and-arrow diagrams, and anything spatial that's tedious to describe in words.

## Run it

The script lives next to this file, so call it by absolute path — your working directory is usually the user's project, not the skill folder:

```bash
python3 <skill-dir>/scripts/server.py --prompt "Sketch the settings page layout"
```

- `--prompt` (optional): one short line shown above the canvas so the user knows what you're asking for. Worth setting — without it they see a blank page.
- `--timeout` (optional, seconds, default 600): gives up if the user walks away.

The command blocks while the user draws. Give your shell tool a long enough timeout (≥ the script's `--timeout`), or run it in the background and wait on it; a short default tool timeout will kill it mid-drawing.

## Result

- **Success** (exit 0): stdout is exactly one absolute path to a `.png`. Open it with your image-reading tool and continue the user's task.
- **Cancelled or timed out** (exit 1, nothing on stdout): ask the user whether they want to try again or describe it in words instead. Don't re-launch on your own.
- stderr shows `Canvas open at http://127.0.0.1:<port>`. If the browser didn't open (remote/headless machine), give the user that URL.

## Reading the sketch

Hand-drawn sketches are rough. Treat boxes as regions, arrows as flow or relationships, and scribbled text as labels — confirm anything you can't read rather than guessing. When you turn the sketch into something concrete (code, a diagram, a spec), say briefly how you interpreted it so the user can correct you.
