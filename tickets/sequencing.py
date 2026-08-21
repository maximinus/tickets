import re

from tickets.models import Epic, Task, Ticket
from tickets.status_engine import compute_ticket_effective_status
from tickets.statuses import OPEN_STATUS


def find_next_actionable_ticket(
    tickets: list[Ticket],
    epics: list[Epic] | None = None,
    tasks: list[Task] | None = None,
) -> Ticket | None:
    tickets_by_id = {ticket.id: ticket for ticket in tickets}
    actionable_tickets = [ticket for ticket in tickets if is_ticket_actionable(ticket, tickets_by_id)]

    if not actionable_tickets:
        return None

    return min(actionable_tickets, key=lambda ticket: sort_ticket_for_selection(ticket, epics, tasks))


def sort_ticket_for_selection(
    ticket: Ticket,
    epics: list[Epic] | None = None,
    tasks: list[Task] | None = None,
) -> tuple[int, int, int]:
    epic_number = extract_numeric_suffix(ticket.epic)
    task_number = epic_number

    if epics is not None:
        epics_by_id = {epic.id: epic for epic in epics}
        epic = epics_by_id.get(ticket.epic)
        if epic is not None:
            epic_number = extract_numeric_suffix(epic.id)
            if tasks is not None:
                tasks_by_id = {task.id: task for task in tasks}
                task = tasks_by_id.get(epic.task)
                if task is not None:
                    task_number = extract_numeric_suffix(task.id)

    ticket_number = extract_numeric_suffix(ticket.id)
    return (epic_number, task_number, ticket_number)


def extract_numeric_suffix(value: str) -> int:
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match is not None else 10**9


def is_ticket_actionable(ticket: Ticket, tickets_by_id: dict[str, Ticket]) -> bool:
    return compute_ticket_effective_status(ticket, tickets_by_id) == OPEN_STATUS
