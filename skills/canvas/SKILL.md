---
name: canvas
description: Opens a minimal canvas for the user to sketch a wireframe, diagram, or visual note, waits until they finish, and returns the image path.
---

# Canvas Skill

Use this skill whenever the user wants to draw, sketch, or illustrate something visually (such as a UI wireframe, architecture diagram, or rough layout).

## Instructions

1. Execute the canvas script and wait for it to complete:
   ```bash
   python3 scripts/server.py
   ```
2. The script will block while the user draws in their browser and will output the absolute file path to a `.png` image once they click **Done & Send to Agent**.
3. Use your image reading / vision tool on the printed file path to inspect the user's drawing and proceed with their request.
