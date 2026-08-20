# LLM-Oriented Ticket System Specification

## 1. Purpose

This project defines a small file-based ticket system for use in LLM-assisted software development.

The system exists to support the following workflow:

1. A human provides a project task or specification.
2. A planner LLM breaks that task into an epic and a set of tickets.
3. A worker LLM is given exactly one ticket and its related epic.
4. When that ticket is complete, the system determines the next available ticket.
5. The process repeats until all tickets for the task are complete.

The system is designed to be simple, human-readable, git-friendly, and suitable for use with small or local models.

## 2. Goals

The system shall:

* store project planning data in a human-friendly format
* allow all data to be version-controlled in git
* keep the ticket model small and easy for an LLM to understand
* allow humans to inspect and manage the state of work
* determine the next actionable ticket automatically
* generate the exact prompt text to be given to the next worker LLM
* provide a command-line interface for human use
* provide a locally served read-only webpage for inspection
* provide unit tests for the core system behaviour

## 3. Non-goals

This project shall not:

* start, manage, or supervise LLM processes
* send prompts to an LLM provider
* implement a chat interface
* provide a multi-user network service
* provide a database-backed system
* provide a browser-based editing interface
* attempt to be a general-purpose issue tracker
* model full agile process features such as story points, priorities, velocity, or sprint planning complexity

The system only needs to prepare, track, and expose work units.

## 4. Design principles

The implementation shall follow these principles:

* **File-based first**: the YAML files are the source of truth.
* **Human-readable**: files should be easy to inspect and edit directly.
* **Minimal schema**: every stored field must justify its existence.
* **Deterministic behaviour**: ticket selection and validation should be predictable.
* **Small context footprint**: the worker LLM should only receive the ticket, the related epic, and fixed instructions.
* **Few dependencies**: prefer the Python standard library and a very small set of third-party libraries.
* **Read-only web view**: editing is done through YAML files or CLI, not the webpage.

## 5. System overview

The system consists of four conceptual parts:

### 5.1 Data store

A directory of YAML files representing tasks, epics, and tickets.

### 5.2 Core logic

Python code that loads, validates, links, and queries the YAML data.

### 5.3 Human interface

A CLI that allows humans to create, inspect, validate, and update the state of work.

### 5.4 Read-only inspection UI

A local webpage that shows tasks, epics, tickets, dependencies, and current status.

## 6. Entities

The system shall model three entities.

### 6.1 Task

A task represents a top-level piece of requested work, usually derived from a human specification.

A task answers: “What broad thing are we trying to build?”

### 6.2 Epic

An epic represents the main implementation objective derived from a task.

A task will usually have one epic in the initial version of the system.

An epic answers: “What body of implementation work must be completed for this task?”

### 6.3 Ticket

A ticket represents one small, actionable unit of work suitable for a single worker LLM session.

A ticket answers: “What exact piece of work should be done now?”

## 7. Storage layout

The system shall store data under a `.tickets/` directory in the project root.

Recommended structure:

```text
.tickets/
    tasks/
        TASK-001.yaml
    epics/
        EPIC-001.yaml
    tickets/
        T-001.yaml
        T-002.yaml
    history/
    prompts/
        planner.md
        worker.md
```

### 7.1 Notes on layout

* `tasks/` contains task files
* `epics/` contains epic files
* `tickets/` contains ticket files
* `history/` may contain archived completed tasks, epics, or snapshots later if desired
* `prompts/` contains fixed prompt templates or instruction files used by the system

The initial implementation may leave `history/` unused.

## 8. YAML format

YAML shall be used for all stored data.

Reasons:

* human-friendly
* easy to diff in git
* easy for LLMs to read
* straightforward to parse in Python

## 9. Required schemas

## 9.1 Task schema

A task file shall contain:

* `id`
* `title`
* `status`
* `description`
* `acceptance_criteria`

Example:

```yaml
id: TASK-001
title: LLM-oriented ticket system
status: open
description: |
  Create a small file-based ticket system for LLM-assisted programming work.

acceptance_criteria:
  - A planner can break a spec into tickets
  - A worker can be given one ticket and one epic
  - A human can inspect progress from the CLI and webpage
```

## 9.2 Epic schema

An epic file shall contain:

* `id`
* `task`
* `title`
* `status`
* `description`
* `acceptance_criteria`

Example:

```yaml
id: EPIC-001
task: TASK-001
title: Build the minimal ticket system
status: open
description: |
  Build the Python implementation, CLI, prompt generation, webpage, and tests
  for the ticket system.

acceptance_criteria:
  - YAML files can be loaded and validated
  - The next actionable ticket can be selected automatically
  - The system can print the next worker prompt to the command line
  - A read-only local webpage can show tasks, epics, and tickets
```

