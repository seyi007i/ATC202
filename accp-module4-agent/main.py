import os
import re
import sys

import anthropic
from ddgs import DDGS

MODEL = "claude-opus-4-8"
MAX_UNCONFIRMED_SEARCHES = 3

SYSTEM_PROMPT = """You are a research assistant that answers questions using the ReAct \
(Reasoning + Acting) pattern.

You have access to one tool:

  search[query] - Searches the web via DuckDuckGo and returns short summaries of the \
top results for "query".

Always respond using exactly this format, one field per line, and nothing else:

Thought: <your reasoning about what to do next>
Action: search
Action Input: <the exact search query>

After a search, you will be given an Observation with the results. Keep alternating \
Thought / Action / Action Input turns until you have enough information to answer. \
When you are ready, respond instead with:

Thought: <your final reasoning>
Final Answer: <a complete, well-supported answer to the original question>

Output only one Thought/Action/Action Input block, or one Thought/Final Answer block, \
per response. Never write the Observation yourself - it will be provided to you.
"""

FINAL_ANSWER_RE = re.compile(r"Final Answer:\s*(.+)", re.DOTALL)
ACTION_INPUT_RE = re.compile(r"Action Input:\s*(.+)")


def search_web(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return a numbered summary of the top results."""
    # backend="html" is used because the default "auto" backend silently
    # returns an empty result list in some network environments.
    results = DDGS().text(query, max_results=max_results, backend="html")
    if not results:
        return "No results found."

    lines = []
    for i, result in enumerate(results, start=1):
        title = result.get("title", "").strip()
        body = result.get("body", "").strip()
        href = result.get("href", "").strip()
        lines.append(f"{i}. {title}\n   {body}\n   {href}")
    return "\n".join(lines)


def extract_final_answer(text: str) -> str | None:
    match = FINAL_ANSWER_RE.search(text)
    return match.group(1).strip() if match else None


def extract_action_input(text: str) -> str | None:
    match = ACTION_INPUT_RE.search(text)
    return match.group(1).strip() if match else None


def confirm_continue(search_count: int) -> bool:
    """Ask the human whether to allow another search once the free quota is used up."""
    reply = input(
        f"\nThe agent has already made {search_count} search calls and wants to make "
        "another. Allow it? [y/N] "
    ).strip().lower()
    return reply in ("y", "yes")


def run_react_agent(question: str, model: str = MODEL, max_steps: int = 6) -> str:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Question: {question}"}]
    search_count = 0

    for step in range(1, max_steps + 1):
        print(f"--- Step {step} ---")
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            stop_sequences=["Observation:"],
        )
        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        print(text)
        messages.append({"role": "assistant", "content": text})

        final_answer = extract_final_answer(text)
        if final_answer:
            return final_answer

        query = extract_action_input(text)
        if not query:
            messages.append({
                "role": "user",
                "content": (
                    "Please respond using the Thought/Action/Action Input format, "
                    "or Thought/Final Answer if you already know the answer."
                ),
            })
            continue

        if search_count >= MAX_UNCONFIRMED_SEARCHES and not confirm_continue(search_count):
            return "Stopped at the user's request after reaching the search call limit."

        search_count += 1
        observation = search_web(query)
        print(f"Observation: {observation}\n")
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "I was unable to reach a final answer within the allotted steps."


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set the ANTHROPIC_API_KEY environment variable before running this agent.")
        return

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = input("Research question: ").strip()
    if not question:
        print("No question provided.")
        return

    answer = run_react_agent(question)
    print("\n=== Final Answer ===")
    print(answer)


if __name__ == "__main__":
    main()
