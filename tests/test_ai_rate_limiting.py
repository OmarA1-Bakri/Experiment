"""
Test AI Rate Limiting Implementation
Tests for Phase 2.1: Backend AI Endpoints - Rate Limiting
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from api.middleware.ai_rate_limiter import (
    AIRateLimiter,
    ai_analysis_limiter,
    ai_followup_limiter,
    ai_help_limiter,
    ai_recommendations_limiter,
    get_ai_rate_limit_stats,
)


class TestAIRateLimiter:
    """Test the AIRateLimiter class functionality."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a test rate limiter with low limits for testing."""
        return AIRateLimiter(requests_per_minute=3, burst_allowance=1)

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self, rate_limiter):
        """Test that requests within the limit are allowed."""
        user_id = "test_user_1"

        # First 3 requests should be allowed
        for _i in range(3):
            allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
            assert allowed is True
            assert retry_after == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_requests_over_limit(self, rate_limiter):
        """Test that requests over the limit are blocked."""
        user_id = "test_user_2"

        # Use up the normal limit (3 requests)
        for _i in range(3):
            allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
            assert allowed is True

        # Use up burst allowance (1 request)
        allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
        assert allowed is True

        # Next request should be blocked
        allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_rate_limiter_burst_allowance(self, rate_limiter):
        """Test that burst allowance works correctly."""
        user_id = "test_user_3"

        # Use up normal limit
        for _i in range(3):
            allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
            assert allowed is True

        # Burst allowance should allow 1 more request
        allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
        assert allowed is True

        # Now should be blocked
        allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
        assert allowed is False

    @pytest.mark.asyncio
    async def test_rate_limiter_window_reset(self, rate_limiter):
        """Test that rate limit window resets correctly."""
        user_id = "test_user_4"

        # Use up the limit
        for _i in range(4):  # 3 normal + 1 burst
            allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
            assert allowed is True

        # Should be blocked now
        allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
        assert allowed is False

        # Simulate time passing by patching both time.time and the rate limiter's time usage
        current_time = time.time()
        future_time = current_time + 61  # 61 seconds later (past the window)

        with patch("time.time", return_value=future_time):
            with patch("api.middleware.ai_rate_limiter.time.time", return_value=future_time):
                # Should be allowed again
                allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
                assert allowed is True

    @pytest.mark.asyncio
    async def test_rate_limiter_different_users(self, rate_limiter):
        """Test that different users have separate rate limits."""
        user1 = "test_user_5"
        user2 = "test_user_6"

        # User 1 uses up their limit
        for _i in range(4):  # 3 normal + 1 burst
            allowed, retry_after = await rate_limiter.check_rate_limit(user1)
            assert allowed is True

        # User 1 should be blocked
        allowed, retry_after = await rate_limiter.check_rate_limit(user1)
        assert allowed is False

        # User 2 should still be allowed
        allowed, retry_after = await rate_limiter.check_rate_limit(user2)
        assert allowed is True

    def test_get_remaining_requests(self, rate_limiter):
        """Test getting remaining requests for a user."""
        user_id = "test_user_7"

        # Initially should have full limit
        remaining = rate_limiter.get_remaining_requests(user_id)
        assert remaining == 3

        # After one request, should have 2 remaining
        # Simulate a request by adding to the deque
        rate_limiter.user_requests[user_id].append(time.time())
        remaining = rate_limiter.get_remaining_requests(user_id)
        assert remaining == 2


class TestAIRateLimiterInstances:
    """Test the pre-configured rate limiter instances."""

    def test_ai_help_limiter_configuration(self):
        """Test AI help limiter has correct configuration."""
        assert ai_help_limiter.requests_per_minute == 10
        assert ai_help_limiter.burst_allowance == 2

    def test_ai_followup_limiter_configuration(self):
        """Test AI follow-up limiter has correct configuration."""
        assert ai_followup_limiter.requests_per_minute == 5
        assert ai_followup_limiter.burst_allowance == 1

    def test_ai_analysis_limiter_configuration(self):
        """Test AI analysis limiter has correct configuration."""
        assert ai_analysis_limiter.requests_per_minute == 3
        assert ai_analysis_limiter.burst_allowance == 1

    def test_ai_recommendations_limiter_configuration(self):
        """Test AI recommendations limiter has correct configuration."""
        assert ai_recommendations_limiter.requests_per_minute == 3
        assert ai_recommendations_limiter.burst_allowance == 1


class TestAIRateLimitStats:
    """Test the rate limiting statistics functionality."""

    def test_get_ai_rate_limit_stats_structure(self):
        """Test that rate limit stats return correct structure."""
        stats = get_ai_rate_limit_stats()

        assert isinstance(stats, dict)
        assert "uptime_seconds" in stats
        assert "total_requests" in stats
        assert "rate_limited_requests" in stats
        assert "rate_limit_percentage" in stats
        assert "requests_by_operation" in stats
        assert "rate_limits_by_operation" in stats
        assert "requests_per_minute" in stats

    def test_rate_limit_stats_initial_values(self):
        """Test initial values of rate limit stats."""
        stats = get_ai_rate_limit_stats()

        # Should start with zero requests
        assert stats["total_requests"] >= 0
        assert stats["rate_limited_requests"] >= 0
        assert stats["uptime_seconds"] >= 0


class TestRateLimitingIntegration:
    """Integration tests for rate limiting with mock endpoints."""

    @pytest.mark.asyncio
    async def test_rate_limiting_with_mock_endpoint(self):
        """Test rate limiting behavior with a mock endpoint."""
        from unittest.mock import MagicMock, patch

        from fastapi import HTTPException

        from api.middleware.ai_rate_limiter import create_ai_rate_limit_dependency
        from database.user import User

        # Mock settings to disable testing mode
        with patch("api.middleware.ai_rate_limiter.settings") as mock_settings:
            mock_settings.is_testing = False

            # Create a test rate limiter with very low limits
            test_limiter = AIRateLimiter(requests_per_minute=1, burst_allowance=0)
            rate_limit_check = create_ai_rate_limit_dependency(test_limiter, "test")

            # Mock user and request
            mock_user = MagicMock(spec=User)
            mock_user.id = "test_user_integration"

            mock_request = MagicMock()
            mock_request.state = MagicMock()

            # First request should pass
            try:
                await rate_limit_check(mock_request, mock_user)
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"First request should have been allowed: {e}")

            # Second request should be rate limited
            try:
                await rate_limit_check(mock_request, mock_user)
                pytest.fail("Second request should have been rate limited but wasn't")
            except HTTPException as exc_info:
                # Should be an HTTP 429 exception
                assert exc_info.status_code == 429
            except Exception as e:
                pytest.fail(f"Unexpected exception type: {type(e).__name__}: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting under concurrent requests."""
        rate_limiter = AIRateLimiter(requests_per_minute=5, burst_allowance=1)
        user_id = "concurrent_test_user"

        async def make_request():
            return await rate_limiter.check_rate_limit(user_id)

        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Count allowed and blocked requests
        allowed_count = sum(1 for allowed, _ in results if allowed)
        blocked_count = sum(1 for allowed, _ in results if not allowed)

        # Should allow 6 requests (5 normal + 1 burst) and block 4
        assert allowed_count == 6
        assert blocked_count == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
