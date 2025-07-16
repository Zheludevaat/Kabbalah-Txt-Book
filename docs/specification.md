## Book‑Generation Desktop App — Specification (v 1.3)

---

### 1  Overview

A **cross‑platform desktop application** (Windows, macOS, Linux) that turns a structured **Book Brief** into a fully drafted manuscript by orchestrating local, template‑driven OpenAI agents (GPT‑4o / GPT‑4.1 with browsing). Accuracy, coherence, security, and ease of use take precedence over cost.

---

### 2  User Workflow

|  #  |  Actor                   |  Action                                                                                                                                                                                                                                    |  Result                                       |
| --- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------- |
|  1  | **User**                 | Completes the *Book Brief* form (title, genre, outline, characters, style, media, output prefs).                                                                                                                                           | Validated JSON `book_plan`.                   |
|  2  | **PipelineBuilderAgent** | Reads `book_plan`, clones agent templates, injects parameters, writes `pipeline.yaml`, DAG, and prompt files into local **/pipeline** workspace; hands them to **PipelineReviewAgent**.                                                    | Pipeline files generated & validated.         |
|  3  | **User**                 | Reviews the proposed pipeline, accepts or amends.                                                                                                                                                                                          | Finalized pipeline instantiated.              |
|  4  | **Pipeline**             | Loops section‑by‑section:  a. `ResearchAgent` gathers facts.  b. `InstructionAgent` distills a writing brief.  c. `DraftAgent` writes prose.  d. `ReviewAgent` checks logic, facts, and continuity.  e. Presents change log + suggestions. | Draft section + review report sent to user.   |
|  5  | **User**                 | Accepts / rejects / edits suggestions.                                                                                                                                                                                                     | Feedback returned to pipeline.                |
|  6  | **RewriteAgent**         | Applies accepted fixes, merges into master manuscript.                                                                                                                                                                                     | Clean section committed.                      |
|  7  | **Loop**                 | Repeat Steps 4‑6 for all sections.                                                                                                                                                                                                         | Complete manuscript.                          |
|  8  | **FormatterAgent**       | Generates requested formats, injects metadata (ISBN, keywords, copyright page).                                                                                                                                                            | EPUB, PDF, DOCX, Markdown ready for download. |

---

### 2.1  Automatic Pipeline Setup (Optional)
If **Auto‑Setup** is toggled in Step 1, the **PipelineBuilderAgent** immediately executes:
1. **Schema validation** → error report if blocking issues.
2. **Genre‑preset lookup** → choose default template.
3. **Agent‑selection matrix** → pick agent types & order.
4. **Parameter injection** → fill prompts from `book_plan`.
5. **DAG generation** → build dependency graph.
6. **Dry‑run** → estimate tokens/cost/time; detect cycles.
7. **Token‑budget estimation** → present projected usage/cost and allow the user to set **hard token/cost caps** before proceeding.
8. **Resource allocation** → pre‑warm local GPU/CPU sessions within user‑defined caps.
9. **10‑second soft‑abort** → user can cancel.

Status is streamed to a log console and progress bar. On completion, the app pauses and waits for **explicit user approval** of the pipeline before any drafting begins.

---

### 3  Agent Templates

| Agent                            | Role                                                                                                         | Key Inputs                                                | Key Outputs                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- | -------------------------- |
| `ResearchAgent`                  | Fetch verifiable facts & references.                                                                         | `book_plan`, section outline                              | Research notes + citations |
| `InstructionAgent`               | Produce concise writing brief per section.                                                                   | `book_plan`, research notes, prior approved text          | Section brief              |
| `DraftAgent`                     | Write prose for the section.                                                                                 | Section brief, prior approved text                        | Raw draft text             |
| `ReviewAgent`                    | Check factual accuracy, continuity, style.                                                                   | Draft, `book_plan`, prior text                            | Issue list + fixes         |
| `RewriteAgent`                   | Apply fixes, merge, maintain style.                                                                          | Draft, fixes, manuscript so far                           | Clean section              |
| `FormatterAgent`                 | Layout, metadata, multi‑format export.                                                                       | Manuscript, output prefs                                  | EPUB, PDF, DOCX            |
| `CoordinatorAgent`               | Track state, versioning, retries.                                                                            | Artifacts, pipeline state                                 | Updated status             |
| `PipelineBuilderAgent`           | Build tailored pipeline from templates.                                                                      | `book_plan`                                               | `/pipeline` workspace      |
| `PipelineReviewAgent`            | Validate & auto‑correct pipeline files.                                                                      | `/pipeline` workspace                                     | Validation report          |

