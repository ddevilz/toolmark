"""
LLM utility layer — wraps LiteLLM for skillforge test and bench.

All model calls go through here so the rest of the codebase stays
provider-agnostic. Supports any LiteLLM model string.
"""

from __future__ import annotations

import json
from typing import Any

from skillforge.models import SkillTestCase


async def llm_call(
    model: str,
    system: str,
    user: str,
) -> tuple[str, dict[str, int]]:
    """
    Make a single LLM call via LiteLLM.
    Returns (response_text, usage_dict).
    """
    try:
        import litellm
    except ImportError as err:
        raise RuntimeError("litellm is required: pip install litellm") from err

    response = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=512,
    )

    text = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
    }
    return text, usage


_JUDGE_SYSTEM = """You are a strict test judge for AI agent skill evaluation.

You are given:
- A test case with an expected tool invocation and parameters
- The actual invocation produced by the skill router

Respond ONLY with valid JSON:
{
  "passed": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "one sentence explanation"
}

Scoring rules:
- STRICT tolerance: exact tool name match + exact parameter key/value match required
- FUZZY tolerance: semantic equivalence counts (e.g. "state: open" == "status: open")
- INVOKED tolerance: only check whether skill was invoked (true/false)
- Penalise hallucinated parameters that weren't expected
- If expect_invoked=false but skill was invoked: always fail
"""


async def llm_judge(
    model: str,
    test_case: SkillTestCase,
    actual_invoked: bool,
    actual_tool: str | None,
    actual_params: dict[str, Any],
) -> tuple[bool, float, str]:
    """
    Call an LLM to judge whether the skill invocation was correct.
    Returns (passed, confidence, reasoning).
    """
    prompt = (
        f"Test case:\n"
        f"  input: {test_case.input!r}\n"
        f"  expect_invoked: {test_case.expect_invoked}\n"
        f"  expect_tool: {test_case.expect_tool!r}\n"
        f"  expect_params: {json.dumps(test_case.expect_params)}\n"
        f"  tolerance: {test_case.tolerance.value}\n\n"
        f"Actual result:\n"
        f"  invoked: {actual_invoked}\n"
        f"  tool: {actual_tool!r}\n"
        f"  params: {json.dumps(actual_params)}\n\n"
        f"Judge this result:"
    )

    text, _ = await llm_call(model=model, system=_JUDGE_SYSTEM, user=prompt)

    try:
        data = json.loads(text)
        return bool(data["passed"]), float(data["confidence"]), str(data.get("reasoning", ""))
    except (json.JSONDecodeError, KeyError):
        # Fallback: basic heuristic
        passed = actual_invoked == test_case.expect_invoked and (
            actual_tool == test_case.expect_tool if test_case.expect_tool else True
        )
        return passed, 0.5, "Judge response unparseable — fallback heuristic used."
