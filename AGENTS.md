# Repository Guidelines

## Project Structure & Module Organization

This repository is a mostly static GitHub Pages site with one small API-backed feature.

- `index.html`, `privacy_policy/index.html`, and `terms/index.html` are top-level static pages.
- `lunch-vote/index.html` contains the lunch voting UI and client-side JavaScript.
- `lunch-vote-api/server.py` is the stdlib Python/SQLite API used by the lunch vote page.
- `assets/` holds shared site assets; `assets/lunch-vote/` holds venue thumbnails and placeholders.
- `docs/` contains feature briefs and implementation notes.
- `run_local_preview.sh` starts the local API and serves the site through nginx in Docker.

## Build, Test, and Development Commands

- `./run_local_preview.sh` starts the local preview at `http://localhost:8088/lunch-vote/` and proxies `/api/` to the Python API.
- `python3 -m py_compile lunch-vote-api/server.py` performs a fast syntax check for the API.
- `docker build -t lunch-vote-api ./lunch-vote-api` verifies the API container build.
- `docker compose -f docker-compose-example.yaml config` validates the full-site Compose example.

There is no package manager build step for the static pages.

## Coding Style & Naming Conventions

Keep static pages self-contained unless shared assets are clearly reusable. Use two-space indentation for HTML, CSS, and JavaScript blocks in existing pages. Use four-space indentation for Python. Prefer descriptive kebab-case paths for new public pages, for example `new-feature/index.html`, and lowercase hyphenated asset names, for example `assets/lunch-vote/venue-name.webp`.

For API changes, keep to the current stdlib Python approach unless a dependency is justified. Avoid committing generated caches such as new `__pycache__` files.

## Testing Guidelines

No formal automated test suite is configured. For static-only changes, preview the affected page with `./run_local_preview.sh` and check browser rendering at the route being changed. For `lunch-vote` or API-backed changes, verify the real preview path, including `/api/lunch-vote` and `/api/lunch-vote/results`; do not rely only on direct API calls.

Run `python3 -m py_compile lunch-vote-api/server.py` after editing the API.

## Commit & Pull Request Guidelines

Recent commit messages are short, imperative summaries such as `lunch vote` and `Remove unnecessary horizontal rule in index.html`. Keep commits focused and mention the affected feature or page.

Pull requests should include a brief change summary, manual test notes, linked issue or brief when available, and screenshots for visible page changes. Call out any API, Docker, or deployment configuration changes explicitly.

## Agent-Specific Instructions

When using external product, platform, or vendor knowledge, verify against authoritative sources that are current within the last 30 days. Do not rely on pre-December 2025 posts or outdated third-party summaries.
