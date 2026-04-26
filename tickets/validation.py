from tickets.models import Epic, Task, Ticket

ALLOWED_STATUS_VALUES = {"open", "in_progress", "blocked", "closed"}


class ValidationError(Exception):
    pass


def validate_repository_data(tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    validate_duplicate_ids_across_entities(tasks, epics, tickets)
    validate_status_values(tasks, epics, tickets)
    validate_epic_task_references(tasks, epics)
    validate_ticket_epic_references(epics, tickets)
    validate_ticket_dependency_references(tickets)
    validate_ticket_dependency_cycles(tickets)


def validate_duplicate_ids_across_entities(tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    all_ids = [task.id for task in tasks] + [epic.id for epic in epics] + [ticket.id for ticket in tickets]
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()

    for entity_id in all_ids:
        if entity_id in seen_ids:
            duplicate_ids.add(entity_id)
        seen_ids.add(entity_id)

    if duplicate_ids:
        duplicate_ids_message = ", ".join(sorted(duplicate_ids))
        raise ValidationError(f"Duplicate IDs across entities: {duplicate_ids_message}")


def validate_status_values(tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    for task in tasks:
        validate_single_status(task.id, "task", task.status)

    for epic in epics:
        validate_single_status(epic.id, "epic", epic.status)

    for ticket in tickets:
        validate_single_status(ticket.id, "ticket", ticket.status)


def validate_single_status(entity_id: str, entity_name: str, status_value: str) -> None:
    if status_value not in ALLOWED_STATUS_VALUES:
        allowed_values = ", ".join(sorted(ALLOWED_STATUS_VALUES))
        raise ValidationError(
            f"Invalid status '{status_value}' for {entity_name} '{entity_id}'. Allowed values: {allowed_values}"
        )


def validate_epic_task_references(tasks: list[Task], epics: list[Epic]) -> None:
    task_ids = {task.id for task in tasks}

    for epic in epics:
        if epic.task not in task_ids:
            raise ValidationError(f"Epic '{epic.id}' references missing task '{epic.task}'")


def validate_ticket_epic_references(epics: list[Epic], tickets: list[Ticket]) -> None:
    epic_ids = {epic.id for epic in epics}

    for ticket in tickets:
        if ticket.epic not in epic_ids:
            raise ValidationError(f"Ticket '{ticket.id}' references missing epic '{ticket.epic}'")


def validate_ticket_dependency_references(tickets: list[Ticket]) -> None:
    ticket_ids = {ticket.id for ticket in tickets}

    for ticket in tickets:
        for dependency_id in ticket.depends_on:
            if dependency_id not in ticket_ids:
                raise ValidationError(f"Ticket '{ticket.id}' has dependency on missing ticket '{dependency_id}'")


def validate_ticket_dependency_cycles(tickets: list[Ticket]) -> None:
    dependency_graph = {ticket.id: ticket.depends_on for ticket in tickets}
    visited_ids: set[str] = set()
    stack_ids: set[str] = set()

    for ticket_id in sorted(dependency_graph):
        if ticket_id not in visited_ids:
            visit_ticket_for_cycle_detection(ticket_id, dependency_graph, visited_ids, stack_ids)


def visit_ticket_for_cycle_detection(
    ticket_id: str,
    dependency_graph: dict[str, list[str]],
    visited_ids: set[str],
    stack_ids: set[str],
) -> None:
    visited_ids.add(ticket_id)
    stack_ids.add(ticket_id)

    for dependency_id in dependency_graph.get(ticket_id, []):
        if dependency_id in stack_ids:
            raise ValidationError(f"Cycle detected in ticket dependencies involving '{dependency_id}'")
        if dependency_id not in visited_ids:
            visit_ticket_for_cycle_detection(dependency_id, dependency_graph, visited_ids, stack_ids)

    stack_ids.remove(ticket_id)
