# Human Manual Tests

These are easy, copy-paste tests for a human to verify the CLI behavior.

## Quick Setup

Run from the repository root.

```bash
source .venv/bin/activate
```

If you already have a local `.tickets` folder you care about, back it up first.

```bash
mv .tickets .tickets.backup.manual-test 2>/dev/null || true
```

## Test Set A: Valid data

Load the ready-made valid fixture:

```bash
rm -rf .tickets
cp -R docs/fixtures/basic/.tickets .tickets
```

### Test A1: Validate passes

Run upgrade first (safe no-op when metadata is already current):

```bash
python -m tickets upgrade
```

Expected:
- Exit code `0`

```bash
python -m tickets validate
```

Expected:
- Exit code `0`
- Output contains `Validation passed.`

### Test A1b: Upgrade adds missing depends_on metadata when needed

Create a task file without `depends_on`:

```bash
cat > .tickets/tasks/TASK-900.yaml <<'YAML'
id: TASK-900
title: Upgrade metadata sample
status: open
description: Task used for upgrade metadata validation.
acceptance_criteria:
	- upgrade inserts default depends_on
YAML
```

Run upgrade:

```bash
python -m tickets upgrade
```

Expected:
- Exit code `0`
- Output contains `TASK-900: Added default "depends_on" with value "[]"`

Then validate:

```bash
python -m tickets validate
```

Expected:
- Exit code `0`
- Output contains `Validation passed.`

### Test A2: List commands show entities

```bash
python -m tickets list tasks
python -m tickets list epics
python -m tickets list tickets
```

Expected:
- Tasks output includes `TASK-001`
- Epics output includes `EPIC-001`
- Tickets output includes `T-001`, `T-002`, and `T-003`

### Test A3: Show command displays full fields

```bash
python -m tickets show T-001
```

Expected output includes:
- `id: T-001`
- `epic: EPIC-001`
- `acceptance_criteria:`
- `out_of_scope:`

### Test A4: Next ticket is deterministic

```bash
python -m tickets next
```

Expected:
- Output is `T-001: Load YAML task, epic, and ticket files`

Reason:
- `T-001` is open and has no dependencies.
- `T-002` depends on `T-001`, so it is not actionable yet.
- `T-003` is blocked.

### Test A5: Prompt command returns worker prompt

```bash
python -m tickets prompt T-001
```

Expected output includes:
- `You are working on exactly one ticket.`
- `Epic:`
- `Ticket:`
- `id: EPIC-001`
- `id: T-001`

### Test A6: Prompt-next returns prompt for the next actionable ticket

```bash
python -m tickets prompt-next
```

Expected output includes:
- `You are working on exactly one ticket.`
- `Ticket:`
- `id: T-001`

## Test Set B: Invalid data

Load the invalid fixture:

```bash
rm -rf .tickets
cp -R docs/fixtures/invalid-missing-epic/.tickets .tickets
```

### Test B1: Validate reports missing epic reference

```bash
python -m tickets validate
```

Expected:
- Non-zero exit code
- Error output contains `missing epic`
- Error output contains `EPIC-999`

### Test B2: Prompt with missing ticket id returns a clear error

```bash
rm -rf .tickets
cp -R docs/fixtures/basic/.tickets .tickets
python -m tickets prompt T-999
```

Expected:
- Non-zero exit code
- Error output contains `Ticket not found`

## Test Set C: Complex text editor project

Load the complex fixture with multiple tasks, epics, and tickets:

```bash
rm -rf .tickets
cp -R docs/fixtures/complex-text-editor/.tickets .tickets
```

### Test C1: Validate complex fixture

Run upgrade first because this fixture intentionally represents legacy metadata without `depends_on` in all files:

```bash
python -m tickets upgrade
```

Expected:
- Exit code `0`
- Output includes updates such as `TASK-100: Added default "depends_on" with value "[]"`

```bash
python -m tickets validate
```

Expected:
- Exit code `0`
- Output contains `Validation passed.`

### Test C2: List shows multiple tasks and epics

```bash
python -m tickets list tasks
python -m tickets list epics
```

Expected:
- Tasks output includes `TASK-100` and `TASK-200`
- Epics output includes `EPIC-110`, `EPIC-120`, and `EPIC-210`

### Test C3: List tickets shows mixed statuses

```bash
python -m tickets list tickets
```

Expected output includes examples of:
- `closed` (for example `T-101`)
- `in_progress` (for example `T-103`)
- `open` (for example `T-121`)
- `blocked` (for example `T-123`)

### Test C4: Next command chooses first actionable open ticket

```bash
python -m tickets next
```

Expected:
- Output is `T-121: Implement open and save file commands`

Reason:
- `T-101` and `T-102` are closed.
- `T-103` is `in_progress`, so it is not actionable.
- `T-121` is open and its dependency (`T-102`) is closed.
- Tickets with lower IDs in open state are either blocked or not actionable.

