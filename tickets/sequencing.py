from tickets.models import Ticket

OPEN_STATUS = "open"
CLOSED_STATUS = "closed"


def find_next_actionable_ticket(tickets: list[Ticket]) -> Ticket | None:
    tickets_by_id = {ticket.id: ticket for ticket in tickets}

    for ticket in sorted(tickets, key=lambda ticket: ticket.id):
        if is_ticket_actionable(ticket, tickets_by_id):
            return ticket

    return None


def is_ticket_actionable(ticket: Ticket, tickets_by_id: dict[str, Ticket]) -> bool:
    if ticket.status != OPEN_STATUS:
        return False

    for dependency_id in ticket.depends_on:
        dependency_ticket = tickets_by_id.get(dependency_id)
        if dependency_ticket is None:
            return False
        if dependency_ticket.status != CLOSED_STATUS:
            return False

    return True
