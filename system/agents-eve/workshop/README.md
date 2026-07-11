# Session 3 EVE workspace

This directory deliberately contains **no agent** in the checked-in course.
The package and TypeScript files are only a pinned runtime shell. Run:

```bash
./scripts/session3-lab-init.sh
```

The real EVE CLI then creates `agent/agent.ts`, `agent/instructions.md`, and
`agent/channels/eve.ts` here. Those generated learner files are gitignored.
