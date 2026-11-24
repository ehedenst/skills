# Skills

A collection of agent skills I've built. Each skill is a folder with a `SKILL.md` (YAML frontmatter + instructions) and any scripts it needs, following the [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) format used by Claude Code and other compatible agents.

## Skills

| Skill | What it does |
|-------|--------------|
| [canvas](skills/canvas) | Opens a browser drawing canvas so you can sketch a wireframe, layout or diagram; the agent waits until you press Done and then reads the PNG. |

## Install

### With `npx skills`

The [`skills`](https://www.npmjs.com/package/skills) CLI detects your agents and installs into the right folders:

```bash
# pick skills interactively
npx skills add ehedenst/skills

# or install one skill globally (user-level)
npx skills add ehedenst/skills --skill canvas -g

# see what's in the repo first
npx skills add ehedenst/skills --list
```

### Manually

Clone the repo and copy (or symlink) the skills you want into your agent's skills folder:

```bash
git clone https://github.com/ehedenst/skills.git
# Claude Code, all projects:
ln -s "$PWD/skills/skills/canvas" ~/.claude/skills/canvas
# or one project only:
ln -s "$PWD/skills/skills/canvas" .claude/skills/canvas
```

Other agents that support skills usually read from a similar folder (for example `~/.agents/skills`); check your agent's docs.

## Requirements

- **canvas:** Python 3 (standard library only) and a web browser on the same machine.

## License

[MIT](LICENSE)
