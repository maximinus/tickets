import unittest

from tickets.models import Epic, Task, Ticket
from tickets.validation import ValidationError, validate_repository_data


def make_task(task_id: str = "TASK-001", status: str = "open") -> Task:
    return Task(
        id=task_id,
        title="Task title",
        status=status,
        description="Task description",
        acceptance_criteria=["criterion"],
    )


def make_epic(epic_id: str = "EPIC-001", task_id: str = "TASK-001", status: str = "open") -> Epic:
    return Epic(
        id=epic_id,
        task=task_id,
        title="Epic title",
        status=status,
        description="Epic description",
        acceptance_criteria=["criterion"],
    )


def make_ticket(
    ticket_id: str = "T-001",
    epic_id: str = "EPIC-001",
    status: str = "open",
    depends_on: list[str] | None = None,
) -> Ticket:
    if depends_on is None:
        depends_on = []

    return Ticket(
        id=ticket_id,
        epic=epic_id,
        title="Ticket title",
        status=status,
        depends_on=depends_on,
        description="Ticket description",
        acceptance_criteria=["criterion"],
        out_of_scope=["not included"],
    )


class ValidationTests(unittest.TestCase):
    def test_reject_invalid_status_values(self) -> None:
        tasks = [make_task(status="planned")]
        epics = [make_epic()]
        tickets = [make_ticket()]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("Invalid status", str(error_context.exception))
        self.assertIn("planned", str(error_context.exception))

    def test_reject_epic_referencing_missing_task(self) -> None:
        tasks = [make_task(task_id="TASK-001")]
        epics = [make_epic(epic_id="EPIC-001", task_id="TASK-999")]
        tickets = [make_ticket(epic_id="EPIC-001")]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("missing task", str(error_context.exception))
        self.assertIn("TASK-999", str(error_context.exception))

    def test_reject_ticket_referencing_missing_epic(self) -> None:
        tasks = [make_task()]
        epics = [make_epic(epic_id="EPIC-001")]
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-999")]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("missing epic", str(error_context.exception))
        self.assertIn("EPIC-999", str(error_context.exception))

    def test_reject_ticket_dependency_on_missing_ticket(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-001", depends_on=["T-999"])]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("missing ticket", str(error_context.exception))
        self.assertIn("T-999", str(error_context.exception))

    def test_detect_simple_ticket_dependency_cycle(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [
            make_ticket(ticket_id="T-001", depends_on=["T-002"]),
            make_ticket(ticket_id="T-002", depends_on=["T-001"]),
        ]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("Cycle detected", str(error_context.exception))

    def test_detect_complex_ticket_dependency_cycle(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [
            make_ticket(ticket_id="T-001", depends_on=["T-002"]),
            make_ticket(ticket_id="T-002", depends_on=["T-003"]),
            make_ticket(ticket_id="T-003", depends_on=["T-001"]),
        ]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("Cycle detected", str(error_context.exception))

    def test_detect_duplicate_ids_across_entities(self) -> None:
        tasks = [make_task(task_id="SHARED-001")]
        epics = [make_epic(epic_id="SHARED-001", task_id="SHARED-001")]
        tickets = [make_ticket(ticket_id="T-001")]

        with self.assertRaises(ValidationError) as error_context:
            validate_repository_data(tasks, epics, tickets)

        self.assertIn("Duplicate IDs", str(error_context.exception))
        self.assertIn("SHARED-001", str(error_context.exception))

    def test_accept_valid_data_structures(self) -> None:
        tasks = [make_task()]
        epics = [make_epic(task_id="TASK-001")]
        tickets = [
            make_ticket(ticket_id="T-001", depends_on=[]),
            make_ticket(ticket_id="T-002", depends_on=["T-001"]),
        ]

        validate_repository_data(tasks, epics, tickets)


if __name__ == "__main__":
    unittest.main()
