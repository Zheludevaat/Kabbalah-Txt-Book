# Kabbalah Txt Book

This repository demonstrates a minimal setup for the Book Generation Desktop App. The full functional requirements are described in [docs/specification.md](docs/specification.md).

The Electron UI exposes every setting needed to run the pipeline so non-technical users can tailor the generation process without editing files manually. Word and token limits, the model selector, and output formats are all tweakable. Each input is paired with a small “ℹ️” icon so you can hover for a short explanation. A stepper wizard guides you through entering the Book Brief, editing the pipeline, and running it. A password field lets you provide your API key on the fly, while a theme toggle offers light or dark mode. All controls include ARIA labels for accessibility and full keyboard navigation.

The pipeline editor offers a drag‑and‑drop viewer with enable/disable checkboxes, a live diff pane, and a token dashboard that visualizes usage during execution. Output formats (DOCX, PDF, EPUB) can be toggled before prebake so the generated book matches your needs.

## Usage

0. Install dependencies separately from running the app. Use the helper scripts provided in the repo:
  ```bash
  ./install_deps.sh       # installs Python and Node packages
  ./run_app.sh            # launches the Electron UI
  ```
  On Windows use `install_deps.bat` and `run_app.bat` instead. The older `setup_and_run.sh` script still combines both steps for convenience.

1. If you prefer manual installation run:
  ```bash
  pip install -U -r requirements.txt
  cd electron-app
  npm install
  ```
2. Install Node.js (includes `npm`) for the Electron desktop app. Packaging
   requires Node 18 or later and the `electron-forge` CLI which is installed
   automatically when running `npm install` inside the `electron-app` folder.
   To build installers for Windows, macOS and Linux you must run the `make`
   command on each target platform.
3. Create a `book_plan.json` describing the outline and preferences or paste it
   into the UI. A complete template is provided at
   `docs/book_plan_template.json`.
4. Set your `OPENAI_API_KEY` in the environment or enter it in the UI so later agents can call the OpenAI API. To avoid saving the key to disk set `SAVE_API_KEY=0`. Set `BROWSING_ENABLED=0` to prevent the ResearchAgent from making HTTP requests.
   Set `BACKUP_DIR` to choose where zipped backups are stored and `BACKUP_PASSWORD` to encrypt them with AES‑256.
   `TOKEN_BUDGET` enforces a hard cap on total tokens during a pipeline run and the runner stops early if exceeded.
5. Run the prebake agent to populate `workspace/prebake`:
   ```bash
   # optional environment overrides used by the UI
   WORDS_PER_CHAPTER=5000 \
   WORDS_PER_PART=2000 \
   MAX_OUTPUT_TOKENS=20000 \
   MODEL=gpt-4o \
   python -m orchestrator.agents.prebake_agent
   ```
   The key will be copied into `workspace/prebake/global/api_key.txt` unless `SAVE_API_KEY=0`.
   If symlinks cannot be created (e.g. on Windows), media files are copied instead.
  Style guidelines and character bios from `book_plan.json` are baked into each
   part prompt so later agents maintain consistency. The prompt templates
   under `templates/` provide thorough instructions, emphasising research
   references, style enforcement and continuity so generated text stays on
   track.
6. Build the pipeline from `pipeline_links.yaml`.
   The builder now fills each prompt template using GPT‑4.1 when an API key is
  provided, storing the reviewed results under `pipeline/` before writing the
  YAML steps. The pipeline runner then executes each step using the
  Research, Instruction, Draft, Review, Rewrite, and Formatter agents.
  ```bash
  python orchestrator/pipeline_builder.py
  python -m orchestrator.agents.pipeline_review_agent
  python -m orchestrator.pipeline_runner  # run the pipeline (uses Prefect if available)
  ```
  # A local SQLite DB in workspace/bookgen.db records step progress.
  # Each run archives the workspace into BACKUP_DIR (or the workspace parent)
  # and encrypts the zip if BACKUP_PASSWORD is set.
  # After each rewrite step a plagiarism scan runs and stores the similarity score.
7. Start the desktop UI after installation:
   ```bash
   ./run_app.sh
   ```
8. The UI contains fields for all settings, the API key, and a Book Plan textarea. Use the buttons to run the Pre‑bake and build steps, then inspect or edit the generated pipeline YAML directly in the interface. After editing press **Save Pipeline** and click **Run Pipeline** to execute the steps while a live log displays progress below. A **Dark** button in the header toggles the theme to improve readability.

9. To build a distributable desktop package first install dependencies inside
   `electron-app/` and then run the `make` script. Electron Forge will bundle
   the app and produce an installer for the platform on which the command is
   executed. Build on Windows for an `.exe`, macOS for a `.dmg`, and Linux for
   an AppImage.
   ```bash
   cd electron-app
   npm install  # installs electron-forge
   npm run make
   ```
   The installers are written to `electron-app/out/`.

10. Run tests with `pytest`.
   ```bash
   pytest -q
   ```
