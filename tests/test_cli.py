from io import StringIO
from pathlib import Path
import tempfile
import unittest

from tickets.cli import build_parser, run_cli

SAMPLE_TASK_YAML = """
id: TASK-001
title: Example task
status: open
description: Task description
acceptance_criteria:
    - criterion one
""".strip()

SAMPLE_TASK_YAML_WITH_DEPENDS_ON = """
id: TASK-001
title: Example task
status: open
depends_on: []
description: Task description
acceptance_criteria:
    - criterion one
""".strip()

SAMPLE_EPIC_YAML = """
id: EPIC-001
task: TASK-001
title: Example epic
status: open
depends_on: []
description: Epic description
acceptance_criteria:
    - criterion one
""".strip()

SAMPLE_TICKET_TEMPLATE = """
id: {ticket_id}
epic: EPIC-001
title: {title}
status: {status}
depends_on: {depends_on}
description: Ticket description
acceptance_criteria:
    - criterion one
out_of_scope:
    - not included
""".strip()

INVALID_TICKET_WITH_MISSING_EPIC = """
id: T-001
epic: EPIC-999
title: Invalid ticket
status: open
depends_on: []
description: Ticket description
acceptance_criteria:
    - criterion one
out_of_scope:
    - not included
""".strip()

SAMPLE_PLAN_YAML = """
epic:
    id: EPIC-001
    task: TASK-001
    title: Imported epic
    status: open
    depends_on: []
    description: Imported epic description
    acceptance_criteria:
        - epic criterion

tickets:
    - id: T-001
      epic: EPIC-001
      title: Imported ticket
      status: open
      depends_on: []
      description: Imported ticket description
      acceptance_criteria:
          - ticket criterion
      out_of_scope:
          - not included
""".strip()