All templates live in `/templates`; cloned instances are written to `/pipeline/<agent‑name>/prompt.txt` and referenced in `pipeline.yaml`.

---

### 4  Data Contracts

```jsonc
// book_plan.json
{
  "metadata": {
    "title": "string",
    "genre": "enum",
    "target_audience": "string",
    "desired_length_words": 80000,
    "language": "en-US",
    "copyright_holder": "string"
  },
  "outline": [ /* chapter objects */ ],
  "characters": [ /* bios */ ],
  "style_guidelines": "string",
  "media_assets": [ /* optional images */ ],
  "research_links": ["url"],
  "output_preferences": {
    "file_formats": ["docx", "pdf", "epub"],
    "chapter_size_words": 4000,
    "token_budget_hard_cap": 200000
  }
}
```

Artifacts are stored in `/workspace` with versioned filenames; diffs are kept in a lightweight SQLite DB.

---

### 5  Quality‑Control Logic

```pseudo
for section in outline:
    notes = ResearchAgent.run(section)
    brief = InstructionAgent.create(section, notes)
    draft = DraftAgent.write(section, brief)
    issues = ReviewAgent.check(draft)
    while issues:
        feedback = UI.prompt_user(issues)
        draft = RewriteAgent.apply(draft, feedback)
        issues = ReviewAgent.check(draft)
    Manuscript.append(draft)

# Plagiarism check on the growing manuscript
similarity = PlagiarismScanAgent.run(Manuscript)
while similarity > THRESHOLD:
    collisions = PlagiarismScanAgent.report(similarity)
    feedback = UI.prompt_user(collisions)
    Manuscript = RewriteAgent.apply(Manuscript, feedback)
    similarity = PlagiarismScanAgent.run(Manuscript)

FormatterAgent.export(Manuscript)
```

---

### 6  Desktop UI Requirements

* **Modern, polished design** using Tailwind + ShadCN components (rounded corners, subtle shadows, fluid motion with Framer‑motion).
* Stepper wizard for Book Brief with autosave, inline examples, and dynamic validation.
* **Pipeline viewer**: collapsible tree, YAML/JSON editor, drag‑and‑drop reorder.
* **Output Control Panel**: choose file formats, languages, narration options, cover templates, and token caps with live cost estimates.
* **Preview panes**:

  * Manuscript diff viewer with rich text.
  * Cover design carousel with zoom.
  * Localization switcher (side‑by‑side original vs translation).
  * Audio waveform player for narration.
* Live console (stdout/stderr) & progress bar for each agent.
* Token‑usage dashboard showing live and cap values.
* **Contextual help**: tooltips, onboarding tour, and searchable help center aimed at layman users.
* Accessibility: keyboard navigation, ARIA labels, WCAG 2.1 AA color contrast.
* Theme toggle (Light/Dark) and customizable accent color.

### 7  Local Technical Stack

| Layer               | Technology                                                          |
| ------------------- | ------------------------------------------------------------------- |
| UI                  | Electron + React + TypeScript (Tailwind)                            |
| Local Orchestration | Python 3.12, Prefect 2 (or custom asyncio runner)                   |
| Storage             | SQLite (metadata) + local filesystem (artifacts)                    |
| OpenAI              | GPT‑4o / GPT‑4.1 via user Pro API key; function calling + streaming |
| Packaging           | Electron‑Forge builder → native installers (MSI, DMG, AppImage)     |
| Auto‑Update         | Electron Updater (optional)                                         |
| Logging             | Local log files + optional Sentry desktop SDK                       |

No external servers are required; everything runs on the user’s PC.

---

### 8  Constraints & Assumptions

1. Unlimited budget for token usage (user is Pro tier) **unless a hard cap is set in Auto‑Setup**.
2. All data stays local unless browsing is required; outbound requests are limited to research queries.
3. Internet is optional but recommended for research agents.

---

### 9  Acceptance Criteria

* User can go Book Brief → pipeline → manuscript with no coding.
* Pipeline files (`pipeline.yaml`, prompts) are human‑readable.
* Manuscript passes ReviewAgent with zero open issues **within user‑defined token cap**.
* Desktop app stays responsive (UI thread never blocked > 200 ms).

---

### 10  Local Operational Notes

* **Security**: data stored under `%USERPROFILE%/BookGen` (Windows) or `~/BookGen` (Unix); AES‑256 optional encryption.
* **Performance**: configurable concurrency (CPU threads, GPU VRAM check).
* **Backup**: auto‑zip project folder on each milestone; user chooses location.
* **Support**: built‑in “Report Issue” dialog gathers logs + config.

---

*End of specification v 1.3 — includes token‑budget caps.*
