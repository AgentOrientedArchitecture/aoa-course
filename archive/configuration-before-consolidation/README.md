# Preserved configuration before consolidation

Snapshot of the working configuration at commit `b6faa4a`, before the 25 October simplification. It preserves the provider examples, eight Compose definitions, launcher implementations and previous setup text. Private `.env` files, keys and runtime data are not included.

The current entry point is the repository-root README. It uses one `.env.example`, one private `.env`, one `system/docker-compose.yml`, and the existing public session commands. Historical scripts here retain their original relative paths; they are reference copies, not launchers to run from this archive.

`tests/check_course_configuration.py` compares the current effective service settings against these preserved overlays for all four sessions and both model routes. Session 4's filesystem service has a separate Compose name and keeps the same tool address through a network alias, so estate evidence mounts remain limited to Session 4.

For a runnable historical checkout, use Git revision `b6faa4a` in a separate folder. Do not overwrite current learner files or configuration to recreate it.
