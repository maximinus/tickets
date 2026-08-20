from dataclasses import dataclass, field


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    status: str
    description: str
    acceptance_criteria: list[str]
    depends_on: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Epic:
    id: str
    task: str
    title: str
    status: str
    description: str
    acceptance_criteria: list[str]
    depends_on: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Ticket:
    id: str
    epic: str
    title: str
    status: str
    depends_on: list[str]
    description: str
    acceptance_criteria: list[str]
    out_of_scope: list[str]
    completion_notes: str | None = None
