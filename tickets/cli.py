import argparse
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence, TextIO

from tickets.creation import (
    DEFAULT_TASK_DESCRIPTION,
    DEFAULT_TASK_TITLE,
    create_task_from_arguments,
    import_plan_from_file,
)
from tickets.prompting import generate_prompt_for_ticket_id
from tickets.repository import RepositoryError, TicketRepository
from tickets.sequencing import find_next_actionable_ticket
from tickets.web import serve_tickets_web

LIST_ENTITY_CHOICES = ["tasks", "epics", "tickets"]
SUCCESS_EXIT_CODE = 0
ERROR_EXIT_CODE = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tickets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List entities")
    list_parser.add_argument("entity", choices=LIST_ENTITY_CHOICES, nargs="?")

    show_parser = subparsers.add_parser("show", help="Show entity details")
    show_parser.add_argument("entity_id")

    subparsers.add_parser("validate", help="Validate repository data")
    subparsers.add_parser("next", help="Show next actionable ticket")

    prompt_parser = subparsers.add_parser("prompt", help="Generate worker prompt for a ticket")
    prompt_parser.add_argument("ticket_id")

    subparsers.add_parser("prompt-next", help="Generate worker prompt for the next actionable ticket")

    create_task_parser = subparsers.add_parser("create-task", help="Create a skeleton task file")
    create_task_parser.add_argument("--task-id")
    create_task_parser.add_argument("--title", default=DEFAULT_TASK_TITLE)
    create_task_parser.add_argument("--description", default=DEFAULT_TASK_DESCRIPTION)
    create_task_parser.add_argument("--acceptance-criterion", action="append", default=[])

    import_plan_parser = subparsers.add_parser("import-plan", help="Import epic and tickets from a plan YAML file")
    import_plan_parser.add_argument("plan_file")

    serve_parser = subparsers.add_parser("serve", help="Serve the read-only local web interface")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    return parser


def run_cli(
    argument_values: Sequence[str] | None = None,
    standard_output: TextIO | None = None,
    standard_error: TextIO | None = None,
    root_path: Path | None = None,
) -> int:
    parser = build_parser()
    parsed_arguments = parser.parse_args(argument_values)

    output_stream = standard_output if standard_output is not None else sys.stdout
    error_stream = standard_error if standard_error is not None else sys.stderr
    repository_root_path = root_path if root_path is not None else Path.cwd()

    try:
        if parsed_arguments.command == "list":
            return handle_list_command(repository_root_path, parsed_arguments.entity, output_stream)
        if parsed_arguments.command == "show":
            return handle_show_command(repository_root_path, parsed_arguments.entity_id, output_stream, error_stream)
        if parsed_arguments.command == "validate":
            return handle_validate_command(repository_root_path, output_stream)
        if parsed_arguments.command == "next":
            return handle_next_command(repository_root_path, output_stream)
        if parsed_arguments.command == "prompt":
            return handle_prompt_command(repository_root_path, parsed_arguments.ticket_id, output_stream)
        if parsed_arguments.command == "prompt-next":
            return handle_prompt_next_command(repository_root_path, output_stream)
        if parsed_arguments.command == "create-task":
            return handle_create_task_command(
                root_path=repository_root_path,
                task_id=parsed_arguments.task_id,
                title=parsed_arguments.title,
                description=parsed_arguments.description,
                acceptance_criteria=parsed_arguments.acceptance_criterion,
                output_stream=output_stream,
            )
        if parsed_arguments.command == "import-plan":
            plan_file_path = Path(parsed_arguments.plan_file)
            return handle_import_plan_command(repository_root_path, plan_file_path, output_stream)
        if parsed_arguments.command == "serve":
            return handle_serve_command(
                repository_root_path, parsed_arguments.host, parsed_arguments.port, output_stream
            )
    except RepositoryError as error:
        print(f"Error: {error}", file=error_stream)
        return ERROR_EXIT_CODE

    parser.print_help(file=error_stream)
    return ERROR_EXIT_CODE


