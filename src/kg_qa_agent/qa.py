from __future__ import annotations

from .config import Settings, settings
from .graph import Neo4jGraphStore
from .llm import ChatClient
from .models import Answer, Evidence
from .utils import extract_json_object


def extract_search_terms(question: str, client: ChatClient) -> list[str]:
    response = client.complete(
        [
            {
                "role": "system",
                "content": "Extract the smallest useful list of entity names or keywords for graph retrieval. Return JSON only.",
            },
            {
                "role": "user",
                "content": f'Question: {question}\nReturn: {{"terms": ["..."]}}',
            },
        ],
        temperature=0.0,
    )
    payload = extract_json_object(response)
    return [str(term).strip() for term in payload.get("terms", []) if str(term).strip()]


def answer_question(
    question: str,
    store: Neo4jGraphStore,
    client: ChatClient,
    config: Settings = settings,
) -> Answer:
    terms = extract_search_terms(question, client)
    rows = store.retrieve(terms, limit=config.retrieval_limit)
    evidence = [Evidence(**row) for row in rows]
    if not evidence:
        return Answer(
            question=question,
            answer="The knowledge graph does not contain enough evidence to answer this question.",
            evidence=[],
        )
    context = "\n".join(
        f"[{index}] {item.subject} --{item.predicate}--> {item.object}"
        for index, item in enumerate(evidence, start=1)
    )
    prompt = f"""Answer the question using only the graph evidence below.
If the evidence is insufficient, state that clearly. Do not add unsupported facts.
Cite supporting evidence with bracket numbers such as [1].

Question: {question}

Graph evidence:
{context}
"""
    answer_text = client.complete(
        [
            {"role": "system", "content": "You are a grounded knowledge-graph question-answering agent."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    return Answer(question=question, answer=answer_text.strip(), evidence=evidence)

