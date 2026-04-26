from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import unquote, urlparse

from tickets.repository import RepositoryError, TicketRepository
from tickets.rendering import (
    render_dashboard_page,
    render_epic_detail_page,
    render_epics_page,
    render_error_page,
    render_not_found_page,
    render_task_detail_page,
    render_tasks_page,
    render_ticket_detail_page,
    render_tickets_page,
)
from tickets.sequencing import find_next_actionable_ticket

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500


@dataclass(frozen=True)
class WebResponse:
    status_code: int
    html_body: str


def build_web_response(root_path: Path, request_path: str) -> WebResponse:
    try:
        repository = TicketRepository(root_path)
        tasks, epics, tickets = repository.load_all()
    except RepositoryError as error:
        error_html = render_error_page(str(error))
        return WebResponse(status_code=HTTP_SERVER_ERROR, html_body=error_html)

    parsed_path = urlparse(request_path).path
    normalized_path = normalize_path(parsed_path)

    if normalized_path == "/":
        next_ticket = find_next_actionable_ticket(tickets)
        return WebResponse(
            status_code=HTTP_OK,
            html_body=render_dashboard_page(tasks, epics, tickets, next_ticket),
        )

    if normalized_path == "/tasks":
        return WebResponse(status_code=HTTP_OK, html_body=render_tasks_page(tasks))

    if normalized_path == "/epics":
        return WebResponse(status_code=HTTP_OK, html_body=render_epics_page(epics))

    if normalized_path == "/tickets":
        return WebResponse(status_code=HTTP_OK, html_body=render_tickets_page(tickets))

    task_id = parse_entity_id(normalized_path, "/task/")
    if task_id is not None:
        task = find_entity_by_id(tasks, task_id)
        if task is None:
            return not_found_response(normalized_path)
        return WebResponse(status_code=HTTP_OK, html_body=render_task_detail_page(task))

    epic_id = parse_entity_id(normalized_path, "/epic/")
    if epic_id is not None:
        epic = find_entity_by_id(epics, epic_id)
        if epic is None:
            return not_found_response(normalized_path)
        return WebResponse(status_code=HTTP_OK, html_body=render_epic_detail_page(epic))

    ticket_id = parse_entity_id(normalized_path, "/ticket/")
    if ticket_id is not None:
        ticket = find_entity_by_id(tickets, ticket_id)
        if ticket is None:
            return not_found_response(normalized_path)
        return WebResponse(status_code=HTTP_OK, html_body=render_ticket_detail_page(ticket))

    return not_found_response(normalized_path)


def not_found_response(request_path: str) -> WebResponse:
    return WebResponse(status_code=HTTP_NOT_FOUND, html_body=render_not_found_page(request_path))


def normalize_path(path_value: str) -> str:
    if path_value.endswith("/") and path_value != "/":
        return path_value[:-1]
    return path_value


def parse_entity_id(normalized_path: str, prefix: str) -> str | None:
    if not normalized_path.startswith(prefix):
        return None
    entity_id = normalized_path.removeprefix(prefix)
    if "/" in entity_id or entity_id == "":
        return None
    return unquote(entity_id)


def find_entity_by_id(entities: list[Any], entity_id: str) -> Any | None:
    for entity in entities:
        if entity.id == entity_id:
            return entity
    return None


def make_request_handler(root_path: Path):
    class TicketsRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            response = build_web_response(root_path, self.path)
            body_bytes = response.html_body.encode("utf-8")
            self.send_response(response.status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

        def log_message(self, format_string: str, *args) -> None:
            return

    return TicketsRequestHandler


def serve_tickets_web(
    root_path: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    output_stream: TextIO | None = None,
) -> None:
    if port <= 0:
        raise RepositoryError("Port must be greater than zero")

    if output_stream is not None:
        print(f"Serving tickets UI at http://{host}:{port}", file=output_stream)

    handler_class = make_request_handler(root_path)
    with ThreadingHTTPServer((host, port), handler_class) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if output_stream is not None:
                print("Stopping tickets server.", file=output_stream)
