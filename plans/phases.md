# Implementation Phases

This document breaks down the LLM-oriented ticket system implementation into discrete, testable phases.

Each phase:
- builds on the previous phase
- delivers working, testable functionality
- includes unit tests
- can be validated by a human before moving forward

## Phase 1: Core Data Models and YAML Loading

**Goal**: Establish the foundational data structures and file loading.

**Deliverables**:
- Python dataclasses for Task, Epic, and Ticket entities
- YAML file loading from `.tickets/` directory structure
- Basic repository class to load and store entities in memory
- Error handling for missing files and invalid YAML

**Implementation**:
- `tickets/models.py` - dataclasses for Task, Epic, Ticket
- `tickets/repository.py` - Repository class with load methods
- `.tickets/` directory structure (tasks/, epics/, tickets/)

**Unit Tests**:
- Load valid task YAML
- Load valid epic YAML
- Load valid ticket YAML
- Handle missing files gracefully
- Handle invalid YAML with clear error messages
- Handle missing required fields

**Human Testing**:
1. Create sample YAML files in `.tickets/` directories
2. Run unit tests: `python -m unittest discover tests`
3. Verify that valid files load without errors
4. Verify that invalid files produce clear error messages

**Success Criteria**:
- All unit tests pass
- Sample YAML files can be loaded into memory
- Invalid YAML produces readable error messages

---

## Phase 2: Validation Logic

**Goal**: Implement all validation rules for data integrity.

**Deliverables**:
- Validation for required fields
- Status value validation (open, in_progress, blocked, closed)
- Reference integrity checks (epic → task, ticket → epic)
- Dependency existence checks
- Cycle detection in ticket dependencies
- Duplicate ID detection

**Implementation**:
- `tickets/validation.py` - Validator class with all validation rules
- Enhanced Repository to run validation after loading

**Unit Tests**:
- Reject invalid status values
- Reject epic referencing non-existent task
- Reject ticket referencing non-existent epic
- Reject ticket dependency on non-existent ticket
- Detect simple cycles (A → B → A)
- Detect complex cycles (A → B → C → A)
- Detect duplicate IDs across entities
- Accept valid data structures

**Human Testing**:
1. Create deliberately invalid YAML files (bad references, cycles, etc.)
2. Run unit tests
3. Load valid and invalid data through repository
4. Verify clear, actionable error messages for each validation failure

**Success Criteria**:
- All validation tests pass
- Invalid data is rejected with clear explanations
- Valid data passes all checks
- Cycle detection works for complex dependency graphs

---

## Phase 3: Ticket Sequencing

**Goal**: Implement logic to find the next actionable ticket.

**Deliverables**:
- Sequencing logic to identify actionable tickets
- Deterministic selection when multiple tickets are actionable
- Respect for ticket status, dependencies, and blocked state

**Implementation**:
- `tickets/sequencing.py` - functions to find next actionable ticket
- Algorithm: ticket is actionable if status is 'open' and all dependencies are 'closed'
- Deterministic ordering: sort by ID and return first match

**Unit Tests**:
- Find next ticket when no dependencies exist
- Skip tickets with open dependencies
- Skip blocked tickets
- Skip in_progress tickets
- Skip closed tickets
- Return None when no tickets are actionable
- Select deterministically when multiple tickets are actionable
- Handle empty ticket list

**Human Testing**:
1. Create a set of tickets with various statuses and dependencies
2. Run unit tests
3. Manually verify which ticket should be next
4. Call sequencing function and verify it matches expectation
5. Close a dependency and verify a blocked ticket becomes actionable

**Success Criteria**:
- All sequencing tests pass
- Next ticket selection is correct and deterministic
- Dependencies properly block tickets from being selected

---

## Phase 4: Basic CLI Commands

**Goal**: Provide human interface for inspection and validation.

**Deliverables**:
- CLI entry point with argparse
- Commands: `list tasks`, `list epics`, `list tickets`
- Commands: `show <id>`
- Command: `validate`
- Command: `next`

**Implementation**:
- `tickets/cli.py` - CLI framework with argparse
- `tickets/__main__.py` or `main.py` - entry point
- List commands display all entities of a type
- Show command displays full entity details
- Validate command runs all validation and reports results
- Next command displays next actionable ticket ID and title

**Unit Tests**:
- CLI argument parsing for each command
- List commands produce output for each entity type
- Show command with valid ID produces output
- Show command with invalid ID produces error
- Validate command reports validation errors
- Next command with actionable ticket shows result
- Next command with no actionable ticket shows appropriate message

**Human Testing**:
1. Install CLI: `pip install -e .`
2. Run `tickets list tasks` - verify output
3. Run `tickets list epics` - verify output
4. Run `tickets list tickets` - verify output
5. Run `tickets show TASK-001` - verify details displayed
6. Run `tickets show INVALID` - verify error message
7. Run `tickets validate` - verify validation results
8. Run `tickets next` - verify next ticket shown

