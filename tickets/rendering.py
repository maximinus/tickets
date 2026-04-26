from html import escape

from tickets.models import Epic, Task, Ticket

OPEN_STATUS = "open"
IN_PROGRESS_STATUS = "in_progress"
BLOCKED_STATUS = "blocked"
CLOSED_STATUS = "closed"

STATUS_LABELS = {
    OPEN_STATUS: "Open",
    IN_PROGRESS_STATUS: "In progress",
    BLOCKED_STATUS: "Blocked",
    CLOSED_STATUS: "Closed",
}

NAV_LINKS = [
    ("/", "Dashboard"),
    ("/tasks", "Tasks"),
    ("/epics", "Epics"),
    ("/tickets", "Tickets"),
]


def render_dashboard_page(
    tasks: list[Task], epics: list[Epic], tickets: list[Ticket], next_ticket: Ticket | None
) -> str:
    stats_html = "".join(
        [
            render_stat_card("Tasks", len(tasks), "/tasks", "#fff5dc"),
            render_stat_card("Epics", len(epics), "/epics", "#e9f7ff"),
            render_stat_card("Tickets", len(tickets), "/tickets", "#f4f0ff"),
            render_stat_card("Open Tickets", count_tickets_by_status(tickets, OPEN_STATUS), "/tickets", "#e8faef"),
        ]
    )

    next_ticket_html = render_next_ticket_panel(next_ticket)
    ticket_grid_html = "".join(
        [render_ticket_card(ticket, include_epic=True) for ticket in sorted(tickets, key=lambda value: value.id)]
    )

    body_html = f"""
    <section class=\"hero\">
      <div>
        <h1>Ticket Workspace</h1>
        <p class=\"hero-text\">A clean, read-only snapshot of tasks, epics, and tickets for the current project.</p>
      </div>
      <div class=\"hero-meta\">Updated from .tickets/</div>
    </section>

    <section class=\"stats-grid\">{stats_html}</section>

    <section class=\"section-block\">
      <header class=\"section-header\">
        <h2>Next Actionable Ticket</h2>
      </header>
      {next_ticket_html}
    </section>

    <section class=\"section-block\">
      <header class=\"section-header\">
        <h2>All Tickets</h2>
      </header>
      <div class=\"toolbar\">
        <input id=\"search-input\" class=\"search-input\" type=\"search\" placeholder=\"Search by id or title\" aria-label=\"Search tickets\" />
        <div class=\"status-filters\">
          <button class=\"chip is-active\" data-status-filter=\"all\" type=\"button\">All</button>
          <button class=\"chip\" data-status-filter=\"open\" type=\"button\">Open</button>
          <button class=\"chip\" data-status-filter=\"in_progress\" type=\"button\">In progress</button>
          <button class=\"chip\" data-status-filter=\"blocked\" type=\"button\">Blocked</button>
          <button class=\"chip\" data-status-filter=\"closed\" type=\"button\">Closed</button>
        </div>
      </div>
      <div class=\"entity-grid js-filter-grid\">{ticket_grid_html}</div>
      <p class=\"empty-note js-empty-note\" hidden>No tickets match the current filters.</p>
    </section>
    """

    return render_page("Dashboard", body_html, "/")


def render_tasks_page(tasks: list[Task]) -> str:
    cards_html = "".join([render_task_card(task) for task in sorted(tasks, key=lambda value: value.id)])
    body_html = f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <h1>Tasks</h1>
        <p class=\"section-description\">Top-level goals that anchor epics and tickets.</p>
      </header>
      <div class=\"entity-grid\">{cards_html}</div>
    </section>
    """
    return render_page("Tasks", body_html, "/tasks")


def render_epics_page(epics: list[Epic]) -> str:
    cards_html = "".join([render_epic_card(epic) for epic in sorted(epics, key=lambda value: value.id)])
    body_html = f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <h1>Epics</h1>
        <p class=\"section-description\">Major implementation tracks connected to tasks.</p>
      </header>
      <div class=\"entity-grid\">{cards_html}</div>
    </section>
    """
    return render_page("Epics", body_html, "/epics")


