from tickets.models import Epic, Task, Ticket

ALLOWED_STATUS_VALUES = {"open", "in_progress", "blocked", "closed"}


class ValidationError(Exception):
    pass


def validate_repository_data(tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    validate_duplicate_ids_across_entities(tasks, epics, tickets)
    validate_status_values(tasks, epics, tickets)
    validate_epic_task_references(tasks, epics)
    validate_ticket_epic_references(epics, tickets)
    validate_task_dependency_references(tasks)
    validate_epic_dependency_references(epics)
    validate_ticket_dependency_references(tickets)
    validate_task_dependency_same_epic(tasks, epics)
    validate_epic_dependency_same_task(epics)
    validate_ticket_dependency_same_task(tasks, epics, tickets)
    validate_task_dependency_cycles(tasks)
    validate_epic_dependency_cycles(epics)
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


def validate_task_dependency_references(tasks: list[Task]) -> None:
    task_ids = {task.id for task in tasks}

    for task in tasks:
        for dependency_id in task.depends_on:
            if dependency_id not in task_ids:
                raise ValidationError(f"Task '{task.id}' has dependency on missing task '{dependency_id}'")


def validate_task_dependency_same_epic(tasks: list[Task], epics: list[Epic]) -> None:
    task_to_epic = {epic.task: epic.id for epic in epics}

    for task in tasks:
        for dependency_id in task.depends_on:
            if dependency_id == task.id:
                continue
            if dependency_id not in task_to_epic:
                continue
            if task_to_epic.get(task.id) != task_to_epic.get(dependency_id):
                raise ValidationError(
                    f"Task '{task.id}' depends on task '{dependency_id}' from a different epic; dependencies must be in the same epic."
                )


def validate_epic_dependency_references(epics: list[Epic]) -> None:
    epic_ids = {epic.id for epic in epics}

    for epic in epics:
        for dependency_id in epic.depends_on:
            if dependency_id not in epic_ids:
                raise ValidationError(f"Epic '{epic.id}' has dependency on missing epic '{dependency_id}'")


def validate_epic_dependency_same_task(epics: list[Epic]) -> None:
    epics_by_id = {epic.id: epic for epic in epics}

    for epic in epics:
        for dependency_id in epic.depends_on:
            dependency_epic = epics_by_id.get(dependency_id)
            if dependency_epic is None:
                continue
            if dependency_epic.task != epic.task:
                raise ValidationError(
                    f"Epic '{epic.id}' depends on epic '{dependency_id}' from a different task; dependencies must be in the same task."
                )


def validate_ticket_dependency_references(tickets: list[Ticket]) -> None:
    ticket_ids = {ticket.id for ticket in tickets}

    for ticket in tickets:
        for dependency_id in ticket.depends_on:
            if dependency_id not in ticket_ids:
                raise ValidationError(f"Ticket '{ticket.id}' has dependency on missing ticket '{dependency_id}'")


def validate_ticket_dependency_same_task(tasks: list[Task], epics: list[Epic], tickets: list[Ticket]) -> None:
    del tasks
    tickets_by_id = {ticket.id: ticket for ticket in tickets}
    epics_by_id = {epic.id: epic for epic in epics}

    for ticket in tickets:
        for dependency_id in ticket.depends_on:
            dependency_ticket = tickets_by_id.get(dependency_id)
            if dependency_ticket is None:
                continue
            dependency_epic = epics_by_id.get(dependency_ticket.epic)
            current_epic = epics_by_id.get(ticket.epic)
            if dependency_epic is None or current_epic is None:
                continue
            if dependency_epic.task != current_epic.task:
                raise ValidationError(
                    f"Ticket '{ticket.id}' depends on ticket '{dependency_id}' from a different task; dependencies must be in the same task."
                )


def validate_task_dependency_cycles(tasks: list[Task]) -> None:
    dependency_graph = {task.id: task.depends_on for task in tasks}
    visited_ids: set[str] = set()
    stack_ids: set[str] = set()

    for task_id in sorted(dependency_graph):
        if task_id not in visited_ids:
            visit_task_for_cycle_detection(task_id, dependency_graph, visited_ids, stack_ids)


def visit_task_for_cycle_detection(
    task_id: str,
    dependency_graph: dict[str, list[str]],
    visited_ids: set[str],
    stack_ids: set[str],
) -> None:
    visited_ids.add(task_id)
    stack_ids.add(task_id)

    for dependency_id in dependency_graph.get(task_id, []):
        if dependency_id in stack_ids:
            raise ValidationError(f"Cycle detected in task dependencies involving '{dependency_id}'")
        if dependency_id not in visited_ids:
            visit_task_for_cycle_detection(dependency_id, dependency_graph, visited_ids, stack_ids)

    stack_ids.remove(task_id)


def validate_epic_dependency_cycles(epics: list[Epic]) -> None:
    dependency_graph = {epic.id: epic.depends_on for epic in epics}
    visited_ids: set[str] = set()
    stack_ids: set[str] = set()

    for epic_id in sorted(dependency_graph):
        if epic_id not in visited_ids:
            visit_epic_for_cycle_detection(epic_id, dependency_graph, visited_ids, stack_ids)


def visit_epic_for_cycle_detection(
    epic_id: str,
    dependency_graph: dict[str, list[str]],
    visited_ids: set[str],
    stack_ids: set[str],
) -> None:
    visited_ids.add(epic_id)
    stack_ids.add(epic_id)

    for dependency_id in dependency_graph.get(epic_id, []):
        if dependency_id in stack_ids:
            raise ValidationError(f"Cycle detected in epic dependencies involving '{dependency_id}'")
        if dependency_id not in visited_ids:
            visit_epic_for_cycle_detection(dependency_id, dependency_graph, visited_ids, stack_ids)

    stack_ids.remove(epic_id)


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