def handle_list_command(root_path: Path, entity_name: str | None, output_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()

    entity_map = {
        "tasks": tasks,
        "epics": epics,
        "tickets": tickets,
    }
    if entity_name is None:
        print_grouped_list_by_epic(tasks, epics, tickets, output_stream)
        return SUCCESS_EXIT_CODE
    else:
        entities = entity_map[entity_name]

    for entity in entities:
        print(f"{entity.id} | {entity.status} | {entity.title}", file=output_stream)

    return SUCCESS_EXIT_CODE


def print_grouped_list_by_epic(tasks: list, epics: list, tickets: list, output_stream: TextIO) -> None:
    tasks_by_id = {task.id: task for task in tasks}
    tickets_by_epic: dict[str, list] = {}

    for ticket in tickets:
        if ticket.epic not in tickets_by_epic:
            tickets_by_epic[ticket.epic] = []
        tickets_by_epic[ticket.epic].append(ticket)

    for epic in sorted(epics, key=lambda value: value.id):
        print(f"{epic.id} | {epic.status} | {epic.title}", file=output_stream)

        task = tasks_by_id.get(epic.task)
        if task is not None:
            print(f"  {task.id} | {task.status} | {task.title}", file=output_stream)

        epic_tickets = tickets_by_epic.get(epic.id, [])
        for ticket in sorted(epic_tickets, key=lambda value: value.id):
            print(f"    {ticket.id} | {ticket.status} | {ticket.title}", file=output_stream)


def handle_show_command(root_path: Path, entity_id: str, output_stream: TextIO, error_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()

    all_entities = [*tasks, *epics, *tickets]
    entity_by_id = {entity.id: entity for entity in all_entities}
    if entity_id not in entity_by_id:
        print(f"Error: Entity not found: {entity_id}", file=error_stream)
        return ERROR_EXIT_CODE

    entity = entity_by_id[entity_id]
    entity_dict = asdict(entity)
    for key, value in entity_dict.items():
        print(f"{key}: {value}", file=output_stream)

    return SUCCESS_EXIT_CODE


def handle_validate_command(root_path: Path, output_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    repository.load_all()
    print("Validation passed.", file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_next_command(root_path: Path, output_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    tasks, epics, tickets = repository.load_all()
    next_ticket = find_next_actionable_ticket(tickets, epics, tasks)

    if next_ticket is None:
        print("No actionable tickets found.", file=output_stream)
        return SUCCESS_EXIT_CODE

    tasks_by_id = {task.id: task for task in tasks}
    epics_by_id = {epic.id: epic for epic in epics}
    epic = epics_by_id.get(next_ticket.epic)
    task = tasks_by_id.get(epic.task) if epic is not None else None

    if epic is not None and task is not None:
        print(f"{epic.id} -> {task.id} -> {next_ticket.id}: {next_ticket.title}", file=output_stream)
    else:
        print(f"{next_ticket.id}: {next_ticket.title}", file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_prompt_command(root_path: Path, ticket_id: str, output_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    _, epics, tickets = repository.load_all()
    prompt_text = generate_prompt_for_ticket_id(ticket_id, epics, tickets)
    print(prompt_text, file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_prompt_next_command(root_path: Path, output_stream: TextIO) -> int:
    repository = TicketRepository(root_path)
    _, epics, tickets = repository.load_all()
    next_ticket = find_next_actionable_ticket(tickets)

    if next_ticket is None:
        print("No actionable tickets found.", file=output_stream)
        return SUCCESS_EXIT_CODE

    prompt_text = generate_prompt_for_ticket_id(next_ticket.id, epics, tickets)
    print(prompt_text, file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_create_task_command(
    root_path: Path,
    task_id: str | None,
    title: str,
    description: str,
    acceptance_criteria: list[str],
    output_stream: TextIO,
) -> int:
    task = create_task_from_arguments(
        root_path=root_path,
        task_id=task_id,
        title=title,
        description=description,
        acceptance_criteria=acceptance_criteria,
    )
    print(f"Created task {task.id}", file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_import_plan_command(root_path: Path, plan_file_path: Path, output_stream: TextIO) -> int:
    resolved_plan_file_path = plan_file_path if plan_file_path.is_absolute() else root_path / plan_file_path
    epic, tickets = import_plan_from_file(root_path=root_path, plan_file_path=resolved_plan_file_path)
    print(f"Imported epic {epic.id} and {len(tickets)} tickets.", file=output_stream)
    return SUCCESS_EXIT_CODE


def handle_serve_command(root_path: Path, host: str, port: int, output_stream: TextIO) -> int:
    serve_tickets_web(root_path, host=host, port=port, output_stream=output_stream)
    return SUCCESS_EXIT_CODE


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
