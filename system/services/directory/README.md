# Course AGNTCY Directory container

The image combines the official `dir-ctl` **v1.8.0** binary with Python and the course's existing `directory-lab.py` helper. The upstream multi-platform image is pinned by digest and supports Linux amd64 and arm64. Docker chooses the platform; learners do not install host binaries or Python.

The course uses AGNTCY's single-process daemon inside this container. It does not deploy the upstream multi-service server/PostgreSQL/OCI topology. This retains the lab's existing SQLite/local-store behaviour and `.course-data/directory` data location. See the [upstream deployment options](https://dir.agntcy.org/latest/dir/dir-deployment-local/) and [CLI container documentation](https://dir.agntcy.org/latest/dir/dir-quickstart/).

Use `scripts/directory.sh` or `scripts\directory.bat` from the repository root. The [learner walkthrough](../../../course/sessions/session-03-eve/DIRECTORY.md) contains the full sequence.

- `up` builds, starts in the background and waits for a real CLI search health check.
- `export`, `push`, `search`, `pull` and `check` execute the helper inside the running container. `cli` exposes the real upstream CLI.
- `stop` retains the container's bind-mounted database and exported records. Global course stop/log commands also include this service.
- The daemon listens on container port 8890; only host loopback is published. The client runs inside the container, while the helper reaches `http://registry:7100` on the course network.
- `.course-data` is mounted writable at `/course-data`; contract templates and the learner workshop are read-only. Provider environment files are neither mounted nor sent in the image build context.
- Shell launchers use the host UID/GID for writable files on Linux. Docker Desktop uses the image's default UID through the batch route.

Optional environment overrides are `COURSE_DIRECTORY_PORT` (host port, default 8890), `COURSE_DIRECTORY_DATA_ROOT` (host data folder), and `DIRECTORY_UID`/`DIRECTORY_GID` for direct Compose use. The integration check uses a separate project, data folder and registry. Stop an existing native daemon before sharing its data with the container.

To repeat the real-container check on macOS/Linux with Docker running:

```bash
python3 tests/check_directory_container.py
```

This check uses synthetic registry metadata and no model calls. It tests publication, retrieval, indexing, contract match/mismatch, failed-output preservation and persistence across stop/start. CI runs it on Linux amd64; native Windows command handling is covered by the cross-platform launcher tests.