**Success Criteria**:
- All CLI tests pass
- All commands produce readable output
- Error messages are clear
- Can inspect entire system state from command line

---

## Phase 5: Prompt Generation

**Goal**: Generate worker prompts from tickets and epics.

**Deliverables**:
- Prompt generation for a given ticket ID
- Include epic and ticket content
- Follow standard worker prompt structure from design
- Plain text output suitable for copy-paste

**Implementation**:
- `tickets/prompting.py` - prompt generation functions
- Load epic related to ticket
- Format prompt with instructions, epic, and ticket
- Return plain text string

**Unit Tests**:
- Generate prompt for valid ticket
- Prompt includes epic content
- Prompt includes ticket content
- Prompt includes fixed instructions
- Error when ticket ID doesn't exist
- Error when related epic doesn't exist

**Human Testing**:
1. Create test ticket and epic
2. Run unit tests
3. Generate prompt manually via prompting module
4. Verify prompt contains all required sections
5. Verify prompt is readable and copy-pasteable

**Success Criteria**:
- All prompting tests pass
- Generated prompts contain epic and ticket
- Prompts follow specified format
- Output is plain text suitable for LLM input

---

## Phase 6: CLI State Management

**Goal**: Allow humans to update ticket status from CLI.

**Deliverables**:
- Commands: `start <ticket-id>`, `close <ticket-id>`, `reopen <ticket-id>`, `block <ticket-id>`
- Update YAML files on disk with new status
- Preserve file formatting where possible

**Implementation**:
- Add state update methods to Repository
- Implement CLI commands for state changes
- Load YAML, update status field, write back to disk
- Validate status transitions where appropriate

**Unit Tests**:
- Start command changes status to in_progress
- Close command changes status to closed
- Reopen command changes status to open
- Block command changes status to blocked
- Commands update YAML file on disk
- Commands reject invalid ticket IDs
- Commands maintain other fields unchanged

**Human Testing**:
1. Create test ticket with status 'open'
2. Run `tickets start T-001` - verify status changes
3. Check YAML file - verify it shows 'in_progress'
4. Run `tickets close T-001` - verify status changes
5. Check YAML file - verify it shows 'closed'
6. Run `tickets next` - verify closed ticket is not selected
7. Run `tickets reopen T-001` - verify back to 'open'

**Success Criteria**:
- All state management tests pass
- Status changes persist to disk
- YAML files remain valid after updates
- Status changes affect ticket sequencing correctly

---

## Phase 7: CLI Prompt Commands

**Goal**: Integrate prompt generation into CLI.

**Deliverables**:
- Command: `prompt <ticket-id>` - generate prompt for specific ticket
- Command: `prompt-next` - generate prompt for next actionable ticket
- Output to stdout for easy redirection or copy-paste

**Implementation**:
- Add prompt commands to CLI
- `prompt <id>` calls prompting module with ticket ID
- `prompt-next` calls sequencing to find next ticket, then generates prompt
- Print result to stdout

**Unit Tests**:
- Prompt command with valid ticket ID produces prompt
- Prompt command with invalid ticket ID shows error
- Prompt-next with actionable ticket produces prompt
- Prompt-next with no actionable ticket shows message

**Human Testing**:
1. Run `tickets prompt T-001` - verify prompt appears
2. Copy prompt and verify it contains epic and ticket
3. Run `tickets prompt-next` - verify next ticket prompt appears
4. Close all tickets and run `tickets prompt-next` - verify appropriate message
5. Test redirecting output: `tickets prompt-next > worker-prompt.txt`

**Success Criteria**:
- All prompt command tests pass
- Prompt-next correctly identifies and generates prompt for next ticket
- Output is suitable for copy-paste or file redirection
- Core workflow is now functional: humans can get next prompt and update status

---

## Phase 8: Read-Only Web Interface

**Goal**: Provide browser-based inspection of system state.

**Deliverables**:
- Local HTTP server using Python standard library
- Routes: `/`, `/tasks`, `/task/<id>`, `/epics`, `/epic/<id>`, `/tickets`, `/ticket/<id>`
- Server-side rendering (no complex frontend required)
- Display all entities, statuses, dependencies
- Highlight next actionable ticket on dashboard

**Implementation**:
- `tickets/web.py` - HTTP server and route handlers
- `tickets/rendering.py` - HTML generation functions
- CLI command: `tickets serve` - start web server
- Simple HTML templates or string formatting
- Dashboard shows summary and next actionable ticket
- Entity list pages show all items with status
- Entity detail pages show full content

**Unit Tests**:
- Dashboard route returns 200 and expected content
- Task list route shows all tasks
- Task detail route shows task content
- Epic list route shows all epics
- Epic detail route shows epic content
- Ticket list route shows all tickets
- Ticket detail route shows ticket content
- Next actionable ticket appears on dashboard
- Invalid ID routes return 404

