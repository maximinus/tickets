from pathlib import Path
from typing import Any

import yaml

from tickets.models import Epic, Task, Ticket
from tickets.validation import ValidationError, validate_repository_data

TASKS_DIR_NAME = "tasks"
EPICS_DIR_NAME = "epics"
TICKETS_DIR_NAME = "tickets"
YAML_FILE_PATTERN = "*.yaml"

TASK_REQUIRED_FIELDS = ["id", "title", "status", "depends_on", "description", "acceptance_criteria"]
EPIC_REQUIRED_FIELDS = ["id", "task", "title", "status", "depends_on", "description", "acceptance_criteria"]
TICKET_REQUIRED_FIELDS = [
    "id",
    "epic",
    "title",
    "status",
    "depends_on",
    "description",
    "acceptance_criteria",
    "out_of_scope",
]


class RepositoryError(Exception):
    pass


class TicketRepository:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.tickets_path = root_path / ".tickets"

    def load_tasks(self) -> list[Task]:
        task_dicts = load_entity_dicts(
            self.tickets_path / TASKS_DIR_NAME,
            TASK_REQUIRED_FIELDS,
            "task",
        )
        tasks: list[Task] = []
        for task_dict in task_dicts:
            depends_on = require_string_list(task_dict, "depends_on", "task")
            acceptance_criteria = require_string_list(
                task_dict,
                "acceptance_criteria",
                "task",
            )
            task = Task(
                id=require_string(task_dict, "id", "task"),
                title=require_string(task_dict, "title", "task"),
                status=require_string(task_dict, "status", "task"),
                description=require_string(task_dict, "description", "task"),
                acceptance_criteria=acceptance_criteria,
                depends_on=depends_on,
            )
            tasks.append(task)
        ensure_unique_ids([task.id for task in tasks], "task")
        return tasks

    def load_epics(self) -> list[Epic]:
        epic_dicts = load_entity_dicts(
            self.tickets_path / EPICS_DIR_NAME,
            EPIC_REQUIRED_FIELDS,
            "epic",
        )
        epics: list[Epic] = []
        for epic_dict in epic_dicts:
            depends_on = require_string_list(epic_dict, "depends_on", "epic")
            acceptance_criteria = require_string_list(
                epic_dict,
                "acceptance_criteria",
                "epic",
            )
            epic = Epic(
                id=require_string(epic_dict, "id", "epic"),
                task=require_string(epic_dict, "task", "epic"),
                title=require_string(epic_dict, "title", "epic"),
                status=require_string(epic_dict, "status", "epic"),
                description=require_string(epic_dict, "description", "epic"),
                acceptance_criteria=acceptance_criteria,
                depends_on=depends_on,
            )
            epics.append(epic)
        ensure_unique_ids([epic.id for epic in epics], "epic")
        return epics

    def load_tickets(self) -> list[Ticket]:
        ticket_dicts = load_entity_dicts(
            self.tickets_path / TICKETS_DIR_NAME,
            TICKET_REQUIRED_FIELDS,
            "ticket",
        )
        tickets: list[Ticket] = []
        for ticket_dict in ticket_dicts:
            depends_on = require_string_list(ticket_dict, "depends_on", "ticket")
            acceptance_criteria = require_string_list(
                ticket_dict,
                "acceptance_criteria",
                "ticket",
            )
            out_of_scope = require_string_list(ticket_dict, "out_of_scope", "ticket")
            completion_notes = require_optional_string(ticket_dict, "completion_notes", "ticket")

            ticket = Ticket(
                id=require_string(ticket_dict, "id", "ticket"),
                epic=require_string(ticket_dict, "epic", "ticket"),
                title=require_string(ticket_dict, "title", "ticket"),
                status=require_string(ticket_dict, "status", "ticket"),
                depends_on=depends_on,
                description=require_string(ticket_dict, "description", "ticket"),
                acceptance_criteria=acceptance_criteria,
                out_of_scope=out_of_scope,
                completion_notes=completion_notes,
            )
            tickets.append(ticket)
        ensure_unique_ids([ticket.id for ticket in tickets], "ticket")
        return tickets

    def load_all(self) -> tuple[list[Task], list[Epic], list[Ticket]]:
        tasks = self.load_tasks()
        epics = self.load_epics()
        tickets = self.load_tickets()
        try:
            validate_repository_data(tasks, epics, tickets)
        except ValidationError as error:
            raise RepositoryError(str(error)) from error
        return tasks, epics, tickets

    def delete_entity(self, entity_id: str) -> list[str]:
        tasks, epics, tickets = self.load_all()

        task_ids_by_id = {task.id: task for task in tasks}
        epic_ids_by_id = {epic.id: epic for epic in epics}
        ticket_ids_by_id = {ticket.id: ticket for ticket in tickets}

        deleted_ids: set[str] = set()

        if entity_id in ticket_ids_by_id:
            deleted_ids.add(entity_id)
        elif entity_id in task_ids_by_id:
            task = task_ids_by_id[entity_id]
            deleted_ids.add(task.id)
            related_epic_ids = {epic.id for epic in epics if epic.task == task.id}
            for epic_id in related_epic_ids:
                deleted_ids.add(epic_id)
                for ticket in tickets:
                    if ticket.epic == epic_id:
                        deleted_ids.add(ticket.id)
        elif entity_id in epic_ids_by_id:
            epic = epic_ids_by_id[entity_id]
            related_task_ids = {task.id for task in tasks if task.id == epic.task}
            related_epic_ids = {current_epic.id for current_epic in epics if current_epic.task in related_task_ids}
            deleted_ids.add(epic.id)
            deleted_ids.update(related_task_ids)
            deleted_ids.update(related_epic_ids)
            for candidate_epic in epics:
                if candidate_epic.task in related_task_ids:
                    for ticket in tickets:
                        if ticket.epic == candidate_epic.id:
                            deleted_ids.add(ticket.id)
        else:
            raise RepositoryError(f"Entity not found: {entity_id}")

        for ticket_id in sorted(deleted_ids):
            ticket_path = self.tickets_path / TICKETS_DIR_NAME / f"{ticket_id}.yaml"
            if ticket_path.exists():
                ticket_path.unlink()

        for task_id in sorted({task_id for task_id in deleted_ids if task_id in task_ids_by_id}):
            task_path = self.tickets_path / TASKS_DIR_NAME / f"{task_id}.yaml"
            if task_path.exists():
                task_path.unlink()

        for epic_id in sorted({epic_id for epic_id in deleted_ids if epic_id in epic_ids_by_id}):
            epic_path = self.tickets_path / EPICS_DIR_NAME / f"{epic_id}.yaml"
            if epic_path.exists():
                epic_path.unlink()

        remove_deleted_dependencies(self.root_path, deleted_ids)
        remaining_tasks, remaining_epics, remaining_tickets = self.load_all()
        update_statuses_after_delete(self.root_path, remaining_tasks, remaining_epics, remaining_tickets)
        return sorted(deleted_ids)


