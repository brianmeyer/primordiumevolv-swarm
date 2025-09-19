# Repository Guidelines

## Project Structure & Module Organization
- `app/` – Main workspace.
  - `app/scripts/` – Executable dev/CI scripts (bash or node). Make files executable: `chmod +x`.
  - `app/utils/` – Shared helpers/utilities used across scripts or app code.
- Recommended (add as needed): `app/tests/` for test files, `app/assets/` for static assets, `app/config/` for environment/config.

## Build, Test, and Development Commands
- `./app/scripts/dev` – Run the local development workflow (start services, watches, etc.).
- `./app/scripts/test` – Execute the test suite; accepts filters (e.g., `./app/scripts/test path_or_pattern`).
- `./app/scripts/build` – Produce build artifacts (images, bundles, or distributions).
- `./app/scripts/format` – Auto-format codebase; fail CI on diffs.

If a script is missing, add it under `app/scripts/` and keep it portable (POSIX shell when possible).

## Coding Style & Naming Conventions
- Indentation: 2 spaces for config/JSON/YAML; 4 spaces for Python; 2 spaces for JS/TS.
- Filenames and dirs: `snake_case` (e.g., `data_loader.py`, `data_loader/`). Scripts in `app/scripts/`: `snake_case` and no extension when possible.
- Prefer small, composable modules in `app/utils/` with clear, single-purpose functions.
- Use an EditorConfig if available; otherwise match existing style. Run `./app/scripts/format` before committing.

## Testing Guidelines
- Place tests under `app/tests/` mirroring source layout (`tests/utils/test_*.py` or `tests/utils/*.spec.ts`).
- Strive for 80%+ coverage on new/changed code. Cover edge cases and error paths.
- Run tests locally via `./app/scripts/test` and ensure they pass before opening a PR.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- Commits: small, focused, and accompanied by context in the body when non-trivial.
- PRs: include a clear description, linked issues, test evidence (output or coverage), and screenshots for UI changes. Keep PRs scoped and reviewable.

## Security & Configuration Tips
- Never commit secrets. Use `.env.local` and provide a sanitized `.env.example`.
- Validate inputs and handle failures in scripts; prefer `set -euo pipefail` in shell scripts.

## Agent-Specific Instructions
- Respect this structure and conventions; avoid broad refactors.
- Add missing scripts/utilities where needed, with minimal, focused changes.
- When in doubt, propose changes via PR with rationale and impact.
