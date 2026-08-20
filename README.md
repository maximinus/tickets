# Tickets

File-based ticket workflow for LLM-assisted software development.

## Requirements

- Python 3.14+
- PyYAML (installed via project dependencies)

## Installation

From the project root:

```bash
pip install -e .
```

If you are using uv and your environment does not provide a pip command:

```bash
uv pip install -e .
```

If you want uv to create/sync the project environment directly:

```bash
uv sync
```

Verify the CLI is installed:

```bash
tickets --help
```

Run with either command style:

```bash
tickets --help
python -m tickets --help
```

## Repository Layout

The CLI reads and writes YAML inside `.tickets` in your current working directory.

```text
.tickets/
	tasks/
	epics/
	tickets/
	prompts/
		planner.md
		worker.md
```

## Commands

### Inspection

```bash
tickets list
tickets list tasks
tickets list epics
tickets list tickets
tickets show TASK-001
tickets show EPIC-001
tickets show T-001
tickets next
```

### Validation

```bash
tickets validate
```

### Prompting

```bash
tickets prompt T-001
tickets prompt-next
```

### Creation and Import

```bash
tickets create-task --task-id TASK-001 --title "My Task" --description "Task description"
tickets import-plan plan.yaml
```

Notes:
- `create-task` defaults status to `open`.
- `create-task` auto-generates the next `TASK-###` id when `--task-id` is omitted.
- `import-plan` validates plan structure and repository integrity before writing files.

### Web UI

```bash
tickets serve
tickets serve --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/` to inspect dashboard, tasks, epics, and tickets.

## Dependency rules

Task dependencies are modeled with `depends_on` and are only valid for tasks within the same epic.

Epic dependencies are also supported with `depends_on`, and they are only valid for epics that belong to the same task.

Ticket dependencies are modeled with `depends_on` and are only valid for tickets that belong to the same task.

A dependency graph that references missing entities or creates a cycle is rejected during validation.

When no dependencies are present, the next actionable ticket is chosen by the lowest numbered epic, then the lowest numbered task in that epic, then the lowest numbered ticket in that task.

## End-to-End Workflow

1. Create a task.

```bash
tickets create-task --task-id TASK-001 --title "Build feature X" --description "Top-level task"
```

2. Generate a planner output YAML file (using `.tickets/prompts/planner.md` as template guidance).

3. Import the plan.

```bash
tickets import-plan plan.yaml
```

4. Validate repository state.

```bash
tickets validate
```

5. Fetch the next worker prompt.

```bash
tickets prompt-next
```

6. Complete the work for that ticket, then set ticket YAML `status: closed` when accepted.

7. Repeat `tickets prompt-next` until no actionable tickets remain.

8. Run the web UI for final inspection.

```bash
tickets serve
```

## Example Prompt Templates

- Planner template: `.tickets/prompts/planner.md`
- Worker template: `.tickets/prompts/worker.md`

## Testing

Run everything:

```bash
python -m unittest discover tests
```

Run the integration suite only:

```bash
python -m unittest tests.test_integration
```

## Manual Test Guide

For step-by-step human validation scenarios, see `docs/manual-tests.md`.