def render_tickets_page(tickets: list[Ticket]) -> str:
    cards_html = "".join(
        [render_ticket_card(ticket, include_epic=True) for ticket in sorted(tickets, key=lambda value: value.id)]
    )
    body_html = f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <h1>Tickets</h1>
        <p class=\"section-description\">Actionable units of work with dependencies and scope.</p>
      </header>
      <div class=\"toolbar\">
        <input id=\"search-input\" class=\"search-input\" type=\"search\" placeholder=\"Search by id or title\" aria-label=\"Search tickets\" />
        <div class=\"status-filters\">
          <button class=\"chip is-active\" data-status-filter=\"all\" type=\"button\">All</button>
          <button class=\"chip\" data-status-filter=\"open\" type=\"button\">Open</button>
          <button class=\"chip\" data-status-filter=\"in_progress\" type=\"button\">In progress</button>
          <button class=\"chip\" data-status-filter=\"blocked\" type=\"button\">Blocked</button>
          <button class=\"chip\" data-status-filter=\"closed\" type=\"button\">Closed</button>
        </div>
      </div>
      <div class=\"entity-grid js-filter-grid\">{cards_html}</div>
      <p class=\"empty-note js-empty-note\" hidden>No tickets match the current filters.</p>
    </section>
    """
    return render_page("Tickets", body_html, "/tickets")


def render_task_detail_page(task: Task) -> str:
    body_html = render_detail_layout(
        "Task",
        task.id,
        task.title,
        task.status,
        [
            render_detail_row("Description", paragraphize(task.description)),
            render_detail_row("Acceptance Criteria", render_list(task.acceptance_criteria)),
        ],
    )
    return render_page(f"Task {task.id}", body_html, "/tasks")


def render_epic_detail_page(epic: Epic) -> str:
    body_html = render_detail_layout(
        "Epic",
        epic.id,
        epic.title,
        epic.status,
        [
            render_detail_row(
                "Task", f'<a class="inline-link" href="/task/{escape(epic.task)}">{escape(epic.task)}</a>'
            ),
            render_detail_row("Description", paragraphize(epic.description)),
            render_detail_row("Acceptance Criteria", render_list(epic.acceptance_criteria)),
        ],
    )
    return render_page(f"Epic {epic.id}", body_html, "/epics")


def render_ticket_detail_page(ticket: Ticket) -> str:
    dependency_html = render_dependency_links(ticket.depends_on)
    rows = [
        render_detail_row(
            "Epic", f'<a class="inline-link" href="/epic/{escape(ticket.epic)}">{escape(ticket.epic)}</a>'
        ),
        render_detail_row("Depends On", dependency_html),
        render_detail_row("Description", paragraphize(ticket.description)),
        render_detail_row("Acceptance Criteria", render_list(ticket.acceptance_criteria)),
        render_detail_row("Out Of Scope", render_list(ticket.out_of_scope)),
    ]
    if ticket.completion_notes:
        rows.append(render_detail_row("Completion Notes", paragraphize(ticket.completion_notes)))

    body_html = render_detail_layout("Ticket", ticket.id, ticket.title, ticket.status, rows)
    return render_page(f"Ticket {ticket.id}", body_html, "/tickets")


def render_not_found_page(request_path: str) -> str:
    body_html = f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <h1>Not Found</h1>
      </header>
      <p class=\"section-description\">No route matches <code>{escape(request_path)}</code>.</p>
      <p><a class=\"inline-link\" href=\"/\">Return to dashboard</a></p>
    </section>
    """
    return render_page("Not Found", body_html, "")


