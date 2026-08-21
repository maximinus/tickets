from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from tickets.models import Epic, Task, Ticket
from tickets.repository import RepositoryError, TicketRepository
from tickets.status_engine import build_underlying_entities
from tickets.statuses import BLOCKED_STATUS, CLOSED_STATUS, TICKET_ALLOWED_STATUSES

TASKS_DIR_NAME = "tasks"
EPICS_DIR_NAME = "epics"
TICKETS_DIR_NAME = "tickets"
TICKETS_ROOT_DIR_NAME = ".tickets"


def set_ticket_status(root_path: Path, ticket_id: str, new_status: str) -> list[str]:
    if new_status not in TICKET_ALLOWED_STATUSES:
        allowed_status_values = ", ".join(sorted(TICKET_ALLOWED_STATUSES))
        raise RepositoryError(f"Invalid status '{new_status}'. Allowed values: {allowed_status_values}")

    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()

    tasks_by_id = {task.id: task for task in tasks}
    epics_by_id = {epic.id: epic for epic in epics}
    tickets_by_id = {ticket.id: ticket for ticket in tickets}

    if ticket_id in tasks_by_id:
        raise RepositoryError(f"Status updates are only supported for tickets. Received task id: {ticket_id}")
    if ticket_id in epics_by_id:
        raise RepositoryError(f"Status updates are only supported for tickets. Received epic id: {ticket_id}")

    ticket = tickets_by_id.get(ticket_id)
    if ticket is None:
        raise RepositoryError(f"Ticket not found: {ticket_id}")

    if new_status != BLOCKED_STATUS:
        for dependency_id in ticket.depends_on:
            dependency_ticket = tickets_by_id.get(dependency_id)
            if dependency_ticket is None or dependency_ticket.status != CLOSED_STATUS:
                raise RepositoryError(
                    f"Cannot set ticket '{ticket_id}' to '{new_status}' while dependency '{dependency_id}' is not closed"
                )

    updated_ticket = replace(ticket, status=new_status)
    updated_tickets = [updated_ticket if item.id == ticket_id else item for item in tickets]

    underlying_tasks, underlying_epics = build_underlying_entities(tasks, epics, updated_tickets)
    underlying_tasks_by_id = {task.id: task for task in underlying_tasks}
    underlying_epics_by_id = {epic.id: epic for epic in underlying_epics}

    update_messages: list[str] = []

    if ticket.status != updated_ticket.status:
        write_ticket_status(root_path, updated_ticket.id, updated_ticket.status)
        update_messages.append(f"{updated_ticket.id}: status {ticket.status} -> {updated_ticket.status}")

    for task in tasks:
        updated_task = underlying_tasks_by_id[task.id]
        if task.status != updated_task.status:
            write_task_status(root_path, updated_task.id, updated_task.status)
            update_messages.append(f"{updated_task.id}: status {task.status} -> {updated_task.status}")

    for epic in epics:
        updated_epic = underlying_epics_by_id[epic.id]
        if epic.status != updated_epic.status:
            write_epic_status(root_path, updated_epic.id, updated_epic.status)
            update_messages.append(f"{updated_epic.id}: status {epic.status} -> {updated_epic.status}")

    # Validate final persisted state after all updates are written.
    TicketRepository(root_path).load_all()
    return update_messages


def write_task_status(root_path: Path, task_id: str, status: str) -> None:
    task_path = root_path / TICKETS_ROOT_DIR_NAME / TASKS_DIR_NAME / f"{task_id}.yaml"
    update_yaml_status_field(task_path, status)


def write_epic_status(root_path: Path, epic_id: str, status: str) -> None:
    epic_path = root_path / TICKETS_ROOT_DIR_NAME / EPICS_DIR_NAME / f"{epic_id}.yaml"
    update_yaml_status_field(epic_path, status)


def write_ticket_status(root_path: Path, ticket_id: str, status: str) -> None:
    ticket_path = root_path / TICKETS_ROOT_DIR_NAME / TICKETS_DIR_NAME / f"{ticket_id}.yaml"
    update_yaml_status_field(ticket_path, status)


def update_yaml_status_field(file_path: Path, status: str) -> None:
    if not file_path.exists():
        raise RepositoryError(f"Entity file not found: {file_path}")

    data = read_yaml_mapping(file_path)
    data["status"] = status
    with file_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(data, file_handle, sort_keys=False)


def read_yaml_mapping(file_path: Path) -> dict[str, Any]:
    try:
        with file_path.open("r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)
    except yaml.YAMLError as error:
        raise RepositoryError(f"Invalid YAML in {file_path}: {error}") from error

    if not isinstance(data, dict):
        raise RepositoryError(f"Expected mapping in entity file: {file_path}")
    return data