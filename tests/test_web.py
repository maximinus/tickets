from pathlib import Path
import tempfile
import unittest

from tickets.web import HTTP_NOT_FOUND, HTTP_OK, build_web_response

SAMPLE_TASK_YAML = """
id: TASK-001
title: Example task
status: open
description: Task description
acceptance_criteria:
  - criterion one
""".strip()

SAMPLE_EPIC_YAML = """
id: EPIC-001
task: TASK-001
title: Example epic
status: open
description: Epic description
acceptance_criteria:
  - criterion one
""".strip()

SAMPLE_TICKET_YAML = """
id: T-001
epic: EPIC-001
title: Example ticket
status: open
depends_on: []
description: Ticket description
acceptance_criteria:
  - criterion one
out_of_scope:
  - not included
""".strip()


class WebRoutesTests(unittest.TestCase):
    def test_dashboard_route_returns_success_and_expected_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            response = build_web_response(root_path, "/")

            self.assertEqual(response.status_code, HTTP_OK)
            self.assertIn("Ticket Workspace", response.html_body)
            self.assertIn("Next Actionable Ticket", response.html_body)
            self.assertIn("T-001", response.html_body)

    def test_task_list_route_shows_all_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            response = build_web_response(root_path, "/tasks")

            self.assertEqual(response.status_code, HTTP_OK)
            self.assertIn("Tasks", response.html_body)
            self.assertIn("TASK-001", response.html_body)

    def test_task_detail_route_shows_task_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            response = build_web_response(root_path, "/task/TASK-001")

            self.assertEqual(response.status_code, HTTP_OK)
            self.assertIn("TASK-001: Example task", response.html_body)
            self.assertIn("Task description", response.html_body)

    def test_epic_routes_show_epic_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            list_response = build_web_response(root_path, "/epics")
            detail_response = build_web_response(root_path, "/epic/EPIC-001")

            self.assertEqual(list_response.status_code, HTTP_OK)
            self.assertIn("EPIC-001", list_response.html_body)
            self.assertEqual(detail_response.status_code, HTTP_OK)
            self.assertIn("EPIC-001: Example epic", detail_response.html_body)

    def test_ticket_routes_show_ticket_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            list_response = build_web_response(root_path, "/tickets")
            detail_response = build_web_response(root_path, "/ticket/T-001")

            self.assertEqual(list_response.status_code, HTTP_OK)
            self.assertIn("T-001", list_response.html_body)
            self.assertEqual(detail_response.status_code, HTTP_OK)
            self.assertIn("T-001: Example ticket", detail_response.html_body)
            self.assertIn("Depends On", detail_response.html_body)

    def test_invalid_id_route_returns_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory_string:
            root_path = Path(temp_directory_string)
            write_sample_repository(root_path)

            response = build_web_response(root_path, "/ticket/T-999")

            self.assertEqual(response.status_code, HTTP_NOT_FOUND)
            self.assertIn("Not Found", response.html_body)


def write_sample_repository(root_path: Path) -> None:
    write_text(root_path / ".tickets/tasks/TASK-001.yaml", SAMPLE_TASK_YAML)
    write_text(root_path / ".tickets/epics/EPIC-001.yaml", SAMPLE_EPIC_YAML)
    write_text(root_path / ".tickets/tickets/T-001.yaml", SAMPLE_TICKET_YAML)


def write_text(file_path: Path, content: str) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
