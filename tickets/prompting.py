from dataclasses import asdict
from pathlib import Path

import yaml

from tickets.models import Epic, Ticket
from tickets.repository import RepositoryError, TicketRepository

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
    epics: list[Epic],
    tickets: list[Ticket],
    current_working_directory: Path | None = None,
) -> str:
    ticket_by_id = {ticket.id: ticket for ticket in tickets}
    epic_by_id = {epic.id: epic for epic in epics}

    ticket = ticket_by_id.get(ticket_id)
    if ticket is None:
        raise RepositoryError(f"Ticket not found: {ticket_id}")

    epic = epic_by_id.get(ticket.epic)
    if epic is None:
        raise RepositoryError(f"Related epic not found for ticket '{ticket_id}': {ticket.epic}")

    worker_instructions = resolve_worker_instructions(current_working_directory)
    return build_worker_prompt(epic, ticket, worker_instructions)


def generate_prompt_for_ticket_id_from_repository(root_path: Path, ticket_id: str) -> str:
    repository = TicketRepository(root_path)
    _, epics, tickets = repository.load_all()
    return generate_prompt_for_ticket_id(ticket_id, epics, tickets)


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


def build_worker_prompt(epic: Epic, ticket: Ticket, worker_instructions: str) -> str:
    epic_text = format_entity_as_yaml(epic)
    ticket_text = format_entity_as_yaml(ticket)

    return f"{worker_instructions}\n\nEpic:\n{epic_text}\n\nTicket:\n{ticket_text}"


def format_entity_as_yaml(entity: Epic | Ticket) -> str:
    entity_dict = asdict(entity)
    return yaml.safe_dump(entity_dict, sort_keys=False, allow_unicode=False).strip()