def render_error_page(error_message: str) -> str:
    body_html = f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <h1>Repository Error</h1>
      </header>
      <p class=\"section-description\">The ticket repository could not be loaded.</p>
      <pre class=\"error-block\">{escape(error_message)}</pre>
    </section>
    """
    return render_page("Repository Error", body_html, "")


def render_page(page_title: str, body_html: str, active_path: str) -> str:
    nav_html = "".join([render_nav_link(path, label, active_path) for path, label in NAV_LINKS])
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(page_title)} | Tickets</title>
  <style>{build_styles()}</style>
</head>
<body>
  <div class=\"background-aura\" aria-hidden=\"true\"></div>
  <div class=\"layout\">
    <header class=\"site-header\">
      <a class=\"site-title\" href=\"/\">Tickets</a>
      <nav class=\"main-nav\">{nav_html}</nav>
    </header>
    <main>{body_html}</main>
  </div>
  <script>{build_script()}</script>
</body>
</html>
"""


def render_nav_link(path: str, label: str, active_path: str) -> str:
    class_name = "nav-link is-active" if path == active_path else "nav-link"
    return f'<a class="{class_name}" href="{path}">{escape(label)}</a>'


def render_stat_card(label: str, value: int, link_path: str, accent_color: str) -> str:
    return (
        '<a class="stat-card" href="'
        f'{link_path}" style="--stat-accent:{accent_color};">'
        f'<span class="stat-label">{escape(label)}</span>'
        f'<strong class="stat-value">{value}</strong>'
        "</a>"
    )


def render_next_ticket_panel(next_ticket: Ticket | None) -> str:
    if next_ticket is None:
        return """
        <article class=\"next-ticket-panel\">
          <p>All tickets are complete or waiting on dependencies.</p>
        </article>
        """

    return f"""
    <article class=\"next-ticket-panel\">
      <div>
        <p class=\"eyebrow\">Recommended next ticket</p>
        <h3><a class=\"inline-link\" href=\"/ticket/{escape(next_ticket.id)}\">{escape(next_ticket.id)}: {escape(next_ticket.title)}</a></h3>
      </div>
      <span class=\"status-pill status-{escape(next_ticket.status)}\">{escape(status_label(next_ticket.status))}</span>
    </article>
    """


def render_task_card(task: Task) -> str:
    return f"""
    <article class=\"entity-card\" data-status=\"{escape(task.status)}\" data-search=\"{escape((task.id + " " + task.title).lower())}\">
      <header class=\"card-header\">
        <a class=\"entity-id\" href=\"/task/{escape(task.id)}\">{escape(task.id)}</a>
        <span class=\"status-pill status-{escape(task.status)}\">{escape(status_label(task.status))}</span>
      </header>
      <h3>{escape(task.title)}</h3>
      <p>{escape(compact_text(task.description))}</p>
    </article>
    """


def render_epic_card(epic: Epic) -> str:
    return f"""
    <article class=\"entity-card\" data-status=\"{escape(epic.status)}\" data-search=\"{escape((epic.id + " " + epic.title).lower())}\">
      <header class=\"card-header\">
        <a class=\"entity-id\" href=\"/epic/{escape(epic.id)}\">{escape(epic.id)}</a>
        <span class=\"status-pill status-{escape(epic.status)}\">{escape(status_label(epic.status))}</span>
      </header>
      <p class=\"meta-link\">Task <a class=\"inline-link\" href=\"/task/{escape(epic.task)}\">{escape(epic.task)}</a></p>
      <h3>{escape(epic.title)}</h3>
      <p>{escape(compact_text(epic.description))}</p>
    </article>
    """


