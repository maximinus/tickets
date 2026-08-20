import unittest

from tickets.models import Ticket
from tickets.sequencing import find_next_actionable_ticket


def make_ticket(
    ticket_id: str,
    status: str = "open",
    depends_on: list[str] | None = None,
) -> Ticket:
    dependency_ids = depends_on if depends_on is not None else []
    return Ticket(
        id=ticket_id,
        epic="EPIC-001",
        title="Ticket title",
        status=status,
        depends_on=dependency_ids,
        description="Ticket description",
        acceptance_criteria=["criterion"],
        out_of_scope=["not included"],
    )


class SequencingTests(unittest.TestCase):
    def test_find_next_ticket_when_no_dependencies_exist(self) -> None:
        tickets = [
            make_ticket("T-001", status="open"),
            make_ticket("T-002", status="open"),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-001")

    def test_skip_tickets_with_open_dependencies(self) -> None:
        tickets = [
            make_ticket("T-001", status="open"),
            make_ticket("T-002", status="open", depends_on=["T-001"]),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-001")

    def test_skip_blocked_tickets(self) -> None:
        tickets = [
            make_ticket("T-001", status="blocked"),
            make_ticket("T-002", status="open"),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-002")

    def test_skip_in_progress_tickets(self) -> None:
        tickets = [
            make_ticket("T-001", status="in_progress"),
            make_ticket("T-002", status="open"),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-002")

    def test_skip_closed_tickets(self) -> None:
        tickets = [
            make_ticket("T-001", status="closed"),
            make_ticket("T-002", status="open"),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-002")

    def test_return_none_when_no_tickets_are_actionable(self) -> None:
        tickets = [
            make_ticket("T-001", status="closed"),
            make_ticket("T-002", status="blocked"),
            make_ticket("T-003", status="in_progress"),
        ]

        next_ticket = find_next_actionable_ticket(tickets)

        self.assertIsNone(next_ticket)

    def test_select_deterministically_when_multiple_are_actionable_by_epic_task_ticket_number(self) -> None:
        tickets = [
            Ticket(
                id="T-010",
                epic="EPIC-010",
                title="Ticket title",
                status="open",
                depends_on=[],
                description="Ticket description",
                acceptance_criteria=["criterion"],
                out_of_scope=["not included"],
            ),
            Ticket(
                id="T-002",
                epic="EPIC-002",
                title="Ticket title",
                status="open",
                depends_on=[],
                description="Ticket description",
                acceptance_criteria=["criterion"],
                out_of_scope=["not included"],
            ),
            Ticket(
                id="T-100",
                epic="EPIC-001",
                title="Ticket title",
                status="open",
                depends_on=[],
                description="Ticket description",
                acceptance_criteria=["criterion"],
                out_of_scope=["not included"],
            ),
        ]

        next_ticket = find_next_actionable_ticket(
            tickets,
            epics=[
                type("Epic", (), {"id": "EPIC-001", "task": "TASK-001"})(),
                type("Epic", (), {"id": "EPIC-002", "task": "TASK-001"})(),
                type("Epic", (), {"id": "EPIC-010", "task": "TASK-001"})(),
            ],
            tasks=[type("Task", (), {"id": "TASK-001"})()],
        )

        self.assertIsNotNone(next_ticket)
        self.assertEqual(next_ticket.id, "T-100")

    def test_handle_empty_ticket_list(self) -> None:
        next_ticket = find_next_actionable_ticket([])

        self.assertIsNone(next_ticket)


if __name__ == "__main__":
    unittest.main()