### Test C5: Prompt-next returns the prompt for T-121

```bash
python -m tickets prompt-next
```

Expected output includes:
- `You are working on exactly one ticket.`
- `Epic:`
- `Ticket:`
- `id: T-121`
- `id: EPIC-120`

### Test C6: Prompt for a deep dependency ticket

```bash
python -m tickets prompt T-213
```

Expected output includes:
- `id: T-213`
- `title: Implement two-pane split editor layout`
- `depends_on:`
- `- T-212`

## Optional cleanup

Restore your previous data if you backed it up:

```bash
rm -rf .tickets
mv .tickets.backup.manual-test .tickets 2>/dev/null || true
```

## Test Set D: Phase 10 End-to-End Workflow

Start from an empty working repository state:

```bash
rm -rf .tickets
mkdir -p .tickets
```

### Test D1: Create task from CLI

```bash
python -m tickets create-task --task-id TASK-001 --title "Phase 10 task" --description "End-to-end test task" --acceptance-criterion "Workflow completes"
```

Expected:
- Exit code `0`
- Output contains `Created task TASK-001`

### Test D2: Create and import a plan file

Create `plan.yaml`:

```yaml
epic:
	id: EPIC-001
	task: TASK-001
	title: End-to-end epic
	status: open
	description: |
		Complete the full workflow with two dependent tickets.
	acceptance_criteria:
		- End-to-end flow is testable

tickets:
	- id: T-001
		epic: EPIC-001
		title: First workflow ticket
		status: open
		depends_on: []
		description: |
			First step.
		acceptance_criteria:
			- First step complete
		out_of_scope:
			- Unrelated work

	- id: T-002
		epic: EPIC-001
		title: Second workflow ticket
		status: open
		depends_on:
			- T-001
		description: |
			Second step.
		acceptance_criteria:
			- Second step complete
		out_of_scope:
			- Unrelated work
```

Import it:

```bash
python -m tickets import-plan plan.yaml
```

Expected:
- Exit code `0`
- Output contains `Imported epic EPIC-001 and 2 tickets.`

### Test D3: Validate and fetch next prompt

```bash
python -m tickets validate
python -m tickets prompt-next
```

Expected:
- Validate prints `Validation passed.`
- Prompt output includes `id: T-001`

### Test D4: Close first ticket and fetch next prompt

Edit `.tickets/tickets/T-001.yaml` and change:

```yaml
status: closed
```

Then run:

```bash
python -m tickets prompt-next
```

Expected:
- Output includes `id: T-002`

### Test D5: Close all tickets and verify completion

Edit `.tickets/tickets/T-002.yaml` and set:

```yaml
status: closed
```

Then run:

```bash
python -m tickets prompt-next
```

Expected:
- Output contains `No actionable tickets found.`

### Test D6: Inspect completed state in web UI

```bash
python -m tickets serve
```

Open `http://127.0.0.1:8000/`.

Expected:
- Dashboard loads
- Next actionable panel shows completion message
- Tasks, epics, and tickets pages render successfully

## Test Set E: Ticket Status Command And Cascade Rules

Load the ready-made valid fixture:

```bash
rm -rf .tickets
cp -R docs/fixtures/basic/.tickets .tickets
python -m tickets upgrade
python -m tickets validate
```

Expected:
- Validate prints `Validation passed.`

### Test E1: Ticket-only status update command

```bash
python -m tickets set-status T-001 in_progress
```

Expected:
- Exit code `0`
- Output contains `T-001: status open -> in_progress`

### Test E2: Parent task and epic statuses cascade from ticket changes

After E1, run:

```bash
python -m tickets show TASK-001
python -m tickets show EPIC-001
```

Expected:
- Task output contains `status: in_progress`
- Epic output contains `status: in_progress`

### Test E3: Dependency guard rejects non-blocked transition while dependency is unresolved

Ticket `T-002` depends on `T-001`. While `T-001` is not closed, this should fail:

```bash
python -m tickets set-status T-002 open
```

Expected:
- Non-zero exit code
- Error output contains `not closed`

### Test E4: Explicitly block dependent ticket

```bash
python -m tickets set-status T-002 blocked
```

Expected:
- Exit code `0`
- Output contains `T-002: status`

### Test E5: Resolve dependency and unblock ticket

Close dependency:

```bash
python -m tickets set-status T-001 closed
```

Then reopen dependent ticket:

```bash
python -m tickets set-status T-002 open
```

Expected:
- Both commands exit `0`
- Second command succeeds because dependency is now closed

### Test E6: Command rejects non-ticket IDs

```bash
python -m tickets set-status TASK-001 closed
python -m tickets set-status EPIC-001 closed
```

Expected:
- Non-zero exit code for both commands
- Error output contains `only supported for tickets`