def render_ticket_card(ticket: Ticket, include_epic: bool) -> str:
    dependency_text = ", ".join(ticket.depends_on) if ticket.depends_on else "none"
    epic_meta_html = ""
    if include_epic:
        epic_meta_html = f'<p class="meta-link">Epic <a class="inline-link" href="/epic/{escape(ticket.epic)}">{escape(ticket.epic)}</a></p>'

    return f"""
    <article class=\"entity-card\" data-status=\"{escape(ticket.status)}\" data-search=\"{escape((ticket.id + " " + ticket.title).lower())}\">
      <header class=\"card-header\">
        <a class=\"entity-id\" href=\"/ticket/{escape(ticket.id)}\">{escape(ticket.id)}</a>
        <span class=\"status-pill status-{escape(ticket.status)}\">{escape(status_label(ticket.status))}</span>
      </header>
      {epic_meta_html}
      <h3>{escape(ticket.title)}</h3>
      <p class=\"meta-line\">Depends on: {escape(dependency_text)}</p>
      <p>{escape(compact_text(ticket.description))}</p>
    </article>
    """


def render_detail_layout(entity_name: str, entity_id: str, title: str, status: str, rows: list[str]) -> str:
    rows_html = "".join(rows)
    return f"""
    <section class=\"section-block\">
      <header class=\"section-header\">
        <p class=\"eyebrow\">{escape(entity_name)}</p>
        <h1>{escape(entity_id)}: {escape(title)}</h1>
        <span class=\"status-pill status-{escape(status)}\">{escape(status_label(status))}</span>
      </header>
      <article class=\"detail-card\">{rows_html}</article>
    </section>
    """


def render_detail_row(label: str, value_html: str) -> str:
    return f"""
    <section class=\"detail-row\">
      <h2>{escape(label)}</h2>
      <div class=\"detail-value\">{value_html}</div>
    </section>
    """


def render_list(values: list[str]) -> str:
    if not values:
        return '<p class="muted">None</p>'

    item_html = "".join([f"<li>{escape(value)}</li>" for value in values])
    return f"<ul>{item_html}</ul>"


def render_dependency_links(dependency_ids: list[str]) -> str:
    if not dependency_ids:
        return '<p class="muted">None</p>'

    links = [
        f'<a class="inline-link" href="/ticket/{escape(dependency_id)}">{escape(dependency_id)}</a>'
        for dependency_id in dependency_ids
    ]
    return "<p>" + ", ".join(links) + "</p>"


def paragraphize(text_value: str) -> str:
    lines = [line.strip() for line in text_value.splitlines() if line.strip()]
    if not lines:
        return '<p class="muted">None</p>'
    return "".join([f"<p>{escape(line)}</p>" for line in lines])


def compact_text(text_value: str) -> str:
    normalized = " ".join([segment.strip() for segment in text_value.splitlines() if segment.strip()])
    if len(normalized) <= 140:
        return normalized
    return normalized[:137] + "..."


def count_tickets_by_status(tickets: list[Ticket], target_status: str) -> int:
    return sum(1 for ticket in tickets if ticket.status == target_status)


def status_label(status_value: str) -> str:
    return STATUS_LABELS.get(status_value, status_value)


