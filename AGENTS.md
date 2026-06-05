# AGENTS.md — Agent Operating Instructions & Coding Standards

This file contains operational instructions, coding standards, and repository conventions for future AI agents working on the **LifeEventRadar** codebase. Follow these rules strictly to ensure code quality, maintainability, and architectural consistency.

---

## 1. Development Workflow

When starting any new task, follow this exact step-by-step workflow:

1. **Information Gathering:**
   - Read `PROJECT.md` to understand the business vision and feature scope.
   - Read `ARCHITECTURE.md` to understand system layers, components, and service boundaries.
   - Read `DECISIONS.md` to understand existing design constraints and rationales.
2. **Task Selection:**
   - Review `TASKS.md` to identify the next pending task in the active milestone. Do not work on future milestones until the current one is completed.
3. **Planning:**
   - Create an implementation plan detailing the proposed changes, new files, modified files, and test plan.
   - Present the plan to the user and obtain explicit approval before editing code files.
4. **Execution:**
   - Implement changes in small, logical, and incremental commits or PRs.
   - Adhere strictly to the coding standards below.
5. **Validation:**
   - Run the automated tests (using `pytest` or SQL validations) and ensure they pass.
   - Manually verify console outputs or database contents where automated tests are not available.
6. **Documentation Update:**
   - If a code change alters schema definitions, weights, or configuration, immediately update the corresponding markdown documentation (`DATA_DICTIONARY.md`, `SCORING_METHODOLOGY.md`, etc.).
7. **Progress Tracking:**
   - Mark the completed tasks in `TASKS.md` by changing `[ ]` to `[x]`.

---

## 2. Coding Standards

### Python Development
* **Style Guide:** Adhere strictly to PEP 8.
* **Typing:** Use type hints for all function arguments and return types.
* **Function Design:** Keep functions focused, modular, and single-purpose. Any function exceeding 40 lines of code should be split into sub-functions.
* **Docstrings:** Document every class and public function using Google-style docstrings. Example:
  ```python
  def compute_home_score(features: dict, config: dict) -> float:
      """Calculates the probability score for the Home Purchase event.

      Args:
          features: Pre-aggregated transaction and visit features.
          config: Weight and threshold scoring configurations.

      Returns:
          A score float bounded between 0.0 and 100.0.
      """
  ```
* **Configuration:** Never hardcode weights or scoring thresholds in calculations. All math variables must be read from a configuration file (`scoring/scoring_config.py`).

### SQL Development
* **Keywords:** Always use uppercase for SQL keywords (`SELECT`, `FROM`, `WHERE`, `JOIN`, `WITH`, `OVER`).
* **Identifiers:** Use lowercase snake_case for all table names and column names.
* **Window Functions:** Document what rolling partition a window query calculates to ensure query logic is readable.
* **File Separation:** Keep DDL schemas separate from data queries. All SQL scripts must reside under the `database/` directory.

---

## 3. Testing Requirements

* **Test Framework:** Use `pytest` for all Python unit and integration testing.
* **Scoring Rules:** Every scoring function in `life_event_scorer.py` and `ewma_engine.py` must have associated unit tests verifying:
  - Behavior when signal aggregates are exactly 0.
  - Behavior when signals are at maximum scaling limit.
  - Correct handling of missing/null inputs.
* **Arbitration Logic:** Unit tests must cover all three tie-breaking priority steps in `arbitration_engine.py` to prevent regression.
* **Execution:** Run tests via CLI:
  ```bash
  pytest tests/
  ```

---

## 4. Documentation Standards

* **Maintenance:** Documentation is part of the deliverable. A task is not complete until its associated documentation has been verified and updated.
* **File Integrity:** Never delete historical design rationales from `DECISIONS.md`. When decisions change, append the new decision, label the old one as "Superseded", and explain the reason for the change.
* **Links:** When linking to files in markdown, always use clickable relative file paths or markdown file links.

---

## 5. Repository Conventions & Folder Structure

Ensure all files are placed in their correct structural folders:

* `database/`: Database DDL files and raw SQL query files.
* `pipeline/`: Data ingestion, ETL cleaning, and outcome simulation scripts.
* `scoring/`: Python life event scoring rules and arbitration components.
* `engagement/`: EWMA calculation and transaction-engagement fusion logic.
* `tests/`: All unit and integration test scripts.
* `data/`: Sample test files and reference mapping tables (CSVs).
* `docs/`: Reference documentation, guides, and Power BI DAX sheets.
* `logs/`: Runtime logs and Pandas cleaning reports.
