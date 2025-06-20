"""
API Performance Tests using pytest-benchmark

Benchmarks critical API endpoints for response time and throughput
performance under various load conditions.
"""

import pytest
import time
import asyncio
import concurrent.futures
from uuid import uuid4
from typing import List, Dict, Any

import requests
from pytest_benchmark.fixture import BenchmarkFixture


@pytest.mark.performance
@pytest.mark.benchmark
class TestAPIPerformance:
    """Benchmark API endpoint performance"""
    
    def test_authentication_performance(self, benchmark: BenchmarkFixture, client):
        """Benchmark authentication endpoint performance"""
        user_data = {
            "email": f"perf-test-{uuid4()}@example.com",
            "password": "PerfTest123!",
            "full_name": "Performance Test User"
        }
        
        # Register user first
        client.post("/api/auth/register", json=user_data)
        
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        def login_request():
            response = client.post("/api/auth/login", json=login_data)
            assert response.status_code == 200
            return response.json()
        
        # Benchmark login performance
        result = benchmark(login_request)
        assert "access_token" in result
        
        # Performance thresholds
        assert benchmark.stats.mean < 0.5  # Mean response time < 500ms
        assert benchmark.stats.max < 2.0   # Max response time < 2s
    
    def test_evidence_creation_performance(self, benchmark: BenchmarkFixture, 
                                         client, authenticated_headers):
        """Benchmark evidence creation performance"""
        def create_evidence():
            evidence_data = {
                "title": f"Performance Test Evidence {uuid4()}",
                "description": "Evidence created during performance testing",
                "evidence_type": "document",
                "source": "manual",
                "framework_mappings": ["ISO27001.A.5.1.1"],
                "tags": ["performance", "test"],
                "metadata": {
                    "test_type": "performance",
                    "created_at": time.time()
                }
            }
            
            response = client.post("/api/evidence", 
                                 json=evidence_data, 
                                 headers=authenticated_headers)
            assert response.status_code == 201
            return response.json()
        
        result = benchmark(create_evidence)
        assert "id" in result
        assert result["title"].startswith("Performance Test Evidence")
        
        # Performance assertions
        assert benchmark.stats.mean < 1.0  # Mean < 1s
        assert benchmark.stats.max < 3.0   # Max < 3s
    
    def test_evidence_search_performance(self, benchmark: BenchmarkFixture,
                                       client, authenticated_headers, evidence_item_instance):
        """Benchmark evidence search performance"""
        def search_evidence():
            search_params = {
                "q": "security",
                "evidence_type": "document",
                "page": 1,
                "page_size": 20
            }
            
            response = client.get("/api/evidence/search", 
                                params=search_params,
                                headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(search_evidence)
        assert "results" in result
        assert "total_count" in result
        
        # Search should be fast
        assert benchmark.stats.mean < 0.8  # Mean < 800ms
        assert benchmark.stats.max < 2.5   # Max < 2.5s
    
    def test_dashboard_performance(self, benchmark: BenchmarkFixture,
                                 client, authenticated_headers):
        """Benchmark dashboard load performance"""
        def load_dashboard():
            response = client.get("/api/users/dashboard", headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(load_dashboard)
        assert "business_profile" in result or "onboarding_completed" in result
        
        # Dashboard should load quickly
        assert benchmark.stats.mean < 1.5  # Mean < 1.5s
        assert benchmark.stats.max < 4.0   # Max < 4s
    
    def test_ai_chat_performance(self, benchmark: BenchmarkFixture,
                               client, authenticated_headers, mock_ai_client):
        """Benchmark AI chat response performance"""
        def send_chat_message():
            chat_data = {
                "message": "What are the key requirements for GDPR compliance?",
                "conversation_id": None,
                "context": {
                    "framework": "GDPR",
                    "urgency": "medium"
                }
            }
            
            response = client.post("/api/chat/send", 
                                 json=chat_data,
                                 headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(send_chat_message)
        assert "response" in result or "message" in result
        
        # AI responses should be reasonably fast
        assert benchmark.stats.mean < 3.0  # Mean < 3s
        assert benchmark.stats.max < 8.0   # Max < 8s
    
    def test_concurrent_request_performance(self, client, authenticated_headers):
        """Test performance under concurrent load"""
        
        def make_concurrent_requests(endpoint: str, num_requests: int = 10) -> List[float]:
            """Make concurrent requests and return response times"""
            response_times = []
            
            def single_request():
                start_time = time.time()
                response = client.get(endpoint, headers=authenticated_headers)
                end_time = time.time()
                
                assert response.status_code == 200
                return end_time - start_time
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [executor.submit(single_request) for _ in range(num_requests)]
                response_times = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            return response_times
        
        # Test concurrent requests to user profile endpoint
        response_times = make_concurrent_requests("/api/users/profile", 20)
        
        # Performance assertions
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0  # Average < 1s under concurrent load
        assert max_response_time < 3.0  # No request > 3s
        assert len([t for t in response_times if t > 2.0]) < 2  # < 10% of requests > 2s
    
    def test_bulk_operation_performance(self, benchmark: BenchmarkFixture,
                                      client, authenticated_headers, db_session, sample_user):
        """Benchmark bulk operations performance"""
        
        # Create multiple evidence items first
        evidence_ids = []
        for i in range(10):
            evidence_data = {
                "title": f"Bulk Test Evidence {i+1}",
                "description": f"Evidence for bulk testing {i+1}",
                "evidence_type": "document"
            }
            
            response = client.post("/api/evidence", 
                                 json=evidence_data,
                                 headers=authenticated_headers)
            assert response.status_code == 201
            evidence_ids.append(response.json()["id"])
        
        def bulk_update():
            bulk_data = {
                "evidence_ids": evidence_ids,
                "status": "reviewed",
                "reason": "Bulk performance test"
            }
            
            response = client.post("/api/evidence/bulk-update",
                                 json=bulk_data,
                                 headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(bulk_update)
        assert result["updated_count"] == 10
        assert result["failed_count"] == 0
        
        # Bulk operations should scale well
        assert benchmark.stats.mean < 2.0  # Mean < 2s for 10 items
        assert benchmark.stats.max < 5.0   # Max < 5s


@pytest.mark.performance 
@pytest.mark.memory
class TestMemoryPerformance:
    """Test memory usage and performance"""
    
    def test_large_dataset_handling(self, client, authenticated_headers):
        """Test performance with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large number of evidence items
        evidence_ids = []
        for i in range(100):
            evidence_data = {
                "title": f"Large Dataset Evidence {i+1:03d}",
                "description": "x" * 1000,  # 1KB description
                "evidence_type": "document",
                "metadata": {
                    "large_field": "x" * 5000,  # 5KB metadata
                    "test_index": i
                }
            }
            
            response = client.post("/api/evidence",
                                 json=evidence_data,
                                 headers=authenticated_headers)
            assert response.status_code == 201
            evidence_ids.append(response.json()["id"])
        
        # Test retrieving large dataset
        start_time = time.time()
        response = client.get("/api/evidence?page_size=100", headers=authenticated_headers)
        retrieval_time = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 100
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Performance assertions
        assert retrieval_time < 5.0  # Should retrieve 100 items in < 5s
        assert memory_increase < 100  # Memory increase should be < 100MB
    
    def test_concurrent_memory_usage(self, client, authenticated_headers):
        """Test memory usage under concurrent load"""
        import psutil
        import os
        import threading
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def worker_thread(thread_id: int):
            """Worker thread that creates and retrieves evidence"""
            for i in range(10):
                # Create evidence
                evidence_data = {
                    "title": f"Thread {thread_id} Evidence {i+1}",
                    "description": f"Evidence from thread {thread_id}",
                    "evidence_type": "document"
                }
                
                response = client.post("/api/evidence",
                                     json=evidence_data,
                                     headers=authenticated_headers)
                assert response.status_code == 201
                
                # Retrieve user evidence
                response = client.get("/api/evidence", headers=authenticated_headers)
                assert response.status_code == 200
        
        # Run multiple threads concurrently
        threads = []
        for thread_id in range(10):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase excessively
        assert memory_increase < 200  # < 200MB increase for concurrent operations


@pytest.mark.performance
@pytest.mark.database
class TestDatabasePerformance:
    """Test database operation performance"""
    
    def test_complex_query_performance(self, benchmark: BenchmarkFixture,
                                     client, authenticated_headers, db_session):
        """Benchmark complex database queries"""
        
        # Create test data for complex queries
        frameworks = ["GDPR", "ISO27001", "SOC2"]
        statuses = ["valid", "expired", "under_review"]
        
        for i in range(50):
            evidence_data = {
                "title": f"Query Test Evidence {i+1:02d}",
                "description": f"Evidence for complex query testing {i+1}",
                "evidence_type": "document",
                "framework_mappings": [f"{frameworks[i % 3]}.{i//10 + 1}.{i%10 + 1}"],
                "status": statuses[i % 3],
                "tags": [f"tag{i%5}", f"category{i%3}"]
            }
            
            response = client.post("/api/evidence",
                                 json=evidence_data,
                                 headers=authenticated_headers)
            assert response.status_code == 201
        
        def complex_search():
            search_params = {
                "q": "evidence testing",
                "evidence_type": ["document"],
                "framework": ["GDPR", "ISO27001"],
                "status": ["valid", "under_review"],
                "tags": ["tag1", "tag2"],
                "sort_by": "created_at",
                "sort_order": "desc",
                "page": 1,
                "page_size": 20
            }
            
            response = client.get("/api/evidence/search",
                                params=search_params,
                                headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(complex_search)
        assert "results" in result
        
        # Complex queries should still be reasonably fast
        assert benchmark.stats.mean < 2.0  # Mean < 2s
        assert benchmark.stats.max < 5.0   # Max < 5s
    
    def test_aggregation_performance(self, benchmark: BenchmarkFixture,
                                   client, authenticated_headers):
        """Benchmark database aggregation queries"""
        
        def get_statistics():
            response = client.get("/api/evidence/stats", headers=authenticated_headers)
            assert response.status_code == 200
            return response.json()
        
        result = benchmark(get_statistics)
        assert "total_evidence_items" in result
        assert "by_status" in result
        assert "by_type" in result
        
        # Aggregation queries should be fast
        assert benchmark.stats.mean < 1.0  # Mean < 1s
        assert benchmark.stats.max < 3.0   # Max < 3s


@pytest.mark.performance
@pytest.mark.integration
class TestEndToEndPerformance:
    """Test end-to-end workflow performance"""
    
    def test_complete_onboarding_performance(self, benchmark: BenchmarkFixture, client):
        """Benchmark complete user onboarding workflow"""
        
        def complete_onboarding():
            # User registration
            user_data = {
                "email": f"e2e-perf-{uuid4()}@example.com",
                "password": "E2EPerf123!",
                "full_name": "E2E Performance Test User"
            }
            
            register_response = client.post("/api/auth/register", json=user_data)
            assert register_response.status_code == 201
            
            # Login
            login_response = client.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create business profile
            profile_data = {
                "company_name": "E2E Performance Test Corp",
                "industry": "Technology",
                "employee_count": 50,
                "revenue_range": "1M-10M",
                "location": "UK"
            }
            
            profile_response = client.post("/api/business-profiles",
                                         json=profile_data,
                                         headers=headers)
            assert profile_response.status_code == 201
            business_profile_id = profile_response.json()["id"]
            
            # Start assessment
            assessment_data = {
                "business_profile_id": business_profile_id,
                "assessment_type": "compliance_scoping"
            }
            
            assessment_response = client.post("/api/assessments",
                                            json=assessment_data,
                                            headers=headers)
            assert assessment_response.status_code == 201
            assessment_id = assessment_response.json()["session_id"]
            
            # Complete assessment
            questions = [
                {"question_id": "data_processing", "response": "yes"},
                {"question_id": "data_types", "response": ["personal_data"]},
                {"question_id": "compliance_experience", "response": "basic"}
            ]
            
            for question in questions:
                client.post(f"/api/assessments/{assessment_id}/responses",
                          json={**question, "move_to_next_stage": True},
                          headers=headers)
            
            complete_response = client.post(f"/api/assessments/{assessment_id}/complete",
                                          headers=headers)
            assert complete_response.status_code == 200
            
            # Get recommendations
            recommendations_response = client.get(
                f"/api/frameworks/recommendations/{business_profile_id}",
                headers=headers
            )
            assert recommendations_response.status_code == 200
            
            # Get dashboard
            dashboard_response = client.get("/api/users/dashboard", headers=headers)
            assert dashboard_response.status_code == 200
            
            return dashboard_response.json()
        
        result = benchmark(complete_onboarding)
        assert "business_profile" in result or "onboarding_completed" in result
        
        # Complete onboarding should finish in reasonable time
        assert benchmark.stats.mean < 10.0  # Mean < 10s for complete flow
        assert benchmark.stats.max < 20.0   # Max < 20s


# Performance test utilities
class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start_monitoring(self):
        """Start performance monitoring"""
        import psutil
        
        self.start_time = time.time()
        self.metrics["initial_cpu"] = psutil.cpu_percent()
        self.metrics["initial_memory"] = psutil.virtual_memory().percent
        
    def stop_monitoring(self):
        """Stop monitoring and return metrics"""
        import psutil
        
        end_time = time.time()
        self.metrics["duration"] = end_time - self.start_time
        self.metrics["final_cpu"] = psutil.cpu_percent()
        self.metrics["final_memory"] = psutil.virtual_memory().percent
        
        return self.metrics


@pytest.fixture
def performance_monitor():
    """Fixture for performance monitoring"""
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    yield monitor
    metrics = monitor.stop_monitoring()
    
    # Log performance metrics
    print(f"Performance metrics: {metrics}")
    
    # Performance assertions
    assert metrics["duration"] < 30.0  # Test should complete in < 30s
    assert metrics["final_cpu"] - metrics["initial_cpu"] < 50  # CPU increase < 50%


@pytest.mark.performance
class TestRealWorldScenarios:
    """Test realistic user scenarios"""
    
    def test_daily_user_workflow(self, performance_monitor, client, authenticated_headers):
        """Test typical daily user workflow performance"""
        
        # Morning dashboard check
        response = client.get("/api/users/dashboard", headers=authenticated_headers)
        assert response.status_code == 200
        
        # Check evidence items
        response = client.get("/api/evidence?page=1&page_size=10", headers=authenticated_headers)
        assert response.status_code == 200
        
        # Add new evidence
        evidence_data = {
            "title": "Daily Workflow Evidence",
            "description": "Evidence added during daily workflow",
            "evidence_type": "document"
        }
        response = client.post("/api/evidence", json=evidence_data, headers=authenticated_headers)
        assert response.status_code == 201
        
        # Search for evidence
        response = client.get("/api/evidence/search?q=workflow", headers=authenticated_headers)
        assert response.status_code == 200
        
        # Check compliance status
        response = client.get("/api/compliance/status", headers=authenticated_headers)
        assert response.status_code == 200
        
        metrics = performance_monitor.stop_monitoring()
        assert metrics["duration"] < 5.0  # Daily workflow should be fast
    
    def test_peak_usage_simulation(self, client):
        """Simulate peak usage with multiple users"""
        import threading
        import time
        
        def user_session(user_id: int):
            """Simulate individual user session"""
            user_data = {
                "email": f"peak-user-{user_id}@example.com",
                "password": "PeakTest123!",
                "full_name": f"Peak Test User {user_id}"
            }
            
            # Register and login
            client.post("/api/auth/register", json=user_data)
            login_response = client.post("/api/auth/login", json={
                "email": user_data["email"],
                "password": user_data["password"]
            })
            
            if login_response.status_code == 200:
                headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
                
                # Simulate user activity
                for _ in range(10):
                    # Random activity
                    activities = [
                        lambda: client.get("/api/users/dashboard", headers=headers),
                        lambda: client.get("/api/evidence", headers=headers),
                        lambda: client.post("/api/evidence", json={
                            "title": f"Peak Evidence {user_id}",
                            "evidence_type": "document"
                        }, headers=headers),
                        lambda: client.get("/api/compliance/status", headers=headers)
                    ]
                    
                    activity = activities[user_id % len(activities)]
                    activity()
                    time.sleep(0.1)  # Brief pause between activities
        
        # Simulate 20 concurrent users
        threads = []
        start_time = time.time()
        
        for user_id in range(20):
            thread = threading.Thread(target=user_session, args=(user_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all users to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Peak usage should handle concurrent users efficiently
        assert total_time < 30.0  # All 20 users should complete in < 30s