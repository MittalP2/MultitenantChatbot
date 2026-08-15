"""
Answer questions using retrieved BMW document chunks.

Answer providers (first match wins):
1. Cursor SDK  — CURSOR_API_KEY
2. OpenAI      — OPENAI_API_KEY (optional later)
3. Ollama      — local model if running
4. Extractive  — no-API fallback from retrieved passages
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from retrieval.retriever import retrieve

SYSTEM_PROMPT = """You are a BMW financial assistant.
Answer ONLY using the provided context from BMW investor reports.
If the context does not contain the answer, say you don't know.
Be concise. Include specific figures when present in the context.
Cite the document name and page for key figures.
"""


def build_context(chunks: List[Dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[{i}] Source: {c['document']} (page {c['page']})\n{c['text']}"
        )
    return "\n\n".join(parts)


def _years_in_text(text: str) -> List[str]:
    return re.findall(r"\b(20[2-3][0-9])\b", text)


def _split_sentences(text: str) -> List[str]:
    rough = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in rough if s and s.strip()]


def _score_snippet(question: str, snippet: str) -> float:
    q_tokens = set(re.findall(r"[a-z0-9]+", question.lower()))
    for t in list(q_tokens):
        if t.startswith("employ"):
            q_tokens.update({"employee", "employees"})
    s_tokens = set(re.findall(r"[a-z0-9]+", snippet.lower()))
    if not q_tokens or not s_tokens:
        return 0.0
    overlap = len(q_tokens & s_tokens) / len(q_tokens)
    years = set(_years_in_text(question))
    year_hit = 1.0 if years and any(y in snippet for y in years) else 0.0
    has_number = 1.0 if re.search(r"\d", snippet) else 0.0
    kpi_hit = 1.0 if re.search(
        r"employees at year|profit/?loss before tax|profit before tax|group revenues|"
        r"ebit margin|free cash flow|deliveries|dividend|all-?electric|"
        r"key performance indicators",
        snippet,
        re.I,
    ) else 0.0
    penalty = 0.0
    if q_tokens & {"employee", "employees", "headcount", "workforce"}:
        if re.search(r"work[\s-]*related|accident|fatalit", snippet, re.I):
            penalty += 0.8
        if re.search(r"employees by (contract|geographical)", snippet, re.I):
            penalty += 0.4
    return overlap + 0.35 * year_hit + 0.25 * has_number + 0.55 * kpi_hit - penalty


def _format_kpi_answer(question: str, chunks: List[Dict]) -> Optional[str]:
    years = _years_in_text(question)
    year = years[0] if years else None
    q = question.lower()
    num = r"\d{1,3}(?:\s*,\s*\d{3})+"

    patterns: List[Tuple[Tuple[str, ...], str, str]] = [
        (
            ("employee", "employees", "headcount", "workforce", "personnel", "staff"),
            rf"Employees at year\s*-?\s*end\d*\s*((?:{num}\s*)+)",
            "Employees at year-end",
        ),
        (
            ("revenue", "revenues"),
            rf"Group revenues\s*((?:{num}\s*)+)",
            "Group revenues",
        ),
        (
            ("profit", "ebt"),
            rf"Profit/?loss before tax(?:\s+in\s+€\s*million)?\s*((?:{num}\s*)+)",
            "Profit/loss before tax",
        ),
    ]

    for triggers, regex, label in patterns:
        if not any(t in q for t in triggers):
            continue
        for c in chunks:
            text = c["text"]
            m = re.search(regex, text, re.I)
            if not m:
                m2 = re.search(
                    rf"employed\s+({num}|\d+)\s+people\s+worldwide",
                    text,
                    re.I,
                )
                if label == "Employees at year-end" and m2:
                    value = re.sub(r"\s*,\s*", ",", m2.group(1))
                    value = re.sub(r"\s+", "", value)
                    return (
                        f"According to {c['document']} (page {c['page']}), "
                        f"the BMW Group employed {value} people worldwide"
                        + (f" at year-end {year}." if year else ".")
                    )
                m3 = re.search(
                    rf"Employees at year\s*-?\s*end\d*\s+({num})",
                    text,
                    re.I,
                )
                if label == "Employees at year-end" and m3:
                    value = re.sub(r"\s*,\s*", ",", m3.group(1))
                    value = re.sub(r"\s+", "", value)
                    return (
                        f"According to {c['document']} (page {c['page']}), "
                        f"Employees at year-end for {year or 'the reported year'} "
                        f"was {value}."
                    )
                continue

            nums = re.findall(num, m.group(1))
            if not nums:
                continue
            value = re.sub(r"\s*,\s*", ",", nums[-1])
            value = re.sub(r"\s+", "", value)
            unit = (
                " EUR million"
                if label in {"Group revenues", "Profit/loss before tax"}
                else ""
            )
            return (
                f"According to {c['document']} (page {c['page']}), "
                f"{label} for {year or 'the reported year'} was {value}{unit}."
            )
    return None


def _extractive_answer(question: str, chunks: List[Dict]) -> str:
    kpi = _format_kpi_answer(question, chunks)
    if kpi:
        return kpi

    scored: List[Tuple[float, Dict, str]] = []
    for c in chunks:
        for sent in _split_sentences(c["text"]):
            if len(sent) < 40:
                continue
            score = _score_snippet(question, sent) + 0.15 * float(c.get("score", 0))
            scored.append((score, c, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] < 0.35:
        top = chunks[0]
        preview = top["text"][:500].replace("\n", " ").strip()
        return (
            "I could not confidently extract a direct answer from the retrieved "
            "passages.\n\n"
            f"Closest passage ({top['document']}, p.{top['page']}):\n{preview}…"
        )

    used_pages = set()
    selected: List[Tuple[Dict, str]] = []
    for score, c, sent in scored:
        key = (c["document"], c["page"])
        if key in used_pages:
            continue
        selected.append((c, sent))
        used_pages.add(key)
        if len(selected) >= 2:
            break

    primary_c, primary = selected[0]
    lines = [
        primary.strip(),
        "",
        f"Source: {primary_c['document']}, page {primary_c['page']}",
    ]
    if len(selected) > 1:
        extra_c, extra = selected[1]
        lines.extend(
            [
                "",
                "Additional context:",
                extra.strip(),
                f"Source: {extra_c['document']}, page {extra_c['page']}",
            ]
        )
    return "\n".join(lines)


def _user_prompt(question: str, context: str) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context from BMW investor reports:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer based only on the context. "
        "Mention document names and pages when you cite a figure. "
        "Do not edit files, do not run shell commands, and do not search the repo — "
        "reply with the answer text only."
    )


def _cursor_headers(api_key: str) -> Dict[str, str]:
    import base64

    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _http_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[Dict] = None,
    timeout: int = 120,
) -> Dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def _answer_with_cursor_cloud(question: str, context: str, api_key: str) -> Optional[str]:
    """
    Cloud Agents HTTPS API (no local bridge).

    Local cursor-sdk on Windows fails with WinError 10038 while starting the
    bridge (select() on a non-socket). Cloud no-repo agents avoid that.
    """
    import time

    headers = _cursor_headers(api_key)
    model = (os.getenv("CURSOR_MODEL") or "composer-2.5").strip()
    prompt = _user_prompt(question, context)
    create_body: Dict = {
        "prompt": {"text": prompt},
        "name": "AutoChat BMW Q&A",
    }
    # "default" = Auto; otherwise pass explicit model id from /v1/models
    if model and model.lower() not in {"auto", "default"}:
        create_body["model"] = {"id": model}

    print("(Asking Cursor cloud agent…)", flush=True)
    try:
        created = _http_json(
            "POST",
            "https://api.cursor.com/v1/agents",
            headers,
            create_body,
            timeout=180,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode("utf-8", errors="replace")
        print(f"(Cursor cloud create failed: HTTP {exc.code} {detail})", flush=True)
        return None
    except Exception as exc:
        print(f"(Cursor cloud create failed: {exc})", flush=True)
        return None

    agent = created.get("agent") or {}
    run = created.get("run") or {}
    agent_id = agent.get("id")
    run_id = run.get("id") or agent.get("latestRunId")
    if not agent_id or not run_id:
        print("(Cursor cloud create returned no agent/run id)", flush=True)
        return None

    status = run.get("status")
    result_text = run.get("result")
    terminal = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}
    try:
        # Create may return FINISHED without inline result — always fetch run once.
        for i in range(60):
            if status in terminal and result_text:
                break
            if i > 0 or status not in terminal or not result_text:
                if i > 0:
                    time.sleep(2)
                data = _http_json(
                    "GET",
                    f"https://api.cursor.com/v1/agents/{agent_id}/runs/{run_id}",
                    headers,
                    timeout=60,
                )
                status = data.get("status") or status
                if data.get("result"):
                    result_text = data.get("result")
            if status in terminal and result_text:
                break
            if status in terminal and i >= 2:
                # Terminal with empty result after a couple refreshes.
                break
    finally:
        try:
            _http_json(
                "POST",
                f"https://api.cursor.com/v1/agents/{agent_id}/archive",
                headers,
                {},
                timeout=30,
            )
        except Exception:
            pass

    if status != "FINISHED" or not result_text:
        print(f"(Cursor cloud status={status!r}; falling back)", flush=True)
        return None
    return str(result_text).strip() or None


def _answer_with_cursor_local(question: str, context: str, api_key: str) -> Optional[str]:
    """Local SDK path (often broken on Windows bridge startup)."""
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    except ImportError:
        print(
            "(Cursor SDK not installed for this Python. "
            "Run: py -3.12 -m pip install cursor-sdk)",
            flush=True,
        )
        return None

    model = os.getenv("CURSOR_MODEL", "composer-2.5")
    with tempfile.TemporaryDirectory(prefix="autochat-cursor-") as tmp:
        ctx_path = Path(tmp) / "CONTEXT.md"
        ctx_path.write_text(
            "# Retrieved BMW report passages\n\n" + context,
            encoding="utf-8",
        )
        prompt = (
            "Read CONTEXT.md in this folder if helpful. "
            "Answer the question using ONLY the BMW report passages below.\n\n"
            + _user_prompt(question, context)
        )
        try:
            result = Agent.prompt(
                prompt,
                AgentOptions(
                    api_key=api_key,
                    model=model,
                    local=LocalAgentOptions(cwd=tmp),
                ),
            )
        except Exception as exc:
            print(f"(Cursor local answer failed: {exc})", flush=True)
            return None

    status = getattr(result, "status", None)
    text = getattr(result, "result", None)
    if status == "error" or not text:
        print(f"(Cursor local run status={status!r}; falling back)", flush=True)
        return None
    return str(text).strip() or None


def _answer_with_cursor(question: str, context: str) -> Optional[str]:
    """Call Cursor. Default = cloud API (Windows-safe); optional local SDK."""
    api_key = (os.getenv("CURSOR_API_KEY") or "").strip()
    if not api_key or api_key.startswith("cursor_your-key"):
        return None

    runtime = (os.getenv("CURSOR_RUNTIME") or "cloud").strip().lower()
    if runtime == "local":
        return _answer_with_cursor_local(question, context, api_key)
    return _answer_with_cursor_cloud(question, context, api_key)


def _answer_with_ollama(question: str, context: str) -> Optional[str]:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer based only on the context. "
                    "Mention document names/pages when you use a figure."
                ),
            },
        ],
    }
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("message") or {}).get("content")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def _answer_with_openai(question: str, context: str) -> Optional[str]:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key.startswith("sk-your-key"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer based only on the context. "
                    "Mention document names/pages when you use a figure."
                ),
            },
        ],
    )
    return resp.choices[0].message.content


def answer_question(
    question: str,
    top_k: int = 5,
    tenant_id: str = "bmw",
) -> Tuple[str, List[Dict]]:
    chunks = retrieve(question, top_k=top_k, tenant_id=tenant_id)
    if not chunks:
        return "I couldn't find relevant passages in the BMW documents.", []

    context = build_context(chunks)

    # Cursor → OpenAI (later) → Ollama → extractive fallback
    for provider in (_answer_with_cursor, _answer_with_openai, _answer_with_ollama):
        answer = provider(question, context)
        if answer:
            return answer, chunks

    return _extractive_answer(question, chunks), chunks
