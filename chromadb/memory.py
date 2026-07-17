import os

import anthropic
import chromadb

MODEL = "claude-opus-4-8"

BASE_SYSTEM_PROMPT = """\
You are the A-Global Knowledge Assistant, a helpful agent that answers \
student questions about A-Global's FAQs, courses, and policies.

Answer using ONLY the context provided below. If the context does not \
contain enough information to answer, say so plainly and suggest the \
student contact A-Global student support instead of guessing.
"""

client = chromadb.Client()
collection = client.create_collection("aglobal_knowledge_base")

collection.add(
    ids=[
        "faq_1",
        "faq_2",
        "faq_3",
        "course_1",
        "course_2",
        "course_3",
        "policy_1",
        "policy_2",
        "policy_3",
        "policy_4",
    ],
    documents=[
        "How do I reset my A-Global student portal password? Click 'Forgot Password' on the login page and follow the email instructions sent to your registered address.",
        "What are the office hours for student support? Student support is available Monday to Friday, 9:00 AM to 5:00 PM, via live chat, email, or phone.",
        "How do I apply for a transcript? Submit a transcript request through the student portal under 'Academic Records'; processing takes 3-5 business days.",
        "Introduction to Artificial Intelligence (ATC200) covers the foundations of AI, including search algorithms, knowledge representation, and machine learning basics.",
        "Data Structures and Algorithms (CSC210) teaches core data structures such as arrays, linked lists, trees, and graphs, along with algorithm design and analysis.",
        "Business Communication (BUS150) develops professional writing, presentation, and interpersonal communication skills for the workplace.",
        "Attendance Policy: Students must maintain at least 75% attendance in each course to be eligible to sit for final examinations.",
        "Academic Integrity Policy: Plagiarism, cheating, or any form of academic dishonesty may result in disciplinary action, including suspension or expulsion.",
        "Refund Policy: Tuition refunds are processed according to the withdrawal date; full refunds are only available within the first two weeks of the semester.",
        "Late Submission Policy: Assignments submitted after the deadline incur a 10% grade deduction per day, up to a maximum of five days late.",
    ],
    metadatas=[
        {"type": "faq", "topic": "account_access"},
        {"type": "faq", "topic": "student_support"},
        {"type": "faq", "topic": "academic_records"},
        {"type": "course", "code": "ATC200"},
        {"type": "course", "code": "CSC210"},
        {"type": "course", "code": "BUS150"},
        {"type": "policy", "category": "attendance"},
        {"type": "policy", "category": "academic_integrity"},
        {"type": "policy", "category": "refunds"},
        {"type": "policy", "category": "late_submission"},
    ],
)


def retrieve_context(query: str, n_results: int = 3) -> str:
    results = collection.query(query_texts=[query], n_results=n_results)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_blocks = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas), start=1):
        context_blocks.append(f"[{i}] ({meta}) {doc}")

    return "\n\n".join(context_blocks)


def build_system_prompt(query: str, n_results: int = 3) -> str:
    context = retrieve_context(query, n_results=n_results)
    if not context:
        context = "No relevant context was found in the knowledge base."
    return f"{BASE_SYSTEM_PROMPT}\nContext:\n{context}"


def ask_agent(query: str, model: str = MODEL) -> str:
    """Retrieve context for `query` and answer it via the Anthropic API."""
    system_prompt = build_system_prompt(query)
    llm_client = anthropic.Anthropic()
    response = llm_client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": query}],
    )
    return next((b.text for b in response.content if b.type == "text"), "").strip()


def _run_demo() -> None:
    """Exercise the agent on queries that match stored docs and ones that don't."""
    test_queries = [
        "How do I reset my password?",           # matches faq_1
        "What is ATC200 about?",                  # matches course_1
        "What happens if I submit an assignment late?",  # matches policy_4
        "What's the best pizza topping?",         # no relevant match
        "Can you help me plan a trip to Mars?",   # no relevant match
    ]

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_api_key:
        print("ANTHROPIC_API_KEY not set — showing retrieved context only.\n")

    for query in test_queries:
        print(f"Query: {query}")
        if has_api_key:
            print(f"Agent: {ask_agent(query)}\n")
        else:
            print(f"Retrieved context:\n{retrieve_context(query)}\n")


if __name__ == "__main__":
    _run_demo()
