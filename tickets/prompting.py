from pathlib import Path

import yaml

from tickets.models import Epic, Task, Ticket
from tickets.repository import RepositoryError, TicketRepository
from tickets.status_engine import build_effective_entities

TICKETS_DIR_NAME = ".tickets"
PROMPTS_DIR_NAME = "prompts"
WORKER_PROMPT_FILE_NAME = "worker.md"

WORKER_INSTRUCTIONS = """You are working on exactly one ticket.

Complete only the ticket below.
Do not perform unrelated work.
Use the acceptance criteria as the definition of done.
Respect the out_of_scope section."""


def generate_prompt_for_ticket_id(
    ticket_id: str,
    tasks: list[Task],
    epics: list[Epic],
    tickets: list[Ticket],
    current_working_directory: Path | None = None,
) -> str:
    task_by_id = {task.id: task for task in tasks}
    ticket_by_id = {ticket.id: ticket for ticket in tickets}
    epic_by_id = {epic.id: epic for epic in epics}

    ticket = ticket_by_id.get(ticket_id)
    if ticket is None:
        raise RepositoryError(f"Ticket not found: {ticket_id}")

    epic = epic_by_id.get(ticket.epic)
    if epic is None:
        raise RepositoryError(f"Related epic not found for ticket '{ticket_id}': {ticket.epic}")

    task = task_by_id.get(epic.task)
    if task is None:
        raise RepositoryError(f"Related task not found for ticket '{ticket_id}': {epic.task}")

    worker_instructions = resolve_worker_instructions(current_working_directory)
    return build_worker_prompt(task, epic, ticket, worker_instructions)


def generate_prompt_for_ticket_id_from_repository(root_path: Path, ticket_id: str) -> str:
    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()
    effective_tasks, effective_epics, effective_tickets = build_effective_entities(tasks, epics, tickets)
    return generate_prompt_for_ticket_id(ticket_id, effective_tasks, effective_epics, effective_tickets)


def resolve_worker_instructions(current_working_directory: Path | None = None) -> str:
    resolved_current_working_directory = current_working_directory if current_working_directory is not None else Path.cwd()
    current_tickets_directory = resolved_current_working_directory / TICKETS_DIR_NAME

    if current_tickets_directory.exists() and current_tickets_directory.is_dir():
        current_worker_prompt_path = current_tickets_directory / PROMPTS_DIR_NAME / WORKER_PROMPT_FILE_NAME
        current_worker_instructions = read_worker_instructions_from_path(current_worker_prompt_path)
        if current_worker_instructions is not None:
            return current_worker_instructions

    installed_worker_prompt_path = get_installed_worker_prompt_path()
    installed_worker_instructions = read_worker_instructions_from_path(installed_worker_prompt_path)
    if installed_worker_instructions is not None:
        return installed_worker_instructions

    return WORKER_INSTRUCTIONS


def get_installed_worker_prompt_path() -> Path:
    package_root_directory = Path(__file__).resolve().parent.parent
    return package_root_directory / TICKETS_DIR_NAME / PROMPTS_DIR_NAME / WORKER_PROMPT_FILE_NAME


def read_worker_instructions_from_path(worker_prompt_path: Path) -> str | None:
    if not worker_prompt_path.exists() or not worker_prompt_path.is_file():
        return None
    return worker_prompt_path.read_text(encoding="utf-8").strip()


def build_worker_prompt(task: Task, epic: Epic, ticket: Ticket, worker_instructions: str) -> str:
    epic_text = format_epic_for_prompt(epic)
    task_text = format_task_for_prompt(task)
    ticket_text = format_ticket_for_prompt(ticket)

    return f"{worker_instructions}\n\nEpic:\n{epic_text}\n\nTask:\n{task_text}\n\nTicket:\n{ticket_text}"


def format_epic_for_prompt(epic: Epic) -> str:
    epic_dict = {
        "id": epic.id,
        "title": epic.title,
        "description": epic.description,
    }
    return yaml.safe_dump(epic_dict, sort_keys=False, allow_unicode=False).strip()


def format_task_for_prompt(task: Task) -> str:
    task_dict = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
    }
    return yaml.safe_dump(task_dict, sort_keys=False, allow_unicode=False).strip()


def format_ticket_for_prompt(ticket: Ticket) -> str:
    ticket_dict = {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "acceptance_criteria": ticket.acceptance_criteria,
        "out_of_scope": ticket.out_of_scope,
    }
    return yaml.safe_dump(ticket_dict, sort_keys=False, allow_unicode=False).strip()
