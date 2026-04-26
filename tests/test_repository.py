from pathlib import Path
import tempfile
import unittest

from tickets.models import Epic, Task, Ticket
from tickets.repository import RepositoryError, TicketRepository


INCOMPLETE_TASK_YAML = """
id: TASK-001
title: Example task
status: open
description: Missing acceptance criteria field
""".strip()

INVALID_ACCEPTANCE_CRITERIA_TASK_YAML = """
id: TASK-001
title: Example task
status: open
description: Example
acceptance_criteria: not-a-list
""".strip()

SAMPLE_TASK_YAML_TEMPLATE = """
id: {task_id}
title: Sample task
status: open
description: Example task description
acceptance_criteria:
    - criterion one
    - criterion two
""".strip()

SAMPLE_EPIC_YAML_TEMPLATE = """
id: {epic_id}
task: {task_id}
title: Sample epic
status: open
description: Example epic description
acceptance_criteria:
    - criterion one
""".strip()

SAMPLE_TICKET_YAML_TEMPLATE = """
id: {ticket_id}
epic: {epic_id}
title: Sample ticket
status: open
depends_on: []
description: Example ticket description
acceptance_criteria:
    - criterion one
out_of_scope:
    - criterion not included
""".strip()


class TicketRepositoryTests(unittest.TestCase):
    def test_load_all_valid_yaml_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path)

            repository = TicketRepository(root_path)
            tasks, epics, tickets = repository.load_all()

            self.assertEqual(len(tasks), 1)
            self.assertEqual(len(epics), 1)
            self.assertEqual(len(tickets), 1)

            self.assertIsInstance(tasks[0], Task)
            self.assertIsInstance(epics[0], Epic)
            self.assertIsInstance(tickets[0], Ticket)

            self.assertEqual(tasks[0].id, "TASK-001")
            self.assertEqual(epics[0].id, "EPIC-001")
            self.assertEqual(tickets[0].id, "T-001")

    def test_missing_ticket_directories_are_handled_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            repository = TicketRepository(root_path)

            tasks, epics, tickets = repository.load_all()

            self.assertEqual(tasks, [])
            self.assertEqual(epics, [])
            self.assertEqual(tickets, [])

    def test_invalid_yaml_raises_repository_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            tasks_directory = root_path / ".tickets" / "tasks"
            tasks_directory.mkdir(parents=True, exist_ok=True)
            invalid_task_path = tasks_directory / "TASK-001.yaml"
            invalid_task_path.write_text("id: [\n", encoding="utf-8")

            repository = TicketRepository(root_path)

            with self.assertRaises(RepositoryError) as error_context:
                repository.load_tasks()

            self.assertIn("Invalid YAML", str(error_context.exception))
            self.assertIn("TASK-001.yaml", str(error_context.exception))

    def test_missing_required_fields_raise_repository_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            tasks_directory = root_path / ".tickets" / "tasks"
            tasks_directory.mkdir(parents=True, exist_ok=True)
            incomplete_task_path = tasks_directory / "TASK-001.yaml"
            incomplete_task_path.write_text(
                INCOMPLETE_TASK_YAML,
                encoding="utf-8",
            )

            repository = TicketRepository(root_path)

            with self.assertRaises(RepositoryError) as error_context:
                repository.load_tasks()

            self.assertIn("Missing required fields", str(error_context.exception))
            self.assertIn("acceptance_criteria", str(error_context.exception))

    def test_duplicate_ticket_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, file_name="T-001-a.yaml", ticket_id="T-001")
            write_sample_ticket(root_path, file_name="T-001-b.yaml", ticket_id="T-001")

            repository = TicketRepository(root_path)

            with self.assertRaises(RepositoryError) as error_context:
                repository.load_tickets()

            self.assertIn("Duplicate ticket id values", str(error_context.exception))
            self.assertIn("T-001", str(error_context.exception))

    def test_non_list_acceptance_criteria_raises_repository_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            tasks_directory = root_path / ".tickets" / "tasks"
            tasks_directory.mkdir(parents=True, exist_ok=True)
            invalid_task_path = tasks_directory / "TASK-001.yaml"
            invalid_task_path.write_text(
                INVALID_ACCEPTANCE_CRITERIA_TASK_YAML,
                encoding="utf-8",
            )

            repository = TicketRepository(root_path)

            with self.assertRaises(RepositoryError) as error_context:
                repository.load_tasks()

            self.assertIn("must be a list", str(error_context.exception))

    def test_load_all_validates_cross_entity_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_task(root_path)
            write_sample_epic(root_path)
            write_sample_ticket(root_path, epic_id="EPIC-999")

            repository = TicketRepository(root_path)

            with self.assertRaises(RepositoryError) as error_context:
                repository.load_all()

            self.assertIn("missing epic", str(error_context.exception))
            self.assertIn("EPIC-999", str(error_context.exception))


def write_sample_task(root_path: Path, task_id: str = "TASK-001") -> None:
    tasks_directory = root_path / ".tickets" / "tasks"
    tasks_directory.mkdir(parents=True, exist_ok=True)
    task_path = tasks_directory / f"{task_id}.yaml"
    task_path.write_text(
        SAMPLE_TASK_YAML_TEMPLATE.format(task_id=task_id),
        encoding="utf-8",
    )


def write_sample_epic(root_path: Path, epic_id: str = "EPIC-001", task_id: str = "TASK-001") -> None:
    epics_directory = root_path / ".tickets" / "epics"
    epics_directory.mkdir(parents=True, exist_ok=True)
    epic_path = epics_directory / f"{epic_id}.yaml"
    epic_path.write_text(
        SAMPLE_EPIC_YAML_TEMPLATE.format(epic_id=epic_id, task_id=task_id),
        encoding="utf-8",
    )


def write_sample_ticket(
    root_path: Path,
    file_name: str = "T-001.yaml",
    ticket_id: str = "T-001",
    epic_id: str = "EPIC-001",
) -> None:
    tickets_directory = root_path / ".tickets" / "tickets"
    tickets_directory.mkdir(parents=True, exist_ok=True)
    ticket_path = tickets_directory / file_name
    ticket_path.write_text(
        SAMPLE_TICKET_YAML_TEMPLATE.format(ticket_id=ticket_id, epic_id=epic_id),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