## 9.3 Ticket schema

A ticket file shall contain:

* `id`
* `epic`
* `title`
* `status`
* `depends_on`
* `description`
* `acceptance_criteria`
* `out_of_scope`

Optional fields may include:

* `completion_notes`

Example:

```yaml
id: T-001
epic: EPIC-001
title: Load YAML task, epic, and ticket files
status: open
depends_on: []
description: |
  Implement loading of YAML files from the .tickets directory and convert them
  into internal Python objects.

acceptance_criteria:
  - Task files can be loaded
  - Epic files can be loaded
  - Ticket files can be loaded
  - Invalid YAML produces a clear error
  - Duplicate IDs are rejected

out_of_scope:
  - Webpage rendering
  - Prompt generation
```

## 10. Status model

The status values for tasks, epics, and tickets shall be constrained to:

* `open`
* `in_progress`
* `blocked`
* `closed`

No other status values shall be accepted in the initial version.

## 11. Relationships

The system shall enforce the following relationships:

* every epic must reference an existing task
* every ticket must reference an existing epic
* every task dependency listed in `depends_on` must reference an existing task in the same epic
* every epic dependency listed in `depends_on` must reference an existing epic in the same task
* every ticket dependency listed in `depends_on` must reference an existing ticket in the same task
* the dependency graph must not contain cycles

The system shall not store reverse dependency fields such as `blocks`. Reverse dependency information shall be derived automatically from `depends_on`.

## 12. Ticket sequencing

The system shall determine the next actionable ticket automatically.

A ticket is actionable if:

* its `status` is `open`
* it is not `blocked`
* every ticket in `depends_on` has `status: closed`

Where multiple actionable tickets exist, the system shall choose one deterministically.

The initial ordering rule is:

1. choose the lowest numbered epic among actionable tickets
2. within that epic, choose the lowest numbered task
3. within that task, choose the lowest numbered ticket
4. if a ticket has dependencies, skip it until all of them are closed

This preserves a simple predictable order without violating same-task dependency rules.

## 13. Prompt generation

## 13.1 Purpose

The system shall be able to generate the next worker prompt as plain text and print it to standard output.

This project is responsible for preparing the prompt text only.

This project is not responsible for starting or managing the LLM.

## 13.2 Input to prompt generation

Given a ticket ID, the system shall assemble a prompt from:

* fixed worker instructions
* the related epic
* the selected ticket

## 13.3 Output format

The generated prompt shall be plain text suitable for copy-paste into a new LLM session.

The prompt shall include:

* a short instruction block
* the epic
* the ticket

It may also include fixed project coding rules later, but the first implementation only needs the above.

## 13.4 Standard worker prompt structure

Recommended output structure:

```text
You are working on exactly one ticket.

Complete only the ticket below.
Do not perform unrelated work.
Use the acceptance criteria as the definition of done.
Respect the out_of_scope section.

Epic:
[epic content]

Ticket:
[ticket content]
```

## 13.5 Next prompt command

The CLI shall provide a command that determines the next actionable ticket and prints the corresponding worker prompt to standard output.

This is a required feature.

## 14. Planner output

The planner LLM is expected to break a task into one epic and a set of tickets.

The system shall support ingesting that structure in a strict machine-readable format.

The initial implementation may choose one of:

* YAML
* JSON

YAML is preferred for consistency with the rest of the system.

Recommended structure:

```yaml
epic:
  id: EPIC-001
  task: TASK-001
  title: Build the minimal ticket system
  status: open
  description: |
    Build the Python implementation, CLI, prompt generation, webpage, and tests.
  acceptance_criteria:
    - YAML files can be loaded and validated
    - The next worker prompt can be generated

tickets:
  - id: T-001
    epic: EPIC-001
    title: Load YAML files
    status: open
    depends_on: []
    description: |
      Load task, epic, and ticket files from disk.
    acceptance_criteria:
      - Tasks load
      - Epics load
      - Tickets load
    out_of_scope:
      - Prompt generation

  - id: T-002
    epic: EPIC-001
    title: Validate YAML relationships
    status: open
    depends_on:
      - T-001
    description: |
      Validate references and dependency rules.
    acceptance_criteria:
      - Missing references are rejected
      - Cycles are rejected
    out_of_scope:
      - CLI display
```

The system shall validate this structure before writing files to disk.

## 15. CLI requirements

The system shall provide a human command-line interface.

The CLI shall support at least the following operations.

## 15.1 Inspection commands

* `tickets list tasks`
* `tickets list epics`
* `tickets list tickets`
* `tickets show TASK-001`
* `tickets show EPIC-001`
* `tickets show T-001`

## 15.2 Validation commands

* `tickets validate`

This command shall validate:

