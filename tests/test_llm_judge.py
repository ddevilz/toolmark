"""
Tests for skillforge.utils.llm — LLM-as-judge evaluation.
Uses mocks — no real API calls made.
"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from skillforge.models import SkillTestCase, ToleranceLevel
from skillforge.utils.llm import llm_judge


def _make_test_case(**kwargs) -> SkillTestCase:
    defaults = {
        "input": "search my open PRs",
        "expect_invoked": True,
        "expect_tool": "search_pull_requests",
        "expect_params": {"state": "open", "assignee": "@me"},
        "tolerance": ToleranceLevel.FUZZY,
    }
    defaults.update(kwargs)
    return SkillTestCase(**defaults)


class TestLLMJudge:
    @pytest.mark.asyncio
    async def test_judge_returns_pass_on_correct_invocation(self):
        judge_response = json.dumps(
            {"passed": True, "confidence": 0.95, "reasoning": "Exact match."}
        )

        with patch("skillforge.utils.llm.llm_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (
                judge_response,
                {"prompt_tokens": 100, "completion_tokens": 20},
            )
            passed, conf, reasoning = await llm_judge(
                model="test-model",
                test_case=_make_test_case(),
                actual_invoked=True,
                actual_tool="search_pull_requests",
                actual_params={"state": "open", "assignee": "@me"},
            )

        assert passed is True
        assert conf == pytest.approx(0.95)
        assert "match" in reasoning.lower()

    @pytest.mark.asyncio
    async def test_judge_returns_fail_on_wrong_tool(self):
        judge_response = json.dumps(
            {"passed": False, "confidence": 0.9, "reasoning": "Wrong tool invoked."}
        )

        with patch("skillforge.utils.llm.llm_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (judge_response, {})
            passed, conf, reasoning = await llm_judge(
                model="test-model",
                test_case=_make_test_case(),
                actual_invoked=True,
                actual_tool="get_issue",  # wrong tool
                actual_params={},
            )

        assert passed is False
        assert conf == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_judge_fallback_on_unparseable_response(self):
        """If judge returns non-JSON, fallback heuristic should be used."""
        with patch("skillforge.utils.llm.llm_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ("not json at all", {})
            passed, conf, reasoning = await llm_judge(
                model="test-model",
                test_case=_make_test_case(),
                actual_invoked=True,
                actual_tool="search_pull_requests",
                actual_params={},
            )

        # Heuristic: invoked matches + tool matches → pass
        assert passed is True
        assert conf == pytest.approx(0.5)
        assert "fallback" in reasoning.lower()

    @pytest.mark.asyncio
    async def test_judge_negative_case_not_invoked(self):
        judge_response = json.dumps(
            {"passed": True, "confidence": 0.99, "reasoning": "Correctly not invoked."}
        )

        with patch("skillforge.utils.llm.llm_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (judge_response, {})
            passed, conf, _ = await llm_judge(
                model="test-model",
                test_case=_make_test_case(expect_invoked=False, expect_tool=None, expect_params={}),
                actual_invoked=False,
                actual_tool=None,
                actual_params={},
            )

        assert passed is True
        assert conf > 0.9


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), 
    reason="Requires ANTHROPIC_API_KEY for real LLM call"
)
@pytest.mark.asyncio
async def test_integration_real_llm_judge():
    """Integration test with real LLM API call."""
    passed, conf, reasoning = await llm_judge(
        model="gpt-4o-mini",
        test_case=_make_test_case(),
        actual_invoked=True,
        actual_tool="search_pull_requests",
        actual_params={"state": "open", "assignee": "@me"},
    )
    
    # Should pass with high confidence for exact match
    assert passed is True
    assert conf > 0.7
    assert len(reasoning) > 10
