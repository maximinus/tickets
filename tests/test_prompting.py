import unittest

from tickets.models import Epic, Ticket
from tickets.prompting import WORKER_INSTRUCTIONS, generate_prompt_for_ticket_id
from tickets.repository import RepositoryError


def make_epic(epic_id: str = "EPIC-001") -> Epic:
    return Epic(
        id=epic_id,
        task="TASK-001",
        title="Build the minimal ticket system",
        status="open",
        description="Epic description",
        acceptance_criteria=["Epic criterion one"],
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
        epics = [make_epic()]
        tickets = [make_ticket()]

        prompt_text = generate_prompt_for_ticket_id("T-001", epics, tickets)

        self.assertIsInstance(prompt_text, str)
        self.assertIn("Epic:", prompt_text)
        self.assertIn("Ticket:", prompt_text)

    def test_prompt_includes_epic_content(self) -> None:
        epics = [make_epic(epic_id="EPIC-123")]
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-123")]

        prompt_text = generate_prompt_for_ticket_id("T-001", epics, tickets)

        self.assertIn("id: EPIC-123", prompt_text)
        self.assertIn("title: Build the minimal ticket system", prompt_text)
        self.assertIn("acceptance_criteria:", prompt_text)
        self.assertIn("- Epic criterion one", prompt_text)

    def test_prompt_includes_ticket_content(self) -> None:
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-777")]

        prompt_text = generate_prompt_for_ticket_id("T-777", epics, tickets)

        self.assertIn("id: T-777", prompt_text)
        self.assertIn("title: Load YAML files", prompt_text)
        self.assertIn("out_of_scope:", prompt_text)
        self.assertIn("- Out of scope item", prompt_text)

    def test_prompt_includes_fixed_instructions(self) -> None:
        epics = [make_epic()]
        tickets = [make_ticket()]

        prompt_text = generate_prompt_for_ticket_id("T-001", epics, tickets)

        self.assertIn(WORKER_INSTRUCTIONS, prompt_text)
        self.assertIn("You are working on exactly one ticket.", prompt_text)
        self.assertIn("Use the acceptance criteria as the definition of done.", prompt_text)

    def test_error_when_ticket_id_does_not_exist(self) -> None:
        epics = [make_epic()]
        tickets = [make_ticket(ticket_id="T-001")]

        with self.assertRaises(RepositoryError) as error_context:
            generate_prompt_for_ticket_id("T-999", epics, tickets)

        self.assertIn("Ticket not found", str(error_context.exception))
        self.assertIn("T-999", str(error_context.exception))

    def test_error_when_related_epic_does_not_exist(self) -> None:
        epics: list[Epic] = []
        tickets = [make_ticket(ticket_id="T-001", epic_id="EPIC-404")]

        with self.assertRaises(RepositoryError) as error_context:
            generate_prompt_for_ticket_id("T-001", epics, tickets)

        self.assertIn("Related epic not found", str(error_context.exception))
        self.assertIn("EPIC-404", str(error_context.exception))


if __name__ == "__main__":
    unittest.main()