**Human Testing**:
1. Run `tickets serve`
2. Open browser to `http://localhost:8000/`
3. Verify dashboard shows summary and next ticket
4. Click through to `/tasks` - verify all tasks listed
5. Click a task ID - verify task details shown
6. Navigate to `/tickets` - verify all tickets with status
7. Click a ticket ID - verify full ticket content including dependencies
8. Verify blocked and closed tickets are visually distinct

**Success Criteria**:
- All web tests pass
- Web interface is readable and navigable
- All entity data is accessible through browser
- Next actionable ticket is visible on dashboard
- Server starts and stops cleanly

---

## Phase 9: Plan Import and Creation

**Goal**: Support creating tasks and importing planner output.

**Deliverables**:
- Command: `create-task` - create skeleton task file
- Command: `import-plan <file>` - validate and import epic + tickets
- Support YAML format for planner output (as specified in design)

**Implementation**:
- `tickets/creation.py` - functions to create and write YAML files
- `create-task` prompts for or accepts task details, writes YAML
- `import-plan` loads planner YAML, validates structure, writes epic and ticket files
- Ensure all validation rules apply during import

**Unit Tests**:
- Create-task generates valid task YAML
- Import-plan with valid planner YAML creates correct files
- Import-plan validates epic references task
- Import-plan validates ticket dependencies
- Import-plan rejects duplicate IDs
- Import-plan rejects invalid structure
- Import-plan performs all standard validation

**Human Testing**:
1. Run `tickets create-task` - follow prompts, verify YAML created
2. Create planner output YAML file with epic and tickets
3. Run `tickets import-plan planner-output.yaml`
4. Run `tickets validate` - verify imported data is valid
5. Run `tickets list epics` - verify epic appears
6. Run `tickets list tickets` - verify all tickets appear
7. Run `tickets next` - verify first actionable ticket is correct
8. Try importing invalid planner output - verify clear errors

**Success Criteria**:
- All import/creation tests pass
- Can create tasks through CLI
- Can import planner output successfully
- Validation catches errors in planner output
- End-to-end workflow is complete

---

## Phase 10: Integration and Polish

**Goal**: End-to-end testing and documentation.

**Deliverables**:
- Full end-to-end workflow test
- README with installation and usage instructions
- Example planner and worker prompts in `.tickets/prompts/`
- Complete sample workflow in documentation

**Implementation**:
- Create comprehensive integration tests
- Document installation: `pip install -e .`
- Document complete workflow from task creation to completion
- Create example YAML files for testing
- Ensure error messages are consistently clear
- Add any missing edge case handling

**Integration Tests**:
- Complete workflow: create task → import plan → validate → prompt-next → close ticket → repeat
- Verify web interface shows correct state throughout workflow
- Test with multiple epics and tasks
- Test with complex dependency graphs
- Verify git-friendly file operations (no unnecessary rewrites)

**Human Testing**:
1. Start from empty `.tickets/` directory
2. Create a new task
3. Write and import a plan (or create manually)
4. Run `tickets validate` - should pass
5. Run `tickets serve` and inspect in browser
6. Run `tickets prompt-next` - get first prompt
7. Mark ticket closed
8. Run `tickets prompt-next` - get second prompt
9. Continue until all tickets closed
10. Verify dashboard shows all complete

**Success Criteria**:
- All integration tests pass
- Complete workflow is documented
- All CLI commands work correctly
- Web interface works correctly
- System is ready for real use

---

## Testing Guidelines

For all phases:
- Write unit tests before or alongside implementation
- Run tests frequently: `python -m unittest discover tests`
- Use `unittest` as specified in AGENTS.md
- Keep tests readable and simple
- Test both success and failure cases
- Ensure good error messages for all failures

## Development Tips

- Start each phase with the tests
- Use sample YAML files in `.tickets/` for manual testing
- Run `tickets validate` frequently during development
- Keep functions small and focused
- Use type hints throughout
- Follow the coding guidelines in AGENTS.md:
  - Prefer functional style over OO
  - Use explanatory variable names
  - No magic numbers
  - No leading underscores
  - Keep code readable and simple

## Dependencies

Expected Python packages:
- `PyYAML` - for YAML parsing
- `pathlib` - for file operations (standard library)
- `dataclasses` - for models (standard library)
- `argparse` - for CLI (standard library)
- `http.server` - for web interface (standard library)
- `unittest` - for testing (standard library)

Keep dependencies minimal as per design principles.

## Completion Criteria

The project is complete when:
- All phases are implemented and tested
- All unit tests pass
- All integration tests pass
- Human can complete full workflow from CLI
- Human can inspect system state from web interface
- Documentation is clear and complete
- Code follows project guidelines

## Notes

Each phase builds on the previous one, but phases can be extended or adjusted based on discoveries during implementation. The key is that at the end of each phase, something concrete works and can be tested by a human.

Phases 1-7 deliver the core CLI workflow. Phase 8 adds the web interface. Phase 9 completes the tooling. Phase 10 ensures everything works together.
