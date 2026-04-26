from dataclasses import asdict
from pathlib import Path

import yaml

from tickets.models import Epic, Ticket
from tickets.repository import RepositoryError, TicketRepository

WORKER_INSTRUCTIONS = """You are working on exactly one ticket.

Complete only the ticket below.
Do not perform unrelated work.
Use the acceptance criteria as the definition of done.
Respect the out_of_scope section."""


def generate_prompt_for_ticket_id(ticket_id: str, epics: list[Epic], tickets: list[Ticket]) -> str:
    ticket_by_id = {ticket.id: ticket for ticket in tickets}
    epic_by_id = {epic.id: epic for epic in epics}

    ticket = ticket_by_id.get(ticket_id)
    if ticket is None:
        raise RepositoryError(f"Ticket not found: {ticket_id}")

    epic = epic_by_id.get(ticket.epic)
    if epic is None:
        raise RepositoryError(f"Related epic not found for ticket '{ticket_id}': {ticket.epic}")

    return build_worker_prompt(epic, ticket)


def generate_prompt_for_ticket_id_from_repository(root_path: Path, ticket_id: str) -> str:
    repository = TicketRepository(root_path)
    _, epics, tickets = repository.load_all()
    return generate_prompt_for_ticket_id(ticket_id, epics, tickets)


def build_worker_prompt(epic: Epic, ticket: Ticket) -> str:
    epic_text = format_entity_as_yaml(epic)
    ticket_text = format_entity_as_yaml(ticket)

    return f"{WORKER_INSTRUCTIONS}\n\nEpic:\n{epic_text}\n\nTicket:\n{ticket_text}"


def format_entity_as_yaml(entity: Epic | Ticket) -> str:
    entity_dict = asdict(entity)
    return yaml.safe_dump(entity_dict, sort_keys=False, allow_unicode=False).strip()