def build_styles() -> str:
    return """
:root {
  --page-bg: #fffdf8;
  --surface: #ffffff;
  --surface-soft: #f8f4ff;
  --text-main: #283237;
  --text-muted: #66767f;
  --border-soft: #eadff0;
  --accent: #5e7e8d;
  --accent-soft: #d7eff9;
  --open-bg: #e8f8ed;
  --open-text: #20603d;
  --progress-bg: #fff2d7;
  --progress-text: #8f5a17;
  --blocked-bg: #ffe8ea;
  --blocked-text: #8d3040;
  --closed-bg: #eceff3;
  --closed-text: #4d5a65;
  --shadow-soft: 0 14px 40px rgba(82, 90, 119, 0.08);
  --radius-large: 20px;
  --radius-medium: 14px;
  --radius-small: 10px;
}

* {
  box-sizing: border-box;
}

[hidden] {
  display: none !important;
}

body {
  margin: 0;
  color: var(--text-main);
  background: radial-gradient(circle at 10% -5%, #fff1db 0%, transparent 42%),
    radial-gradient(circle at 95% 5%, #e6f8ff 0%, transparent 38%),
    var(--page-bg);
  font-family: "Avenir Next", "Segoe UI", "Trebuchet MS", sans-serif;
  line-height: 1.5;
}

h1,
h2,
h3 {
  margin: 0;
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  letter-spacing: 0.01em;
}

p {
  margin: 0;
}

.background-aura {
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(130deg, rgba(255, 255, 255, 0.4), transparent 45%);
}

.layout {
  width: min(1100px, calc(100% - 2.5rem));
  margin: 2.25rem auto 4rem;
}

.site-header {
  position: sticky;
  top: 1.25rem;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(234, 223, 240, 0.85);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft);
}

.site-title {
  font-family: "Iowan Old Style", "Palatino Linotype", serif;
  color: var(--text-main);
  font-size: 1.25rem;
  text-decoration: none;
}

.main-nav {
  display: flex;
  gap: 0.4rem;
}

.nav-link {
  color: var(--text-muted);
  text-decoration: none;
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  transition: background-color 180ms ease, color 180ms ease, transform 220ms ease;
}

.nav-link:hover {
  color: var(--text-main);
  background: #f6f1ff;
  transform: translateY(-1px);
}

.nav-link.is-active {
  color: #30495a;
  background: #e8f2fb;
}

main {
  display: grid;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.hero {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-large);
  background: linear-gradient(130deg, rgba(255, 248, 232, 0.8), rgba(236, 245, 255, 0.78));
  box-shadow: var(--shadow-soft);
  padding: 2.2rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  animation: rise-in 500ms ease;
}

.hero h1 {
  font-size: clamp(1.8rem, 2.6vw, 2.5rem);
}

.hero-text {
  margin-top: 0.75rem;
  color: var(--text-muted);
  max-width: 62ch;
}

.hero-meta {
  align-self: flex-start;
  font-size: 0.92rem;
  color: #4f6d7b;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(161, 198, 216, 0.58);
  padding: 0.4rem 0.75rem;
  white-space: nowrap;
}

.section-block {
  display: grid;
  gap: 1rem;
}

.section-header {
  display: grid;
  gap: 0.55rem;
}

.section-description {
  color: var(--text-muted);
}

.stats-grid,
.entity-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
}

.stat-card,
.entity-card,
.next-ticket-panel,
.detail-card {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-medium);
  background: var(--surface);
  box-shadow: var(--shadow-soft);
}

.stat-card {
  text-decoration: none;
  color: inherit;
  display: grid;
  gap: 0.45rem;
  padding: 1rem;
  border-top: 5px solid var(--stat-accent);
  transition: transform 200ms ease, box-shadow 200ms ease;
  animation: rise-in 420ms ease both;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 18px 32px rgba(101, 95, 126, 0.14);
}

.stat-label {
  color: var(--text-muted);
}

.stat-value {
  font-size: 1.7rem;
  line-height: 1;
}

.next-ticket-panel {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1.1rem 1.2rem;
  animation: rise-in 500ms ease;
}

.eyebrow {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #617688;
}

.inline-link {
  color: #315d74;
  text-decoration: none;
  border-bottom: 1px solid rgba(49, 93, 116, 0.26);
  transition: border-color 160ms ease, color 160ms ease;
}

.inline-link:hover {
  color: #1d4960;
  border-color: rgba(29, 73, 96, 0.66);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  justify-content: space-between;
  align-items: center;
}

.search-input {
  border: 1px solid #dfe6ea;
  border-radius: 999px;
  padding: 0.6rem 0.95rem;
  min-width: min(100%, 24rem);
  background: #ffffff;
  color: var(--text-main);
}

.search-input:focus {
  outline: 2px solid #d4ecfb;
  outline-offset: 1px;
}

.status-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.chip {
  border: 1px solid #dce6eb;
  background: #ffffff;
  color: #4c606d;
  border-radius: 999px;
  padding: 0.4rem 0.78rem;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background-color 160ms ease;
}

.chip:hover {
  transform: translateY(-1px);
  border-color: #b7d4e2;
}

.chip.is-active {
  background: #e6f3ff;
  border-color: #b6d4ec;
  color: #345166;
}

.entity-card {
  display: grid;
  gap: 0.6rem;
  padding: 1rem;
  transition: transform 230ms ease, box-shadow 230ms ease;
  animation: rise-in 540ms ease both;
}

.entity-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 34px rgba(102, 92, 126, 0.15);
}

.entity-grid .entity-card:nth-child(2) {
  animation-delay: 40ms;
}

.entity-grid .entity-card:nth-child(3) {
  animation-delay: 80ms;
}

.entity-grid .entity-card:nth-child(4) {
  animation-delay: 120ms;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.entity-id {
  color: var(--text-main);
  text-decoration: none;
  font-weight: 600;
}

.meta-link,
.meta-line {
  color: var(--text-muted);
  font-size: 0.92rem;
}

.status-pill {
  font-size: 0.76rem;
  padding: 0.23rem 0.58rem;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.status-open {
  background: var(--open-bg);
  color: var(--open-text);
}

.status-in_progress {
  background: var(--progress-bg);
  color: var(--progress-text);
}

.status-blocked {
  background: var(--blocked-bg);
  color: var(--blocked-text);
}

.status-closed {
  background: var(--closed-bg);
  color: var(--closed-text);
}

.detail-card {
  padding: 1rem 1.2rem;
  display: grid;
  gap: 1rem;
}

.detail-row {
  display: grid;
  gap: 0.45rem;
}

.detail-row h2 {
  font-size: 1.05rem;
}

.detail-value p + p,
.detail-value ul {
  margin-top: 0.5rem;
}

.detail-value ul {
  padding-left: 1.2rem;
}

.muted,
.empty-note {
  color: var(--text-muted);
}

.error-block {
  background: #fff3f4;
  border: 1px solid #f0d9dc;
  border-radius: var(--radius-small);
  padding: 0.9rem;
  overflow-x: auto;
}

@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 760px) {
  .layout {
    width: min(1100px, calc(100% - 1.25rem));
    margin-top: 1.15rem;
  }

  .site-header {
    border-radius: var(--radius-medium);
    position: static;
    flex-direction: column;
    align-items: flex-start;
  }

  .hero {
    padding: 1.35rem;
    flex-direction: column;
  }

  .toolbar {
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }
}
"""


