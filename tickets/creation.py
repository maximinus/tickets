from pathlib import Path
from typing import Any

import yaml

from tickets.models import Epic, Task, Ticket
from tickets.repository import (
    EPIC_REQUIRED_FIELDS,
    TICKET_REQUIRED_FIELDS,
    RepositoryError,
    TicketRepository,
    ensure_required_fields,
    ensure_unique_ids,
    require_optional_string,
    require_string,
    require_string_list,
)
from tickets.validation import validate_repository_data
from tickets.validation import ValidationError

TASKS_DIR_NAME = "tasks"
EPICS_DIR_NAME = "epics"
TICKETS_DIR_NAME = "tickets"
TICKETS_ROOT_DIR_NAME = ".tickets"
DEFAULT_TASK_STATUS = "open"
DEFAULT_TASK_TITLE = "New task"
DEFAULT_TASK_DESCRIPTION = "Describe the task."
DEFAULT_TASK_ACCEPTANCE_CRITERION = "Define acceptance criteria"
TASK_ID_PREFIX = "TASK-"
TASK_ID_DIGITS = 3
TOP_LEVEL_PLAN_KEYS = ["epic", "tickets"]


def create_task_from_arguments(
    root_path: Path,
    task_id: str | None,
    title: str,
    description: str,
    acceptance_criteria: list[str],
) -> Task:
    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()

    resolved_task_id = task_id if task_id is not None else generate_next_task_id(tasks)
    resolved_acceptance_criteria = acceptance_criteria if acceptance_criteria else [DEFAULT_TASK_ACCEPTANCE_CRITERION]

    task = Task(
        id=resolved_task_id,
        title=title,
        status=DEFAULT_TASK_STATUS,
        description=description,
        acceptance_criteria=resolved_acceptance_criteria,
    )

    try:
        validate_repository_data(tasks + [task], epics, tickets)
    except ValidationError as error:
        raise RepositoryError(str(error)) from error
    write_task_yaml(root_path, task)
    return task


def import_plan_from_file(root_path: Path, plan_file_path: Path) -> tuple[Epic, list[Ticket]]:
    plan_data = read_yaml_file(plan_file_path)
    ensure_plan_shape(plan_data, plan_file_path)

    epic_data = plan_data["epic"]
    ticket_data_list = plan_data["tickets"]

    epic = parse_imported_epic(epic_data, plan_file_path)
    tickets = parse_imported_tickets(ticket_data_list, plan_file_path)

    repository = TicketRepository(root_path)
    tasks, existing_epics, existing_tickets = repository.load_all()

    try:
        validate_repository_data(tasks, existing_epics + [epic], existing_tickets + tickets)
    except ValidationError as error:
        raise RepositoryError(str(error)) from error
    write_epic_yaml(root_path, epic)
    write_ticket_yaml_files(root_path, tickets)

    return epic, tickets


def generate_next_task_id(tasks: list[Task]) -> str:
    max_numeric_id = 0

    for task in tasks:
        if task.id.startswith(TASK_ID_PREFIX):
            suffix_value = task.id[len(TASK_ID_PREFIX) :]
            if suffix_value.isdigit():
                numeric_id = int(suffix_value)
                if numeric_id > max_numeric_id:
                    max_numeric_id = numeric_id

    next_numeric_id = max_numeric_id + 1
    padded_numeric_id = str(next_numeric_id).zfill(TASK_ID_DIGITS)
    return f"{TASK_ID_PREFIX}{padded_numeric_id}"


def parse_imported_epic(epic_data: Any, plan_file_path: Path) -> Epic:
    if not isinstance(epic_data, dict):
        raise RepositoryError(f"Plan file must contain an 'epic' mapping: {plan_file_path}")

    ensure_required_fields(epic_data, EPIC_REQUIRED_FIELDS, "epic", plan_file_path)
    acceptance_criteria = require_string_list(epic_data, "acceptance_criteria", "epic")

    return Epic(
        id=require_string(epic_data, "id", "epic"),
        task=require_string(epic_data, "task", "epic"),
        title=require_string(epic_data, "title", "epic"),
        status=require_string(epic_data, "status", "epic"),
        description=require_string(epic_data, "description", "epic"),
        acceptance_criteria=acceptance_criteria,
    )


