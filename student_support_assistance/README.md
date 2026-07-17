# Student Support Assistant

A production-quality Python agent that answers student FAQs, checks
enrollment status, and escalates complex requests to a human advisor. Built
using a lightweight Agent SDK pattern (Agent + Tool registry + intent
router) inspired by the OpenAI Agents SDK, but fully local and
deterministic — no API key or network access required.

## Project Overview

The assistant automatically decides which of three tools to invoke based on
a student's message:

| Tool                       | Used for                                                            |
| --------------------------- | -------------------------------------------------------------------- |
| `search_knowledge_base`     | FAQs — tuition, deadlines, registration, campus, admissions, etc.   |
| `check_enrollment_status`   | "Am I enrolled?", "What courses am I taking?"                       |
| `escalate_to_advisor`       | Complaints, appeals, disputes, or explicit requests for a human      |

Routing is done by a deterministic keyword-based classifier
(`utils.classify_intent`), with escalation keywords taking priority over
enrollment keywords, which take priority over the knowledge-base fallback.
This keeps behavior fast, free, and fully unit-testable offline.

## Architecture

```
student_support_assistance/
│
├── agent.py            # AgentTool, StudentSupportAgent, intent routing (the "Runner")
├── tools.py             # The 3 tool implementations (search / enrollment / escalation)
├── knowledge_base.py    # FAQ search/scoring implementation
├── data.py              # Mock knowledge base + mock student records
├── models.py            # Dataclasses (FAQEntry, StudentRecord, ...) + structured exceptions
├── prompts.py           # System prompt
├── config.py            # Tunable constants (top_k, keyword lists, file paths, ...)
├── utils.py             # Validation, tokenization, intent classification, logging setup
├── tests/
│   ├── test_search.py   # Knowledge-base search tests
│   ├── test_tools.py    # Tool-level tests (enrollment, escalation, search)
│   └── test_agent.py    # Agent routing + error-handling tests
├── requirements.txt
└── README.md
```

**Design notes**

- **Models**: All data contracts (`FAQEntry`, `StudentRecord`,
  `EscalationTicket`, `AgentResponse`, ...) are immutable `@dataclass`
  types in `models.py`, along with a small structured exception hierarchy
  (`StudentSupportError` → `InvalidInputError` / `EmptyQueryError`,
  `StudentNotFoundError`, `TicketWriteError`, `KnowledgeBaseError`).
- **Dependency injection**: `search_faqs()` accepts an injectable
  `knowledge_base` parameter, `escalate_to_advisor()` accepts an injectable
  `tickets_file` path, and `StudentSupportAgent` accepts an injectable
  `tools` registry — all so tests can swap in fakes/temp files without
  monkeypatching internals.
- **Error handling**: Every tool validates its inputs and raises a
  specific, structured exception (never a bare `Exception`). The agent
  catches domain errors (e.g. `StudentNotFoundError`) *and* unexpected
  runtime exceptions per tool call, and always converts them into a
  polite, human-readable message instead of crashing.
- **Logging**: A shared logger (`utils.setup_logging`) records every tool
  invocation and warning/error condition.

## Installation

Requires Python 3.12+ (tested on 3.14).

```bash
cd student_support_assistance
pip install -r requirements.txt
```

No API keys or external services are required — everything runs locally.

## Dependencies

- [`pytest`](https://pytest.org) — test runner
- [`pytest-cov`](https://pytest-cov.readthedocs.io) — coverage reporting

(The application itself uses only the Python standard library.)

## How to Run

Run the built-in demo, which exercises all three tools end-to-end:

```bash
python -m student_support_assistance.agent
```

Or use the agent programmatically — see [Example API Usage](#example-api-usage) below.

## How to Run Tests

From the directory **containing** `student_support_assistance/` (i.e. one level
above it):

```bash
pytest student_support_assistance/tests -v
```

With coverage:

```bash
pytest student_support_assistance/tests --cov=student_support_assistance --cov-report=term-missing
```

The suite currently has 59 tests covering FAQ search, enrollment lookup,
escalation ticket creation, invalid/malformed input, missing parameters,
nonexistent student IDs, empty queries, file I/O errors, agent routing, and
unexpected runtime exceptions, at 100% statement coverage of the
application modules.

## Example API Usage

```python
from student_support_assistance.agent import StudentSupportAgent

agent = StudentSupportAgent()

# Knowledge base
response = agent.run("When is course registration?")
print(response.tool_used)  # "search_knowledge_base"
print(response.message)

# Enrollment (student ID can be passed explicitly or embedded in the message)
response = agent.run("Check enrollment for student S1001")
print(response.data)  # {"student_id": "S1001", "status": "Enrolled", "courses": [...]}

# Escalation
response = agent.run("I want to appeal my tuition decision.", student_id="S1001")
print(response.data)  # {"ticket_id": "...", "status": "created"}
```

Tools can also be called directly, without going through the agent:

```python
from student_support_assistance.tools import (
    check_enrollment_status,
    escalate_to_advisor,
    search_knowledge_base,
)

results = search_knowledge_base("How do I pay tuition?")
record = check_enrollment_status("S1001")
ticket = escalate_to_advisor("S1001", "Disputing a late fee charge")
```

## Sample Conversations

**Knowledge base**

```
User: When is course registration?
Agent [search_knowledge_base]: Course registration for the upcoming semester
opens four weeks before the term starts and closes one week after classes
begin. Check the academic calendar on the student portal for exact dates.
```

**Enrollment**

```
User: Check enrollment for student S1001
Agent [check_enrollment_status]: Your enrollment status is 'Enrolled'.
Courses: Python Programming, Data Structures.
```

**Escalation**

```
User: I want to appeal my tuition decision.
Agent [escalate_to_advisor]: I've created support ticket
ff62b357-dffb-4468-82ad-9fbb52d8f7f4 and a human advisor will follow up
with you soon.
```

**Error handling — unknown student ID**

```
User: Check my enrollment for S9999
Agent [check_enrollment_status]: I'm sorry, I couldn't find a student with
ID 'S9999'. Please double-check the ID and try again.
```

**Error handling — missing student ID before escalation**

```
User: I have a complaint about my professor.
Agent [none]: I'd like to connect you with a human advisor. Could you
first share your student ID so I can open a ticket for you?
```

## Support Ticket Storage

Escalated requests are appended, one per line, to `support_tickets.txt`
(created next to `config.py` on first use). Each line records the ticket
ID, student ID, status, and query summary. This path is configurable via
`config.SUPPORT_TICKETS_FILE` and injectable per-call via
`escalate_to_advisor(..., tickets_file=...)`.