class CliTests(unittest.TestCase):
    def test_argument_parsing_for_list_command_without_entity(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["list"])

        self.assertEqual(parsed_arguments.command, "list")
        self.assertIsNone(parsed_arguments.entity)

    def test_argument_parsing_for_list_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["list", "tasks"])

        self.assertEqual(parsed_arguments.command, "list")
        self.assertEqual(parsed_arguments.entity, "tasks")

    def test_argument_parsing_for_show_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["show", "TASK-001"])

        self.assertEqual(parsed_arguments.command, "show")
        self.assertEqual(parsed_arguments.entity_id, "TASK-001")

    def test_argument_parsing_for_validate_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["validate"])

        self.assertEqual(parsed_arguments.command, "validate")

    def test_argument_parsing_for_next_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["next"])

        self.assertEqual(parsed_arguments.command, "next")

    def test_argument_parsing_for_prompt_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["prompt", "T-001"])

        self.assertEqual(parsed_arguments.command, "prompt")
        self.assertEqual(parsed_arguments.ticket_id, "T-001")

    def test_argument_parsing_for_prompt_next_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["prompt-next"])

        self.assertEqual(parsed_arguments.command, "prompt-next")

    def test_argument_parsing_for_create_task_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(
            [
                "create-task",
                "--task-id",
                "TASK-010",
                "--title",
                "Created task",
                "--description",
                "Description",
                "--acceptance-criterion",
                "one criterion",
            ]
        )

        self.assertEqual(parsed_arguments.command, "create-task")
        self.assertEqual(parsed_arguments.task_id, "TASK-010")
        self.assertEqual(parsed_arguments.title, "Created task")
        self.assertEqual(parsed_arguments.description, "Description")
        self.assertEqual(parsed_arguments.acceptance_criterion, ["one criterion"])

    def test_argument_parsing_for_import_plan_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["import-plan", "plan.yaml"])

        self.assertEqual(parsed_arguments.command, "import-plan")
        self.assertEqual(parsed_arguments.plan_file, "plan.yaml")

    def test_argument_parsing_for_upgrade_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["upgrade"])

        self.assertEqual(parsed_arguments.command, "upgrade")

    def test_argument_parsing_for_serve_command(self) -> None:
        parser = build_parser()
        parsed_arguments = parser.parse_args(["serve", "--host", "0.0.0.0", "--port", "8100"])

        self.assertEqual(parsed_arguments.command, "serve")
        self.assertEqual(parsed_arguments.host, "0.0.0.0")
        self.assertEqual(parsed_arguments.port, 8100)

    def test_list_commands_produce_output_for_each_entity_type(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001")

            task_output = StringIO()
            epic_output = StringIO()
            ticket_output = StringIO()
            error_output = StringIO()

            task_exit_code = run_cli(
                ["list", "tasks"],
                standard_output=task_output,
                standard_error=error_output,
                root_path=root_path,
            )
            epic_exit_code = run_cli(
                ["list", "epics"],
                standard_output=epic_output,
                standard_error=error_output,
                root_path=root_path,
            )
            ticket_exit_code = run_cli(
                ["list", "tickets"],
                standard_output=ticket_output,
                standard_error=error_output,
                root_path=root_path,
            )

            self.assertEqual(task_exit_code, 0)
            self.assertEqual(epic_exit_code, 0)
            self.assertEqual(ticket_exit_code, 0)

            self.assertIn("TASK-001", task_output.getvalue())
            self.assertIn("EPIC-001", epic_output.getvalue())
            self.assertIn("T-001", ticket_output.getvalue())

    def test_list_command_without_entity_shows_all_entities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001")

            standard_output = StringIO()
            standard_error = StringIO()

            exit_code = run_cli(
                ["list"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            output_lines = standard_output.getvalue().splitlines()
            self.assertGreaterEqual(len(output_lines), 3)
            self.assertEqual(output_lines[0], "EPIC-001 | open | Example epic")
            self.assertEqual(output_lines[1], "  TASK-001 | open | Example task")
            self.assertEqual(output_lines[2], "    T-001 | open | Ticket T-001")
            self.assertEqual(standard_error.getvalue(), "")

    def test_show_command_with_valid_id_produces_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["show", "TASK-001"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("id: TASK-001", standard_output.getvalue())
            self.assertIn("title: Example task", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_show_command_with_invalid_id_produces_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["show", "INVALID"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(standard_output.getvalue(), "")
            self.assertIn("Entity not found", standard_error.getvalue())

    def test_validate_command_reports_validation_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_raw_ticket(root_path, INVALID_TICKET_WITH_MISSING_EPIC)

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["validate"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(standard_output.getvalue(), "")
            self.assertIn("missing epic", standard_error.getvalue())

    def test_next_command_with_actionable_ticket_shows_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="open", depends_on=[])
            write_sample_ticket(root_path, ticket_id="T-002", status="open", depends_on=["T-001"])

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["next"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("EPIC-001 -> TASK-001 -> T-001: Ticket T-001", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_next_command_with_no_actionable_ticket_shows_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="closed")
            write_sample_ticket(root_path, ticket_id="T-002", status="blocked")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["next"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("No actionable tickets found", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_prompt_command_with_valid_ticket_id_produces_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="open", depends_on=[])

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["prompt", "T-001"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("You are working on exactly one ticket.", standard_output.getvalue())
            self.assertIn("Epic:", standard_output.getvalue())
            self.assertIn("Ticket:", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_prompt_command_with_invalid_ticket_id_shows_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="open", depends_on=[])

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["prompt", "T-999"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(standard_output.getvalue(), "")
            self.assertIn("Ticket not found", standard_error.getvalue())

    def test_prompt_next_with_actionable_ticket_produces_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="open", depends_on=[])
            write_sample_ticket(root_path, ticket_id="T-002", status="open", depends_on=["T-001"])

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["prompt-next"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("You are working on exactly one ticket.", standard_output.getvalue())
            self.assertIn("id: T-001", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_prompt_next_with_no_actionable_ticket_shows_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", status="closed")
            write_sample_ticket(root_path, ticket_id="T-002", status="blocked")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["prompt-next"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("No actionable tickets found", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

    def test_create_task_command_creates_task_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                [
                    "create-task",
                    "--task-id",
                    "TASK-001",
                    "--title",
                    "Created task",
                    "--description",
                    "Task description",
                    "--acceptance-criterion",
                    "criterion one",
                ],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Created task TASK-001", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

            created_task_path = root_path / ".tickets" / "tasks" / "TASK-001.yaml"
            self.assertTrue(created_task_path.exists())
            self.assertIn("title: Created task", created_task_path.read_text(encoding="utf-8"))

    def test_import_plan_command_imports_epic_and_tickets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            plan_file_path = root_path / "plan.yaml"
            plan_file_path.write_text(SAMPLE_PLAN_YAML, encoding="utf-8")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["import-plan", "plan.yaml"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("Imported epic EPIC-001 and 1 tickets", standard_output.getvalue())
            self.assertEqual(standard_error.getvalue(), "")

            created_epic_path = root_path / ".tickets" / "epics" / "EPIC-001.yaml"
            created_ticket_path = root_path / ".tickets" / "tickets" / "T-001.yaml"
            self.assertTrue(created_epic_path.exists())
            self.assertTrue(created_ticket_path.exists())

    def test_upgrade_command_adds_default_depends_on_for_missing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic_without_depends_on(root_path)
            write_sample_ticket_without_depends_on(root_path, ticket_id="T-001")

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["upgrade"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(standard_error.getvalue(), "")

            output_lines = standard_output.getvalue().splitlines()
            self.assertEqual(
                output_lines,
                [
                    'TASK-001: Added default "depends_on" with value "[]"',
                    'EPIC-001: Added default "depends_on" with value "[]"',
                    'T-001: Added default "depends_on" with value "[]"',
                ],
            )

            task_text = (root_path / ".tickets" / "tasks" / "TASK-001.yaml").read_text(encoding="utf-8")
            epic_text = (root_path / ".tickets" / "epics" / "EPIC-001.yaml").read_text(encoding="utf-8")
            ticket_text = (root_path / ".tickets" / "tickets" / "T-001.yaml").read_text(encoding="utf-8")

            self.assertIn("depends_on: []", task_text)
            self.assertIn("depends_on: []", epic_text)
            self.assertIn("depends_on: []", ticket_text)

    def test_upgrade_command_noop_for_existing_depends_on(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task_with_depends_on(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, ticket_id="T-001", depends_on=[])

            standard_output = StringIO()
            standard_error = StringIO()
            exit_code = run_cli(
                ["upgrade"],
                standard_output=standard_output,
                standard_error=standard_error,
                root_path=root_path,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(standard_output.getvalue(), "")
            self.assertEqual(standard_error.getvalue(), "")


def write_sample_task(root_path: Path) -> None:
    tasks_directory = root_path / ".tickets" / "tasks"
    tasks_directory.mkdir(parents=True, exist_ok=True)
    task_path = tasks_directory / "TASK-001.yaml"
    task_path.write_text(SAMPLE_TASK_YAML, encoding="utf-8")


def write_sample_task_with_depends_on(root_path: Path) -> None:
    tasks_directory = root_path / ".tickets" / "tasks"
    tasks_directory.mkdir(parents=True, exist_ok=True)
    task_path = tasks_directory / "TASK-001.yaml"
    task_path.write_text(SAMPLE_TASK_YAML_WITH_DEPENDS_ON, encoding="utf-8")


def write_sample_epic(root_path: Path) -> None:
    epics_directory = root_path / ".tickets" / "epics"
    epics_directory.mkdir(parents=True, exist_ok=True)
    epic_path = epics_directory / "EPIC-001.yaml"
    epic_path.write_text(SAMPLE_EPIC_YAML, encoding="utf-8")


def write_sample_epic_without_depends_on(root_path: Path) -> None:
    epics_directory = root_path / ".tickets" / "epics"
    epics_directory.mkdir(parents=True, exist_ok=True)
    epic_path = epics_directory / "EPIC-001.yaml"
    epic_path.write_text(
        "\n".join(
            [
                "id: EPIC-001",
                "task: TASK-001",
                "title: Example epic",
                "status: open",
                "description: Epic description",
                "acceptance_criteria:",
                "    - criterion one",
            ]
        ),
        encoding="utf-8",
    )


def write_sample_ticket(
    root_path: Path,
    ticket_id: str,
    status: str = "open",
    depends_on: list[str] | None = None,
) -> None:
    dependency_ids = depends_on if depends_on is not None else []
    tickets_directory = root_path / ".tickets" / "tickets"
    tickets_directory.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_directory / f"{ticket_id}.yaml"
    ticket_path.write_text(
        SAMPLE_TICKET_TEMPLATE.format(
            ticket_id=ticket_id,
            title=f"Ticket {ticket_id}",
            status=status,
            depends_on=dependency_ids,
        ),
        encoding="utf-8",
    )


def write_sample_ticket_without_depends_on(root_path: Path, ticket_id: str) -> None:
    tickets_directory = root_path / ".tickets" / "tickets"
    tickets_directory.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_directory / f"{ticket_id}.yaml"
    ticket_path.write_text(
        "\n".join(
            [
                f"id: {ticket_id}",
                "epic: EPIC-001",
                f"title: Ticket {ticket_id}",
                "status: open",
                "description: Ticket description",
                "acceptance_criteria:",
                "    - criterion one",
                "out_of_scope:",
                "    - not included",
            ]
        ),
        encoding="utf-8",
    )


def write_raw_ticket(root_path: Path, ticket_yaml: str) -> None:
    tickets_directory = root_path / ".tickets" / "tickets"
    tickets_directory.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_directory / "T-001.yaml"
    ticket_path.write_text(ticket_yaml, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
