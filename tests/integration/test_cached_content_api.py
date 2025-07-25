"""
Integration Tests for Google Cached Content API Endpoints

Tests the cached content metrics endpoint and integration with AI services.
"""

import pytest


@pytest.mark.integration
@pytest.mark.ai
class TestCachedContentAPI:
    """Test cached content API endpoints."""

    def test_cache_metrics_endpoint_success(self, client, authenticated_headers):
        """Test cache metrics endpoint returns valid metrics."""
        response = client.get("/api/ai/assessments/cache/metrics", headers=authenticated_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "cache_metrics" in data
        assert "request_id" in data
        assert "generated_at" in data

        cache_metrics = data["cache_metrics"]
        assert "cache_status" in cache_metrics

        # Verify cache status structure
        cache_status = cache_metrics["cache_status"]
        assert "google_cached_content_enabled" in cache_status
        assert "legacy_cache_enabled" in cache_status
        assert "timestamp" in cache_status

    def test_cache_metrics_endpoint_authentication_required(self, unauthenticated_test_client):
        """Test cache metrics endpoint requires authentication."""
        response = unauthenticated_test_client.get("/api/ai/assessments/cache/metrics")
        assert response.status_code == 401

    def test_cache_metrics_includes_performance_data(self, client, authenticated_headers):
        """Test cache metrics includes performance data when available."""
        response = client.get("/api/ai/assessments/cache/metrics", headers=authenticated_headers)

        assert response.status_code == 200
        data = response.json()
        cache_metrics = data["cache_metrics"]

        # Should have either Google cached content or legacy cache metrics
        has_google_cache = "google_cached_content" in cache_metrics
        has_legacy_cache = "legacy_cache" in cache_metrics

        assert has_google_cache or has_legacy_cache

        # If Google cached content is available, check structure
        if has_google_cache and "error" not in cache_metrics["google_cached_content"]:
            google_metrics = cache_metrics["google_cached_content"]
            assert "hit_rate_percentage" in google_metrics
            assert "cache_hits" in google_metrics
            assert "cache_misses" in google_metrics
            assert "total_requests" in google_metrics
            assert "cache_types" in google_metrics

    @pytest.mark.slow
    def test_cache_metrics_with_ai_activity(
        self, client, authenticated_headers, sample_business_profile_data
    ):
        """Test cache metrics after some AI activity."""
        # First, create a business profile to trigger AI caching
        profile_response = client.post(
            "/api/business-profiles",
            json=sample_business_profile_data,
            headers=authenticated_headers,
        )
        assert profile_response.status_code == 201
        business_profile_id = profile_response.json()["id"]

        # Trigger AI analysis to potentially create cached content
        analysis_data = {
            "framework": "ISO27001",
            "assessment_results": {
                "responses": [
                    {"question_id": "q1", "response": "yes"},
                    {"question_id": "q2", "response": "no"},
                ]
            },
            "business_profile_id": business_profile_id,
        }

        # Make AI analysis request (may create cached content)
        analysis_response = client.post(
            "/api/ai/assessments/analysis", json=analysis_data, headers=authenticated_headers
        )
        # Don't assert success as AI service might be mocked

        # Now check cache metrics
        metrics_response = client.get(
            "/api/ai/assessments/cache/metrics", headers=authenticated_headers
        )

        assert metrics_response.status_code == 200
        data = metrics_response.json()

        # Should have cache metrics regardless of AI success
        assert "cache_metrics" in data
        assert "cache_status" in data["cache_metrics"]