def parse_imported_tickets(ticket_data_list: Any, plan_file_path: Path) -> list[Ticket]:
    if not isinstance(ticket_data_list, list):
        raise RepositoryError(f"Plan file must contain a 'tickets' list: {plan_file_path}")

    imported_tickets: list[Ticket] = []
    for ticket_data in ticket_data_list:
        if not isinstance(ticket_data, dict):
            raise RepositoryError(f"Each imported ticket must be a mapping in file: {plan_file_path}")

        ensure_required_fields(ticket_data, TICKET_REQUIRED_FIELDS, "ticket", plan_file_path)

        ticket = Ticket(
            id=require_string(ticket_data, "id", "ticket"),
            epic=require_string(ticket_data, "epic", "ticket"),
            title=require_string(ticket_data, "title", "ticket"),
            status=require_string(ticket_data, "status", "ticket"),
            depends_on=require_string_list(ticket_data, "depends_on", "ticket"),
            description=require_string(ticket_data, "description", "ticket"),
            acceptance_criteria=require_string_list(ticket_data, "acceptance_criteria", "ticket"),
            out_of_scope=require_string_list(ticket_data, "out_of_scope", "ticket"),
            completion_notes=require_optional_string(ticket_data, "completion_notes", "ticket"),
        )
        imported_tickets.append(ticket)

    ensure_unique_ids([ticket.id for ticket in imported_tickets], "ticket")
    return imported_tickets


def ensure_plan_shape(plan_data: Any, plan_file_path: Path) -> None:
    if not isinstance(plan_data, dict):
        raise RepositoryError(f"Plan file must contain a top-level mapping: {plan_file_path}")

    missing_keys = [key for key in TOP_LEVEL_PLAN_KEYS if key not in plan_data]
    if missing_keys:
        missing_keys_message = ", ".join(sorted(missing_keys))
        raise RepositoryError(f"Plan file is missing required keys ({missing_keys_message}): {plan_file_path}")


def read_yaml_file(file_path: Path) -> Any:
    if not file_path.exists():
        raise RepositoryError(f"Plan file not found: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as file_handle:
            return yaml.safe_load(file_handle)
    except yaml.YAMLError as error:
        raise RepositoryError(f"Invalid YAML in {file_path}: {error}") from error


def write_task_yaml(root_path: Path, task: Task) -> None:
    file_path = root_path / TICKETS_ROOT_DIR_NAME / TASKS_DIR_NAME / f"{task.id}.yaml"
    if file_path.exists():
        raise RepositoryError(f"Task file already exists: {file_path}")

    task_data = {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "description": task.description,
        "acceptance_criteria": task.acceptance_criteria,
    }
    write_yaml_mapping(file_path, task_data)


def write_epic_yaml(root_path: Path, epic: Epic) -> None:
    file_path = root_path / TICKETS_ROOT_DIR_NAME / EPICS_DIR_NAME / f"{epic.id}.yaml"
    if file_path.exists():
        raise RepositoryError(f"Epic file already exists: {file_path}")

    epic_data = {
        "id": epic.id,
        "task": epic.task,
        "title": epic.title,
        "status": epic.status,
        "description": epic.description,
        "acceptance_criteria": epic.acceptance_criteria,
    }
    write_yaml_mapping(file_path, epic_data)


def write_ticket_yaml_files(root_path: Path, tickets: list[Ticket]) -> None:
    for ticket in tickets:
        file_path = root_path / TICKETS_ROOT_DIR_NAME / TICKETS_DIR_NAME / f"{ticket.id}.yaml"
        if file_path.exists():
            raise RepositoryError(f"Ticket file already exists: {file_path}")

    for ticket in tickets:
        write_ticket_yaml(root_path, ticket)


def write_ticket_yaml(root_path: Path, ticket: Ticket) -> None:
    file_path = root_path / TICKETS_ROOT_DIR_NAME / TICKETS_DIR_NAME / f"{ticket.id}.yaml"
    ticket_data: dict[str, Any] = {
        "id": ticket.id,
        "epic": ticket.epic,
        "title": ticket.title,
        "status": ticket.status,
        "depends_on": ticket.depends_on,
        "description": ticket.description,
        "acceptance_criteria": ticket.acceptance_criteria,
        "out_of_scope": ticket.out_of_scope,
    }
    if ticket.completion_notes is not None:
        ticket_data["completion_notes"] = ticket.completion_notes

    write_yaml_mapping(file_path, ticket_data)


def write_yaml_mapping(file_path: Path, data: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(data, file_handle, sort_keys=False)
