from io import StringIO
from pathlib import Path
import hashlib
import shutil
import tempfile
import unittest

import yaml

from tickets.cli import run_cli
from tickets.web import HTTP_OK, build_web_response

SAMPLE_PLAN_YAML = """
epic:
  id: EPIC-001
  task: TASK-001
  title: Build the minimal ticket system
  status: open
  description: |
    Build loading, validation, sequencing, prompt generation, and web inspection.
  acceptance_criteria:
    - Core workflow can run from CLI

tickets:
  - id: T-001
    epic: EPIC-001
    title: Implement first step
    status: open
    depends_on: []
    description: |
      Complete first step.
    acceptance_criteria:
      - First step done
    out_of_scope:
      - Unrelated work

  - id: T-002
    epic: EPIC-001
    title: Implement second step
    status: open
    depends_on:
      - T-001
    description: |
      Complete second step.
    acceptance_criteria:
      - Second step done
    out_of_scope:
      - Unrelated work
""".strip()


class IntegrationTests(unittest.TestCase):
    def test_end_to_end_cli_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            plan_file_path = root_path / "plan.yaml"
            plan_file_path.write_text(SAMPLE_PLAN_YAML, encoding="utf-8")

            create_exit, create_output, create_error = run_command(
                root_path,
                [
                    "create-task",
                    "--task-id",
                    "TASK-001",
                    "--title",
                    "Example integration task",
                    "--description",
                    "Integration workflow task",
                    "--acceptance-criterion",
                    "Workflow can be completed",
                ],
            )
            self.assertEqual(create_exit, 0)
            self.assertIn("Created task TASK-001", create_output)
            self.assertEqual(create_error, "")

            import_exit, import_output, import_error = run_command(
                root_path,
                ["import-plan", "plan.yaml"],
            )
            self.assertEqual(import_exit, 0)
            self.assertIn("Imported epic EPIC-001 and 2 tickets.", import_output)
            self.assertEqual(import_error, "")

            validate_exit, validate_output, validate_error = run_command(root_path, ["validate"])
            self.assertEqual(validate_exit, 0)
            self.assertIn("Validation passed.", validate_output)
            self.assertEqual(validate_error, "")

            first_prompt_exit, first_prompt_output, first_prompt_error = run_command(root_path, ["prompt-next"])
            self.assertEqual(first_prompt_exit, 0)
            self.assertIn("id: T-001", first_prompt_output)
            self.assertEqual(first_prompt_error, "")

            set_ticket_status(root_path, "T-001", "closed")

            second_prompt_exit, second_prompt_output, second_prompt_error = run_command(root_path, ["prompt-next"])
            self.assertEqual(second_prompt_exit, 0)
            self.assertIn("id: T-002", second_prompt_output)
            self.assertEqual(second_prompt_error, "")

            set_ticket_status(root_path, "T-002", "closed")

            final_prompt_exit, final_prompt_output, final_prompt_error = run_command(root_path, ["prompt-next"])
            self.assertEqual(final_prompt_exit, 0)
            self.assertIn("No actionable tickets found.", final_prompt_output)
            self.assertEqual(final_prompt_error, "")

    def test_web_dashboard_updates_across_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            (root_path / ".tickets" / "tasks").mkdir(parents=True, exist_ok=True)
            (root_path / ".tickets" / "tasks" / "TASK-001.yaml").write_text(
                """
id: TASK-001
title: Web integration task
status: open
description: Task description
acceptance_criteria:
  - One criterion
""".strip(),
                encoding="utf-8",
            )
            plan_file_path = root_path / "plan.yaml"
            plan_file_path.write_text(SAMPLE_PLAN_YAML, encoding="utf-8")
            run_command(root_path, ["import-plan", str(plan_file_path)])

            first_dashboard = build_web_response(root_path, "/")
            self.assertEqual(first_dashboard.status_code, HTTP_OK)
            self.assertIn("Next Actionable Ticket", first_dashboard.html_body)
            self.assertIn("T-001: Implement first step", first_dashboard.html_body)

            set_ticket_status(root_path, "T-001", "closed")

            second_dashboard = build_web_response(root_path, "/")
            self.assertEqual(second_dashboard.status_code, HTTP_OK)
            self.assertIn("T-002: Implement second step", second_dashboard.html_body)

            set_ticket_status(root_path, "T-002", "closed")

            final_dashboard = build_web_response(root_path, "/")
            self.assertEqual(final_dashboard.status_code, HTTP_OK)
            self.assertIn("All tickets are complete or waiting on dependencies.", final_dashboard.html_body)

    def test_complex_fixture_workflow_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            fixture_source_path = Path("docs/fixtures/complex-text-editor/.tickets")
            fixture_target_path = root_path / ".tickets"
            shutil.copytree(fixture_source_path, fixture_target_path)

            validate_exit, validate_output, validate_error = run_command(root_path, ["validate"])
            self.assertEqual(validate_exit, 0)
            self.assertIn("Validation passed.", validate_output)
            self.assertEqual(validate_error, "")

            next_exit, next_output, next_error = run_command(root_path, ["next"])
            self.assertEqual(next_exit, 0)
            self.assertIn("T-121: Implement open and save file commands", next_output)
            self.assertEqual(next_error, "")

            dashboard_response = build_web_response(root_path, "/")
            self.assertEqual(dashboard_response.status_code, HTTP_OK)
            self.assertIn("T-121: Implement open and save file commands", dashboard_response.html_body)

    def test_create_and_import_do_not_rewrite_unrelated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            task_directory_path = root_path / ".tickets" / "tasks"
            task_directory_path.mkdir(parents=True, exist_ok=True)
            existing_task_path = task_directory_path / "TASK-050.yaml"
            existing_task_content = """
id: TASK-050
title: Existing task
status: open
description: Existing task description
acceptance_criteria:
  - Existing criterion
""".strip()
            existing_task_path.write_text(existing_task_content, encoding="utf-8")
            before_hash = hash_file(existing_task_path)

            create_exit, _, _ = run_command(
                root_path,
                [
                    "create-task",
                    "--task-id",
                    "TASK-051",
                    "--title",
                    "New task",
                    "--description",
                    "New description",
                    "--acceptance-criterion",
                    "Criterion",
                ],
            )
            self.assertEqual(create_exit, 0)

            plan_file_path = root_path / "plan.yaml"
            plan_file_path.write_text(
                SAMPLE_PLAN_YAML.replace("TASK-001", "TASK-050").replace("EPIC-001", "EPIC-050"),
                encoding="utf-8",
            )
            import_exit, _, _ = run_command(root_path, ["import-plan", "plan.yaml"])
            self.assertEqual(import_exit, 0)

            after_hash = hash_file(existing_task_path)
            self.assertEqual(before_hash, after_hash)


def run_command(root_path: Path, arguments: list[str]) -> tuple[int, str, str]:
    standard_output = StringIO()
    standard_error = StringIO()
    exit_code = run_cli(arguments, standard_output=standard_output, standard_error=standard_error, root_path=root_path)
    return exit_code, standard_output.getvalue(), standard_error.getvalue()


def set_ticket_status(root_path: Path, ticket_id: str, new_status: str) -> None:
    ticket_path = root_path / ".tickets" / "tickets" / f"{ticket_id}.yaml"
    ticket_data = yaml.safe_load(ticket_path.read_text(encoding="utf-8"))
    ticket_data["status"] = new_status
    ticket_path.write_text(yaml.safe_dump(ticket_data, sort_keys=False), encoding="utf-8")


def hash_file(file_path: Path) -> str:
    file_bytes = file_path.read_bytes()
    return hashlib.sha256(file_bytes).hexdigest()


if __name__ == "__main__":
    unittest.main()