def build_script() -> str:
    return """
(function () {
  var grid = document.querySelector('.js-filter-grid');
  if (!grid) {
    return;
  }

  var cards = Array.from(grid.querySelectorAll('.entity-card'));
  var chips = Array.from(document.querySelectorAll('.chip[data-status-filter]'));
  var searchInput = document.getElementById('search-input');
  var emptyNote = document.querySelector('.js-empty-note');
  var activeStatus = 'all';

  function applyFilters() {
    var searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';
    var visibleCount = 0;

    cards.forEach(function (card) {
      var cardStatus = card.getAttribute('data-status') || '';
      var cardSearch = card.getAttribute('data-search') || '';
      var statusMatch = activeStatus === 'all' || cardStatus === activeStatus;
      var searchMatch = searchTerm.length === 0 || cardSearch.indexOf(searchTerm) >= 0;
      var isVisible = statusMatch && searchMatch;
      card.hidden = !isVisible;
      if (isVisible) {
        visibleCount += 1;
      }
    });

    if (emptyNote) {
      emptyNote.hidden = visibleCount > 0;
    }
  }

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      activeStatus = chip.getAttribute('data-status-filter') || 'all';
      chips.forEach(function (currentChip) {
        currentChip.classList.toggle('is-active', currentChip === chip);
      });
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', applyFilters);
  }

  applyFilters();
})();
"""
