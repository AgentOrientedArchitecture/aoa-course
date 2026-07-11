# Session 3 EVE workspace

This directory deliberately contains **no agent** in the checked-in course.
The package, lockfile, and TypeScript config are only a pinned runtime shell.
From the course root run:

```bash
./scripts/session3-up.sh
```

On Windows use `scripts\session3-up.bat`. The script opens an interactive
container shell with EVE on `PATH`. Type `eve init .` yourself. The real EVE CLI
creates `agent/agent.ts`, `agent/instructions.md`, and `agent/channels/eve.ts`
here; edit them on the host, then test with `eve info` and `eve dev` inside the
container. Generated learner files are gitignored.
