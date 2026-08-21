from dataclasses import replace

from tickets.models import Epic, Task, Ticket
from tickets.statuses import BLOCKED_STATUS, CLOSED_STATUS, IN_PROGRESS_STATUS, OPEN_STATUS


def compute_ticket_effective_status(ticket: Ticket, tickets_by_id: dict[str, Ticket]) -> str:
    if ticket.status == CLOSED_STATUS:
        return CLOSED_STATUS
    if ticket.status == BLOCKED_STATUS:
        return BLOCKED_STATUS

    for dependency_id in ticket.depends_on:
        dependency_ticket = tickets_by_id.get(dependency_id)
        if dependency_ticket is None:
            return BLOCKED_STATUS
        if dependency_ticket.status != CLOSED_STATUS:
            return BLOCKED_STATUS

    return ticket.status


def compute_task_underlying_status(task: Task, tickets_for_task: list[Ticket]) -> str:
    if not tickets_for_task:
        return OPEN_STATUS

    if all(ticket.status == CLOSED_STATUS for ticket in tickets_for_task):
        return CLOSED_STATUS

    if any(ticket.status in {IN_PROGRESS_STATUS, CLOSED_STATUS} for ticket in tickets_for_task):
        return IN_PROGRESS_STATUS

    return OPEN_STATUS


def compute_task_effective_status(
    task: Task,
    task_underlying_status: str,
    task_underlying_status_by_id: dict[str, str],
) -> str:
    if task_underlying_status == CLOSED_STATUS:
        return CLOSED_STATUS

    for dependency_id in task.depends_on:
        dependency_status = task_underlying_status_by_id.get(dependency_id)
        if dependency_status is None:
            return BLOCKED_STATUS
        if dependency_status != CLOSED_STATUS:
            return BLOCKED_STATUS

    return task_underlying_status


def compute_epic_underlying_status(epic: Epic, tasks_for_epic: list[Task]) -> str:
    if not tasks_for_epic:
        return OPEN_STATUS

    if all(task.status == CLOSED_STATUS for task in tasks_for_epic):
        return CLOSED_STATUS

    if any(task.status in {IN_PROGRESS_STATUS, CLOSED_STATUS} for task in tasks_for_epic):
        return IN_PROGRESS_STATUS

    return OPEN_STATUS


def compute_epic_effective_status(
    epic: Epic,
    epic_underlying_status: str,
    epic_underlying_status_by_id: dict[str, str],
) -> str:
    if epic_underlying_status == CLOSED_STATUS:
        return CLOSED_STATUS

    for dependency_id in epic.depends_on:
        dependency_status = epic_underlying_status_by_id.get(dependency_id)
        if dependency_status is None:
            return BLOCKED_STATUS
        if dependency_status != CLOSED_STATUS:
            return BLOCKED_STATUS

    return epic_underlying_status


def build_effective_entities(
    tasks: list[Task],
    epics: list[Epic],
    tickets: list[Ticket],
) -> tuple[list[Task], list[Epic], list[Ticket]]:
    tickets_by_id = {ticket.id: ticket for ticket in tickets}
    effective_tickets = [
        replace(ticket, status=compute_ticket_effective_status(ticket, tickets_by_id))
        for ticket in tickets
    ]

    epics_by_id = {epic.id: epic for epic in epics}
    tickets_by_task: dict[str, list[Ticket]] = {}
    for ticket in tickets:
        epic = epics_by_id.get(ticket.epic)
        if epic is None:
            continue
        if epic.task not in tickets_by_task:
            tickets_by_task[epic.task] = []
        tickets_by_task[epic.task].append(ticket)

    task_underlying_by_id = {
        task.id: compute_task_underlying_status(task, tickets_by_task.get(task.id, []))
        for task in tasks
    }
    underlying_tasks = [
        replace(task, status=task_underlying_by_id[task.id])
        for task in tasks
    ]

    effective_tasks = [
        replace(
            task,
            status=compute_task_effective_status(task, task_underlying_by_id[task.id], task_underlying_by_id),
        )
        for task in tasks
    ]

    underlying_tasks_by_id = {task.id: task for task in underlying_tasks}
    tasks_by_epic: dict[str, list[Task]] = {}
    for epic in epics:
        task = underlying_tasks_by_id.get(epic.task)
        if task is None:
            continue
        if epic.id not in tasks_by_epic:
            tasks_by_epic[epic.id] = []
        tasks_by_epic[epic.id].append(task)

    epic_underlying_by_id = {
        epic.id: compute_epic_underlying_status(epic, tasks_by_epic.get(epic.id, []))
        for epic in epics
    }
    effective_epics = [
        replace(
            epic,
            status=compute_epic_effective_status(epic, epic_underlying_by_id[epic.id], epic_underlying_by_id),
        )
        for epic in epics
    ]

    return effective_tasks, effective_epics, effective_tickets


def build_underlying_entities(
    tasks: list[Task],
    epics: list[Epic],
    tickets: list[Ticket],
) -> tuple[list[Task], list[Epic]]:
    epics_by_id = {epic.id: epic for epic in epics}
    tickets_by_task: dict[str, list[Ticket]] = {}
    for ticket in tickets:
        epic = epics_by_id.get(ticket.epic)
        if epic is None:
            continue
        if epic.task not in tickets_by_task:
            tickets_by_task[epic.task] = []
        tickets_by_task[epic.task].append(ticket)

    underlying_tasks = [
        replace(task, status=compute_task_underlying_status(task, tickets_by_task.get(task.id, [])))
        for task in tasks
    ]

    underlying_tasks_by_id = {task.id: task for task in underlying_tasks}
    tasks_by_epic: dict[str, list[Task]] = {}
    for epic in epics:
        task = underlying_tasks_by_id.get(epic.task)
        if task is None:
            continue
        if epic.id not in tasks_by_epic:
            tasks_by_epic[epic.id] = []
        tasks_by_epic[epic.id].append(task)

    underlying_epics = [
        replace(epic, status=compute_epic_underlying_status(epic, tasks_by_epic.get(epic.id, [])))
        for epic in epics
    ]

    return underlying_tasks, underlying_epics