def remove_deleted_dependencies(root_path: Path, deleted_ids: set[str]) -> None:
    tickets_root = root_path / ".tickets"
    for directory_name in (TASKS_DIR_NAME, EPICS_DIR_NAME, TICKETS_DIR_NAME):
        entity_directory = tickets_root / directory_name
        if not entity_directory.exists():
            continue
        for file_path in sorted(entity_directory.glob(YAML_FILE_PATTERN)):
            file_data = read_yaml_file(file_path)
            if not isinstance(file_data, dict):
                continue
            if "depends_on" not in file_data:
                continue
            file_data["depends_on"] = [
                dependency_id for dependency_id in file_data["depends_on"] if dependency_id not in deleted_ids
            ]
            with file_path.open("w", encoding="utf-8") as file_handle:
                yaml.safe_dump(file_data, file_handle, sort_keys=False)


def update_statuses_after_delete(root_path: Path, tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    from tickets.status_engine import build_effective_entities, build_underlying_entities

    effective_tasks, effective_epics, effective_tickets = build_effective_entities(tasks, epics, tickets)
    effective_tasks_by_id = {task.id: task for task in effective_tasks}
    effective_epics_by_id = {epic.id: epic for epic in effective_epics}
    effective_tickets_by_id = {ticket.id: ticket for ticket in effective_tickets}

    underlying_tasks, underlying_epics = build_underlying_entities(tasks, epics, tickets)
    underlying_tasks_by_id = {task.id: task for task in underlying_tasks}
    underlying_epics_by_id = {epic.id: epic for epic in underlying_epics}

    for ticket in tickets:
        effective_ticket = effective_tickets_by_id[ticket.id]
        if ticket.status != effective_ticket.status:
            write_status_update(root_path, TICKETS_DIR_NAME, ticket.id, effective_ticket.status)

    for task in tasks:
        underlying_task = underlying_tasks_by_id[task.id]
        if task.status != underlying_task.status:
            write_status_update(root_path, TASKS_DIR_NAME, task.id, underlying_task.status)

    for epic in epics:
        underlying_epic = underlying_epics_by_id[epic.id]
        if epic.status != underlying_epic.status:
            write_status_update(root_path, EPICS_DIR_NAME, epic.id, underlying_epic.status)


def write_status_update(root_path: Path, directory_name: str, entity_id: str, status: str) -> None:
    file_path = root_path / ".tickets" / directory_name / f"{entity_id}.yaml"
    if not file_path.exists():
        return
    file_data = read_yaml_file(file_path)
    if not isinstance(file_data, dict):
        raise RepositoryError(f"Expected mapping in entity file: {file_path}")
    file_data["status"] = status
    with file_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(file_data, file_handle, sort_keys=False)


def load_entity_dicts(entity_directory: Path, required_fields: list[str], entity_name: str) -> list[dict[str, Any]]:
    if not entity_directory.exists():
        return []

    file_paths = sorted(entity_directory.glob(YAML_FILE_PATTERN))
    entity_dicts: list[dict[str, Any]] = []

    for file_path in file_paths:
        file_data = read_yaml_file(file_path)
        if not isinstance(file_data, dict):
            raise RepositoryError(f"Expected mapping in {entity_name} file: {file_path}")
        ensure_required_fields(file_data, required_fields, entity_name, file_path)
        entity_dicts.append(file_data)

    return entity_dicts


def read_yaml_file(file_path: Path) -> Any:
    try:
        with file_path.open("r", encoding="utf-8") as file_handle:
            return yaml.safe_load(file_handle)
    except yaml.YAMLError as error:
        raise RepositoryError(f"Invalid YAML in {file_path}: {error}") from error


def ensure_required_fields(
    entity_dict: dict[str, Any], required_fields: list[str], entity_name: str, file_path: Path
) -> None:
    missing_fields = [field_name for field_name in required_fields if field_name not in entity_dict]
    if missing_fields:
        missing_fields_message = ", ".join(sorted(missing_fields))
        raise RepositoryError(f"Missing required fields in {entity_name} file {file_path}: {missing_fields_message}")


def require_string(entity_dict: dict[str, Any], field_name: str, entity_name: str) -> str:
    field_value = entity_dict[field_name]
    if not isinstance(field_value, str):
        raise RepositoryError(f"Field '{field_name}' in {entity_name} must be a string")
    return field_value


def require_optional_string(entity_dict: dict[str, Any], field_name: str, entity_name: str) -> str | None:
    if field_name not in entity_dict:
        return None
    field_value = entity_dict[field_name]
    if field_value is None:
        return None
    if not isinstance(field_value, str):
        raise RepositoryError(f"Field '{field_name}' in {entity_name} must be a string if present")
    return field_value


def require_string_list(entity_dict: dict[str, Any], field_name: str, entity_name: str) -> list[str]:
    if field_name not in entity_dict:
        return []

    field_value = entity_dict[field_name]
    if not isinstance(field_value, list):
        raise RepositoryError(f"Field '{field_name}' in {entity_name} must be a list")

    list_values: list[str] = []
    for value in field_value:
        if not isinstance(value, str):
            raise RepositoryError(f"Field '{field_name}' in {entity_name} must contain only strings")
        list_values.append(value)

    return list_values


def ensure_unique_ids(entity_ids: list[str], entity_name: str) -> None:
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()

    for entity_id in entity_ids:
        if entity_id in seen_ids:
            duplicate_ids.add(entity_id)
        seen_ids.add(entity_id)

    if duplicate_ids:
        duplicate_ids_message = ", ".join(sorted(duplicate_ids))
        raise RepositoryError(f"Duplicate {entity_name} id values: {duplicate_ids_message}")
