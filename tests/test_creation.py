from pathlib import Path
import tempfile
import unittest

from tickets.creation import create_task_from_arguments, import_plan_from_file
from tickets.repository import RepositoryError, TicketRepository

SAMPLE_EXISTING_TASK_YAML = """
id: TASK-001
title: Existing task
status: open
depends_on: []
description: Existing task description
acceptance_criteria:
    - existing criterion
""".strip()

VALID_PLAN_YAML = """
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
    title: Imported ticket 1
    status: open
    depends_on: []
    description: Ticket 1 description
    acceptance_criteria:
      - ticket criterion one
    out_of_scope:
      - not included

  - id: T-002
    epic: EPIC-001
    title: Imported ticket 2
    status: open
    depends_on:
      - T-001
    description: Ticket 2 description
    acceptance_criteria:
      - ticket criterion two
    out_of_scope:
      - not included
""".strip()

INVALID_PLAN_MISSING_TASK_REFERENCE_YAML = """
epic:
  id: EPIC-001
  task: TASK-999
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
    description: Ticket description
    acceptance_criteria:
      - ticket criterion
    out_of_scope:
      - not included
""".strip()

INVALID_PLAN_MISSING_DEPENDENCY_YAML = """
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
    depends_on:
      - T-999
    description: Ticket description
    acceptance_criteria:
      - ticket criterion
    out_of_scope:
      - not included
""".strip()

INVALID_PLAN_DUPLICATE_TICKET_IDS_YAML = """
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
    title: Imported ticket 1
    status: open
    depends_on: []
    description: Ticket 1 description
    acceptance_criteria:
      - ticket criterion one
    out_of_scope:
      - not included

  - id: T-001
    epic: EPIC-001
    title: Imported ticket 2
    status: open
    depends_on: []
    description: Ticket 2 description
    acceptance_criteria:
      - ticket criterion two
    out_of_scope:
      - not included
""".strip()

INVALID_PLAN_STRUCTURE_YAML = """
tickets:
  - id: T-001
""".strip()

INVALID_PLAN_STATUS_YAML = """
epic:
  id: EPIC-001
  task: TASK-001
  title: Imported epic
  status: invalid
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
    description: Ticket description
    acceptance_criteria:
      - ticket criterion
    out_of_scope:
      - not included
""".strip()


class CreationTests(unittest.TestCase):
    def test_create_task_generates_valid_task_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)

            created_task = create_task_from_arguments(
                root_path=root_path,
                task_id=None,
                title="New task title",
                description="New task description",
                acceptance_criteria=["criterion one", "criterion two"],
            )

            self.assertEqual(created_task.id, "TASK-002")

            repository = TicketRepository(root_path)
            tasks, epics, tickets = repository.load_all()
            self.assertEqual(len(tasks), 2)
            self.assertEqual(len(epics), 0)
            self.assertEqual(len(tickets), 0)
            loaded_task = [task for task in tasks if task.id == "TASK-002"][0]
            self.assertEqual(loaded_task.title, "New task title")
            self.assertEqual(loaded_task.status, "open")

    def test_import_plan_with_valid_yaml_creates_epic_and_ticket_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, VALID_PLAN_YAML)

            imported_epic, imported_tickets = import_plan_from_file(root_path, plan_file_path)

            self.assertEqual(imported_epic.id, "EPIC-001")
            self.assertEqual(len(imported_tickets), 2)

            repository = TicketRepository(root_path)
            tasks, epics, tickets = repository.load_all()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(len(epics), 1)
            self.assertEqual(len(tickets), 2)
            self.assertEqual(epics[0].id, "EPIC-001")
            self.assertEqual(tickets[0].id, "T-001")
            self.assertEqual(tickets[1].id, "T-002")

    def test_import_plan_rejects_missing_task_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, INVALID_PLAN_MISSING_TASK_REFERENCE_YAML)

            with self.assertRaises(RepositoryError) as error_context:
                import_plan_from_file(root_path, plan_file_path)

            self.assertIn("missing task", str(error_context.exception))
            self.assertIn("TASK-999", str(error_context.exception))

    def test_import_plan_rejects_missing_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, INVALID_PLAN_MISSING_DEPENDENCY_YAML)

            with self.assertRaises(RepositoryError) as error_context:
                import_plan_from_file(root_path, plan_file_path)

            self.assertIn("missing ticket", str(error_context.exception))
            self.assertIn("T-999", str(error_context.exception))

    def test_import_plan_rejects_duplicate_ticket_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, INVALID_PLAN_DUPLICATE_TICKET_IDS_YAML)

            with self.assertRaises(RepositoryError) as error_context:
                import_plan_from_file(root_path, plan_file_path)

            self.assertIn("Duplicate ticket id values", str(error_context.exception))
            self.assertIn("T-001", str(error_context.exception))

    def test_import_plan_rejects_invalid_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, INVALID_PLAN_STRUCTURE_YAML)

            with self.assertRaises(RepositoryError) as error_context:
                import_plan_from_file(root_path, plan_file_path)

            self.assertIn("missing required keys", str(error_context.exception))
            self.assertIn("epic", str(error_context.exception))

    def test_import_plan_runs_standard_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_existing_task(root_path)
            plan_file_path = write_plan_file(root_path, INVALID_PLAN_STATUS_YAML)

            with self.assertRaises(RepositoryError) as error_context:
                import_plan_from_file(root_path, plan_file_path)

            self.assertIn("Invalid status", str(error_context.exception))


def write_existing_task(root_path: Path) -> None:
    task_path = root_path / ".tickets" / "tasks" / "TASK-001.yaml"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(SAMPLE_EXISTING_TASK_YAML, encoding="utf-8")


def write_plan_file(root_path: Path, plan_yaml: str) -> Path:
    plan_file_path = root_path / "plan.yaml"
    plan_file_path.write_text(plan_yaml, encoding="utf-8")
    return plan_file_path


if __name__ == "__main__":
    unittest.main()
