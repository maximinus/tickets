from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tickets.models import Epic, Task, Ticket
from tickets.prompting import WORKER_INSTRUCTIONS, generate_prompt_for_ticket_id
from tickets.repository import RepositoryError


def make_task(task_id: str = "TASK-001") -> Task:
    return Task(
        id=task_id,
        title="Build the ticket workflow",
        status="open",
        description="Task description",
        acceptance_criteria=["Task criterion one"],
        depends_on=[],
    )


def make_epic(epic_id: str = "EPIC-001", task_id: str = "TASK-001") -> Epic:
    return Epic(
        id=epic_id,
        task=task_id,
        title="Build the minimal ticket system",
        status="open",
        description="Epic description",
        acceptance_criteria=["Epic criterion one"],
        depends_on=[],
    )


def make_ticket(ticket_id: str = "T-001", epic_id: str = "EPIC-001") -> Ticket:
    return Ticket(
        id=ticket_id,
        epic=epic_id,
        title="Load YAML files",
        status="open",
        depends_on=[],
        description="Ticket description",
        acceptance_criteria=["Ticket criterion one"],
        out_of_scope=["Out of scope item"],
    )


class PromptingTests(unittest.TestCase):
    def test_generate_prompt_for_valid_ticket(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket()]

        prompt_text = generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIsInstance(prompt_text, str)
        self.assertIn("Epic:", prompt_text)
        self.assertIn("Task:", prompt_text)
        self.assertIn("Ticket:", prompt_text)

    def test_prompt_includes_epic_content(self) -> None:
        tasks = [make_task()]
        epics = [make_epic(epic_id="EPIC-123")]
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-123")]

        prompt_text = generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIn("id: EPIC-123", prompt_text)
        self.assertIn("title: Build the minimal ticket system", prompt_text)
        self.assertIn("description:\nEpic description", prompt_text)
        self.assertNotIn("task: TASK-001", prompt_text)
        self.assertNotIn("status: open", prompt_text)
        self.assertNotIn("- Epic criterion one", prompt_text)

    def test_prompt_includes_task_content(self) -> None:
        tasks = [make_task(task_id="TASK-888")]
        epics = [make_epic(epic_id="EPIC-123", task_id="TASK-888")]
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-123")]

        prompt_text = generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIn("Task:\nid: TASK-888", prompt_text)
        self.assertIn("title: Build the ticket workflow", prompt_text)
        self.assertIn("description:\nTask description", prompt_text)
        self.assertNotIn("acceptance_criteria:\n- Task criterion one", prompt_text)

    def test_prompt_includes_ticket_content(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-777")]

        prompt_text = generate_prompt_for_ticket_id("T-777", tasks, epics, tickets)

        self.assertIn("id: T-777", prompt_text)
        self.assertIn("title: Load YAML files", prompt_text)
        self.assertIn("description:\nTicket description", prompt_text)
        self.assertIn("acceptance_criteria:", prompt_text)
        self.assertIn("out_of_scope:", prompt_text)
        self.assertIn("- Out of scope item", prompt_text)
        self.assertNotIn("epic: EPIC-001", prompt_text)
        self.assertNotIn("depends_on: []", prompt_text)
        self.assertNotIn("completion_notes", prompt_text)

    def test_prompt_normalizes_escaped_description_text(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [
            Ticket(
                id="T-777",
                epic="EPIC-001",
                title="Load YAML files",
                status="open",
                depends_on=[],
                description='"First line\\nSecond line\\n\\nThird line with slash\\"',
                acceptance_criteria=["Ticket criterion one"],
                out_of_scope=["Out of scope item"],
            )
        ]

        prompt_text = generate_prompt_for_ticket_id("T-777", tasks, epics, tickets)

        self.assertIn("description:\nFirst line\nSecond line\n\nThird line with slash", prompt_text)
        self.assertNotIn("\\n", prompt_text)
        self.assertNotIn("\\", prompt_text)

    def test_prompt_includes_fixed_instructions(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket()]

        prompt_text = generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIn(WORKER_INSTRUCTIONS, prompt_text)
        self.assertIn("You are working on exactly one ticket.", prompt_text)
        self.assertIn("Use the acceptance criteria as the definition of done.", prompt_text)

    def test_prompt_uses_current_working_directory_worker_file_when_available(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket()]

        with tempfile.TemporaryDirectory() as temp_directory_string:
            current_working_directory = Path(temp_directory_string)
            worker_prompt_path = current_working_directory / ".tickets" / "prompts" / "worker.md"
            worker_prompt_path.parent.mkdir(parents=True, exist_ok=True)
            worker_prompt_path.write_text("CWD worker instructions", encoding="utf-8")

            prompt_text = generate_prompt_for_ticket_id(
                "T-001",
                tasks,
                epics,
                tickets,
                current_working_directory=current_working_directory,
            )

            self.assertIn("CWD worker instructions", prompt_text)

    def test_prompt_uses_installed_worker_file_when_current_working_directory_prompt_missing(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket()]

        with tempfile.TemporaryDirectory() as temp_directory_string:
            current_working_directory = Path(temp_directory_string)
            (current_working_directory / ".tickets").mkdir(parents=True, exist_ok=True)

            installed_worker_prompt_path = current_working_directory / "installed-worker.md"
            installed_worker_prompt_path.write_text("Installed worker instructions", encoding="utf-8")

            with patch(
                "tickets.prompting.get_installed_worker_prompt_path",
                return_value=installed_worker_prompt_path,
            ):
                prompt_text = generate_prompt_for_ticket_id(
                    "T-001",
                    tasks,
                    epics,
                    tickets,
                    current_working_directory=current_working_directory,
                )

            self.assertIn("Installed worker instructions", prompt_text)

    def test_prompt_falls_back_to_constant_when_no_worker_file_exists(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket()]

        with tempfile.TemporaryDirectory() as temp_directory_string:
            current_working_directory = Path(temp_directory_string)
            missing_installed_worker_prompt_path = current_working_directory / "missing" / "worker.md"

            with patch(
                "tickets.prompting.get_installed_worker_prompt_path",
                return_value=missing_installed_worker_prompt_path,
            ):
                prompt_text = generate_prompt_for_ticket_id(
                    "T-001",
                    tasks,
                    epics,
                    tickets,
                    current_working_directory=current_working_directory,
                )

            self.assertIn(WORKER_INSTRUCTIONS, prompt_text)

    def test_error_when_ticket_id_does_not_exist(self) -> None:
        tasks = [make_task()]
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-001")]

        with self.assertRaises(RepositoryError) as error_context:
            generate_prompt_for_ticket_id("T-999", tasks, epics, tickets)

        self.assertIn("Ticket not found", str(error_context.exception))
        self.assertIn("T-999", str(error_context.exception))

    def test_error_when_related_epic_does_not_exist(self) -> None:
        tasks = [make_task()]
        epics: list[Epic] = []
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-404")]

        with self.assertRaises(RepositoryError) as error_context:
            generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIn("Related epic not found", str(error_context.exception))
        self.assertIn("EPIC-404", str(error_context.exception))

    def test_error_when_related_task_does_not_exist(self) -> None:
        tasks: list[Task] = []
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-001")]

        with self.assertRaises(RepositoryError) as error_context:
            generate_prompt_for_ticket_id("T-001", tasks, epics, tickets)

        self.assertIn("Related task not found", str(error_context.exception))
        self.assertIn("TASK-001", str(error_context.exception))


if __name__ == "__main__":
    unittest.main()
