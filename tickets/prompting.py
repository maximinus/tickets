from pathlib import Path

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
    lines = [
        f"id: {epic.id}",
        f"title: {epic.title}",
        format_description_field(epic.description),
    ]
    return "\n".join(lines)


def format_task_for_prompt(task: Task) -> str:
    lines = [
        f"id: {task.id}",
        f"title: {task.title}",
        format_description_field(task.description),
    ]
    return "\n".join(lines)


def format_ticket_for_prompt(ticket: Ticket) -> str:
    lines = [
        f"id: {ticket.id}",
        f"title: {ticket.title}",
        format_description_field(ticket.description),
        format_string_list_field("acceptance_criteria", ticket.acceptance_criteria),
        format_string_list_field("out_of_scope", ticket.out_of_scope),
    ]
    return "\n".join(lines)


def format_description_field(description_value: str) -> str:
    normalized_description = normalize_description_text(description_value)
    return f"description:\n{normalized_description}"


def format_string_list_field(field_name: str, values: list[str]) -> str:
    if not values:
        return f"{field_name}:\n- None"

    list_items = [f"- {value}" for value in values]
    return "\n".join([f"{field_name}:", *list_items])


def normalize_description_text(description_value: str) -> str:
    normalized_description = description_value.replace("\r\n", "\n").replace("\r", "\n")
    normalized_description = normalized_description.replace("\\n", "\n")
    normalized_description = normalized_description.replace("\\", "")

    cleaned_description = normalized_description.strip()
    if cleaned_description.startswith('"') and cleaned_description.endswith('"') and len(cleaned_description) >= 2:
        cleaned_description = cleaned_description[1:-1].strip()

    return cleaned_description if cleaned_description else "None"