* YAML parsing
* required fields
* allowed statuses
* reference integrity
* dependency cycles

## 15.3 State update commands

* `tickets close T-001`
* `tickets reopen T-001`
* `tickets block T-001`
* `tickets start T-001`

These commands shall update status fields in the corresponding YAML file.

## 15.4 Sequencing commands

* `tickets next`

This command shall print the next actionable ticket ID and title.

## 15.5 Prompt commands

* `tickets prompt T-001`

This command shall print the worker prompt for a specific ticket.

* `tickets prompt-next`

This command shall determine the next actionable ticket and print the corresponding worker prompt.

This command is required.

## 15.6 Creation commands

The initial implementation may include:

* `tickets create-task`
* `tickets import-plan <file>`

`create-task` creates a skeleton task file.

`import-plan` validates and writes the epic and tickets produced by the planner LLM.

These are useful but may be implemented after core read/query functionality.

## 15.7 Web server command

* `tickets serve`

This command shall start a local HTTP server for the read-only webpage.

## 16. Read-only webpage requirements

The local webpage shall provide a simple inspection interface for humans.

It shall be read-only in the initial version.

The page shall display:

* all tasks
* all epics
* all tickets
* statuses
* dependencies
* next actionable ticket

Recommended pages:

* `/` dashboard
* `/tasks`
* `/task/<id>`
* `/epics`
* `/epic/<id>`
* `/tickets`
* `/ticket/<id>`

The webpage may be rendered entirely on the server side. A heavy JavaScript frontend is not required.

## 17. Validation requirements

The system shall reject invalid data.

Validation shall include:

* invalid YAML
* missing required fields
* duplicate IDs
* invalid status values
* epic referencing a missing task
* ticket referencing a missing epic
* ticket dependency referencing a missing ticket
* cyclic dependencies

Validation errors shall be clear and readable by a human.

## 18. Git compatibility

The system shall be designed for storage in git.

To support that:

* files shall be plain text
* files shall be stable and deterministic in layout where possible
* one entity shall be stored per file
* there shall be no binary storage
* the system should avoid rewriting unrelated files during normal operations

## 19. Python implementation requirements

The system shall be written in Python.

The implementation should prefer:

* `argparse`
* `pathlib`
* `dataclasses`
* `http.server` or similarly small standard-library HTTP support
* `unittest`

A small YAML library such as `PyYAML` is acceptable.

The dependency count should be kept low.

## 20. Suggested package layout

A recommended Python layout is:

```text
tickets/
    __init__.py
    cli.py
    models.py
    repository.py
    validation.py
    sequencing.py
    prompting.py
    web.py
    rendering.py

tests/
    test_repository.py
    test_validation.py
    test_sequencing.py
    test_prompting.py
    test_cli.py
    test_web.py
```

This layout is not mandatory, but the responsibilities should be separated along similar lines.

## 21. Unit testing requirements

The project shall include unit tests for the core behaviours.

At minimum, tests shall cover:

### 21.1 Repository tests

* loading valid task, epic, and ticket files
* handling invalid YAML
* rejecting duplicate IDs

### 21.2 Validation tests

* rejecting missing references
* rejecting invalid status values
* rejecting dependency cycles

### 21.3 Sequencing tests

* finding the next actionable ticket
* skipping blocked tickets
* skipping tickets with open dependencies

### 21.4 Prompt tests

* generating a prompt for a given ticket
* generating the next prompt for the next actionable ticket
* ensuring epic and ticket content are included

### 21.5 CLI tests

* `list`
* `show`
* `validate`
* `next`
* `prompt`
* `prompt-next`

### 21.6 Web tests

* dashboard route works
* entity pages render expected text
* next actionable ticket appears on the dashboard

## 22. Expected workflow

The expected human workflow is:

1. create a task from a spec
2. use a planner LLM to create an epic and tickets
3. import that plan into the system
4. validate the resulting YAML
5. run `tickets prompt-next`
6. copy the printed prompt into a new worker LLM session
7. review the worker’s output
8. mark the ticket closed if accepted
9. repeat until all tickets are closed

The system prepares and tracks work. It does not run the worker LLM.

## 23. Acceptance criteria for this project

The project is complete when:

* tasks, epics, and tickets can be stored as YAML
* the system can validate the stored files
* the system can determine the next actionable ticket
* the system can print the next worker prompt to the command line
* humans can inspect the state from the CLI
* humans can inspect the state from a local read-only webpage
* unit tests cover the core logic

## 24. Future extensions

The following are reasonable later extensions, but are not required in the initial version:

* templates for planner and worker prompts
* ticket completion notes
* task archival
* richer dependency visualisation
* optional project coding rules in generated prompts
* support for more than one epic per task
* JSON export

They should not complicate the first implementation.
