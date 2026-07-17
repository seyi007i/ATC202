# ReAct Research Agent

A minimal ReAct (Reasoning + Acting) agent built on the Claude API. The agent
alternates between reasoning and issuing web searches (via DuckDuckGo) until
it has enough information to give a final answer.

## Setup

```bash
pip install -r requirements.txt
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your-key-here   # macOS/Linux
$env:ANTHROPIC_API_KEY = "your-key-here" # Windows PowerShell
```

## Usage

```bash
python main.py "your research question"
```

Or run it without arguments to be prompted for a question:

```bash
python main.py
```

## How it works

1. The agent receives your question and responds with a `Thought` /
   `Action` / `Action Input` block, where the action is a web search.
2. `main.py` executes the search and feeds the results back as an
   `Observation`.
3. This repeats until the agent responds with a `Thought` / `Final Answer`
   block instead, which is printed as the result.

The loop runs for at most 6 steps (`max_steps` in `run_react_agent`) to
avoid going on indefinitely.

## Human-in-the-loop confirmation

To prevent runaway execution, the agent may make up to
`MAX_UNCONFIRMED_SEARCHES` (default: 3) search calls automatically. Beyond
that, it pauses before each additional search and asks you to confirm:

```
The agent has already made 3 search calls and wants to make another. Allow it? [y/N]
```

Answering anything other than `y`/`yes` stops the run.
