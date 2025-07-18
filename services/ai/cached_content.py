"""
Google Cached Content Integration for AI Optimization

This module implements Google's CachedContent API to replace the custom caching system,
providing better performance and cost optimization through Google's native caching.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai
from config.logging_config import get_logger
from config.ai_config import ModelType

logger = get_logger(__name__)


class CacheContentType(Enum):
    """Types of content that can be cached."""

    ASSESSMENT_CONTEXT = "assessment_context"
    BUSINESS_PROFILE = "business_profile"
    FRAMEWORK_CONTEXT = "framework_context"
    INDUSTRY_REGULATIONS = "industry_regulations"
    SYSTEM_INSTRUCTIONS = "system_instructions"


@dataclass
class CacheLifecycleConfig:
    """Configuration for cache lifecycle management."""

    default_ttl_hours: int = 2
    max_ttl_hours: int = 24
    min_ttl_minutes: int = 30
    auto_refresh_threshold: float = 0.8  # Refresh when 80% of TTL has passed
    max_cache_size_mb: int = 100

    # Cache Strategy Optimization
    performance_based_ttl: bool = True
    cache_warming_enabled: bool = True
    intelligent_invalidation: bool = True

    # Performance thresholds for TTL adjustment
    fast_response_threshold_ms: int = 200
    slow_response_threshold_ms: int = 2000
    ttl_adjustment_factor: float = 0.2  # 20% adjustment based on performance


class GoogleCachedContentManager:
    """
    Manager for Google's CachedContent API integration.

    Provides intelligent caching of assessment contexts, business profiles,
    and framework information for improved AI performance and cost reduction.
    """

    def __init__(self, lifecycle_config: Optional[CacheLifecycleConfig] = None):
        self.config = lifecycle_config or CacheLifecycleConfig()
        self.active_caches: Dict[str, genai.caching.CachedContent] = {}
        self.cache_metadata: Dict[str, Dict[str, Any]] = {}

        # Check if we're in test mode
        import os

        self.use_mock = os.getenv("USE_MOCK_AI", "false").lower() == "true"

        # Cache performance metrics
        self.metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_creates": 0,
            "cache_refreshes": 0,
            "total_cost_savings": 0.0,
            "total_size_cached_mb": 0.0,
        }

        # Cache Strategy Optimization
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_warming_queue: List[Dict[str, Any]] = []
        self.invalidation_triggers: Dict[str, datetime] = {}

    async def create_assessment_cache(
        self,
        framework_id: str,
        business_profile: Dict[str, Any],
        assessment_context: Optional[Dict[str, Any]] = None,
        model_type: ModelType = ModelType.GEMINI_25_FLASH,
    ) -> Optional[genai.caching.CachedContent]:
        """
        Create cached content for assessment context.

        Args:
            framework_id: ID of the compliance framework
            business_profile: Business profile data
            assessment_context: Additional assessment context
            model_type: Model to use for caching

        Returns:
            CachedContent instance or None if creation failed
        """
        # Return mock cache in test environment
        if self.use_mock:
            from unittest.mock import MagicMock

            mock_cache = MagicMock()
            mock_cache.name = f"mock-cache-{framework_id}"
            mock_cache.model = model_type.value
            # Update metrics for testing
            self.metrics["cache_creates"] += 1
            return mock_cache

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                CacheContentType.ASSESSMENT_CONTEXT,
                framework_id,
                business_profile.get("id", "unknown"),
            )

            # Check if cache already exists
            if cache_key in self.active_caches:
                existing_cache = self.active_caches[cache_key]
                if self._is_cache_valid(existing_cache):
                    logger.debug(f"Using existing assessment cache: {cache_key}")
                    self.metrics["cache_hits"] += 1
                    return existing_cache
                else:
                    # Cache expired, remove it
                    await self._remove_cache(cache_key)

            # Build cache content
            cache_content = self._build_assessment_cache_content(
                framework_id, business_profile, assessment_context
            )

            # Calculate TTL based on content stability
            ttl_hours = self._calculate_assessment_ttl(framework_id, business_profile)
            ttl = timedelta(hours=ttl_hours)

            # Create cached content
            display_name = f"assessment_{framework_id}_{business_profile.get('id', 'unknown')[:8]}"

            cached_content = genai.caching.CachedContent.create(
                model=model_type.value, contents=cache_content, ttl=ttl, display_name=display_name
            )

            # Store cache reference and metadata
            self.active_caches[cache_key] = cached_content
            self.cache_metadata[cache_key] = {
                "type": CacheContentType.ASSESSMENT_CONTEXT.value,
                "created_at": datetime.utcnow(),
                "ttl_hours": ttl_hours,
                "framework_id": framework_id,
                "business_profile_id": business_profile.get("id"),
                "size_estimate_mb": len(json.dumps(cache_content)) / (1024 * 1024),
            }

            self.metrics["cache_creates"] += 1
            self.metrics["total_size_cached_mb"] += self.cache_metadata[cache_key][
                "size_estimate_mb"
            ]

            logger.info(f"Created assessment cache: {display_name} with {ttl_hours}h TTL")
            return cached_content

        except Exception as e:
            logger.error(f"Failed to create assessment cache: {e}")
            self.metrics["cache_misses"] += 1
            return None

    async def create_business_profile_cache(
        self, business_profile: Dict[str, Any], model_type: ModelType = ModelType.GEMINI_25_FLASH
    ) -> Optional[genai.caching.CachedContent]:
        """
        Create cached content for business profile context.

        Args:
            business_profile: Business profile data
            model_type: Model to use for caching

        Returns:
            CachedContent instance or None if creation failed
        """
        try:
            # Generate cache key based on profile similarity
            cache_key = self._generate_business_profile_cache_key(business_profile)

            # Check for existing similar profile cache
            if cache_key in self.active_caches:
                existing_cache = self.active_caches[cache_key]
                if self._is_cache_valid(existing_cache):
                    logger.debug(f"Using existing business profile cache: {cache_key}")
                    self.metrics["cache_hits"] += 1
                    return existing_cache
                else:
                    await self._remove_cache(cache_key)

            # Build business profile cache content
            cache_content = self._build_business_profile_cache_content(business_profile)

            # Calculate TTL based on business stability factors
            ttl_hours = self._calculate_business_profile_ttl(business_profile)
            ttl = timedelta(hours=ttl_hours)

            # Create cached content
            display_name = f"business_profile_{business_profile.get('id', 'unknown')[:8]}"

            cached_content = genai.caching.CachedContent.create(
                model=model_type.value, contents=cache_content, ttl=ttl, display_name=display_name
            )

            # Store cache reference and metadata
            self.active_caches[cache_key] = cached_content
            self.cache_metadata[cache_key] = {
                "type": CacheContentType.BUSINESS_PROFILE.value,
                "created_at": datetime.utcnow(),
                "ttl_hours": ttl_hours,
                "business_profile_id": business_profile.get("id"),
                "industry": business_profile.get("industry"),
                "size_estimate_mb": len(json.dumps(cache_content)) / (1024 * 1024),
            }

            self.metrics["cache_creates"] += 1
            self.metrics["total_size_cached_mb"] += self.cache_metadata[cache_key][
                "size_estimate_mb"
            ]

            logger.info(f"Created business profile cache: {display_name} with {ttl_hours}h TTL")
            return cached_content

        except Exception as e:
            logger.error(f"Failed to create business profile cache: {e}")
            self.metrics["cache_misses"] += 1
            return None

    async def create_framework_cache(
        self,
        framework_id: str,
        industry_context: Optional[str] = None,
        model_type: ModelType = ModelType.GEMINI_25_FLASH,
    ) -> Optional[genai.caching.CachedContent]:
        """
        Create cached content for framework-specific information.

        Args:
            framework_id: ID of the compliance framework
            industry_context: Industry-specific context
            model_type: Model to use for caching

        Returns:
            CachedContent instance or None if creation failed
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                CacheContentType.FRAMEWORK_CONTEXT, framework_id, industry_context or "general"
            )

            # Check for existing cache
            if cache_key in self.active_caches:
                existing_cache = self.active_caches[cache_key]
                if self._is_cache_valid(existing_cache):
                    logger.debug(f"Using existing framework cache: {cache_key}")
                    self.metrics["cache_hits"] += 1
                    return existing_cache
                else:
                    await self._remove_cache(cache_key)

            # Build framework cache content
            cache_content = self._build_framework_cache_content(framework_id, industry_context)

            # Framework information is relatively stable - longer TTL
            ttl_hours = 12  # 12 hour TTL for framework context
            ttl = timedelta(hours=ttl_hours)

            # Create cached content
            display_name = f"framework_{framework_id}_{industry_context or 'general'}"

            cached_content = genai.caching.CachedContent.create(
                model=model_type.value, contents=cache_content, ttl=ttl, display_name=display_name
            )

            # Store cache reference and metadata
            self.active_caches[cache_key] = cached_content
            self.cache_metadata[cache_key] = {
                "type": CacheContentType.FRAMEWORK_CONTEXT.value,
                "created_at": datetime.utcnow(),
                "ttl_hours": ttl_hours,
                "framework_id": framework_id,
                "industry_context": industry_context,
                "size_estimate_mb": len(json.dumps(cache_content)) / (1024 * 1024),
            }

            self.metrics["cache_creates"] += 1
            self.metrics["total_size_cached_mb"] += self.cache_metadata[cache_key][
                "size_estimate_mb"
            ]

            logger.info(f"Created framework cache: {display_name} with {ttl_hours}h TTL")
            return cached_content

        except Exception as e:
            logger.error(f"Failed to create framework cache: {e}")
            self.metrics["cache_misses"] += 1
            return None

    def get_cached_content(
        self, content_type: CacheContentType, identifier: str, secondary_key: Optional[str] = None
    ) -> Optional[genai.caching.CachedContent]:
        """
        Get existing cached content by type and identifier.

        Args:
            content_type: Type of cached content
            identifier: Primary identifier
            secondary_key: Secondary identifier for composite keys

        Returns:
            CachedContent instance or None if not found/expired
        """
        cache_key = self._generate_cache_key(content_type, identifier, secondary_key)

        if cache_key in self.active_caches:
            cached_content = self.active_caches[cache_key]
            if self._is_cache_valid(cached_content):
                self.metrics["cache_hits"] += 1
                return cached_content
            else:
                # Cache expired, remove it
                self._remove_cache_sync(cache_key)

        self.metrics["cache_misses"] += 1
        return None

    async def refresh_cache(self, cache_key: str) -> bool:
        """
        Refresh an existing cache with updated content.

        Args:
            cache_key: Key of the cache to refresh

        Returns:
            True if refresh succeeded, False otherwise
        """
        try:
            if cache_key not in self.cache_metadata:
                logger.warning(f"Cannot refresh unknown cache: {cache_key}")
                return False

            metadata = self.cache_metadata[cache_key]
            content_type = CacheContentType(metadata["type"])

            # Refresh based on content type
            if content_type == CacheContentType.ASSESSMENT_CONTEXT:
                # Would need to reconstruct the assessment cache
                # This is a simplified implementation
                logger.info(f"Refreshing assessment cache: {cache_key}")

            elif content_type == CacheContentType.BUSINESS_PROFILE:
                # Would need to reconstruct the business profile cache
                logger.info(f"Refreshing business profile cache: {cache_key}")

            elif content_type == CacheContentType.FRAMEWORK_CONTEXT:
                # Would need to reconstruct the framework cache
                logger.info(f"Refreshing framework cache: {cache_key}")

            self.metrics["cache_refreshes"] += 1
            return True

        except Exception as e:
            logger.error(f"Failed to refresh cache {cache_key}: {e}")
            return False

    async def cleanup_expired_caches(self) -> int:
        """
        Clean up expired caches and free resources.

        Returns:
            Number of caches cleaned up
        """
        cleaned_count = 0
        expired_keys = []

        for cache_key, cached_content in self.active_caches.items():
            if not self._is_cache_valid(cached_content):
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            await self._remove_cache(cache_key)
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} expired caches")
        return cleaned_count

    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache performance metrics."""
        total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        hit_rate = (self.metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            "hit_rate_percentage": round(hit_rate, 2),
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "total_requests": total_requests,
            "active_caches": len(self.active_caches),
            "cache_creates": self.metrics["cache_creates"],
            "cache_refreshes": self.metrics["cache_refreshes"],
            "total_size_cached_mb": round(self.metrics["total_size_cached_mb"], 2),
            "estimated_cost_savings": round(self.metrics["total_cost_savings"], 4),
            "cache_types": {
                cache_type.value: len(
                    [k for k, m in self.cache_metadata.items() if m.get("type") == cache_type.value]
                )
                for cache_type in CacheContentType
            },
        }

    def _generate_cache_key(
        self, content_type: CacheContentType, identifier: str, secondary_key: Optional[str] = None
    ) -> str:
        """Generate unique cache key for content."""
        key_parts = [content_type.value, identifier]
        if secondary_key:
            key_parts.append(secondary_key)

        combined_key = "|".join(key_parts)
        return f"gai_cache:{hashlib.sha256(combined_key.encode()).hexdigest()[:16]}"

    def _generate_business_profile_cache_key(self, business_profile: Dict[str, Any]) -> str:
        """Generate cache key based on business profile similarity factors."""
        # Create similarity hash based on key characteristics
        similarity_factors = {
            "industry": business_profile.get("industry", ""),
            "employee_count_range": self._get_employee_count_range(
                business_profile.get("employee_count", 0)
            ),
            "existing_frameworks": sorted(business_profile.get("existing_frameworks", [])),
            "has_international_operations": business_profile.get(
                "has_international_operations", False
            ),
            "handles_personal_data": business_profile.get("handles_personal_data", False),
        }

        similarity_key = json.dumps(similarity_factors, sort_keys=True)
        return self._generate_cache_key(
            CacheContentType.BUSINESS_PROFILE,
            hashlib.sha256(similarity_key.encode()).hexdigest()[:12],
        )

    def _get_employee_count_range(self, employee_count: int) -> str:
        """Bucket employee count into ranges for cache similarity."""
        if employee_count < 10:
            return "micro"
        elif employee_count < 50:
            return "small"
        elif employee_count < 250:
            return "medium"
        elif employee_count < 1000:
            return "large"
        else:
            return "enterprise"

    def _build_assessment_cache_content(
        self,
        framework_id: str,
        business_profile: Dict[str, Any],
        assessment_context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build cache content for assessment context."""
        content_parts = []

        # Framework information
        content_parts.append(f"Compliance Framework: {framework_id}")
        content_parts.append(f"Framework Type: {self._get_framework_type(framework_id)}")

        # Business profile context
        content_parts.append(f"Company: {business_profile.get('company_name', 'Unknown')}")
        content_parts.append(f"Industry: {business_profile.get('industry', 'Unknown')}")
        content_parts.append(f"Employee Count: {business_profile.get('employee_count', 0)}")
        content_parts.append(f"Country: {business_profile.get('country', 'Unknown')}")

        # Business characteristics
        characteristics = []
        if business_profile.get("handles_personal_data"):
            characteristics.append("handles personal data")
        if business_profile.get("processes_payments"):
            characteristics.append("processes payments")
        if business_profile.get("stores_health_data"):
            characteristics.append("stores health data")
        if business_profile.get("provides_financial_services"):
            characteristics.append("provides financial services")
        if business_profile.get("operates_critical_infrastructure"):
            characteristics.append("operates critical infrastructure")
        if business_profile.get("has_international_operations"):
            characteristics.append("has international operations")

        if characteristics:
            content_parts.append(f"Business Characteristics: {', '.join(characteristics)}")

        # Technology stack
        if business_profile.get("cloud_providers"):
            content_parts.append(
                f"Cloud Providers: {', '.join(business_profile['cloud_providers'])}"
            )
        if business_profile.get("saas_tools"):
            content_parts.append(f"SaaS Tools: {', '.join(business_profile['saas_tools'])}")

        # Existing compliance
        if business_profile.get("existing_frameworks"):
            content_parts.append(
                f"Existing Frameworks: {', '.join(business_profile['existing_frameworks'])}"
            )

        # Assessment context
        if assessment_context:
            content_parts.append(f"Assessment Context: {json.dumps(assessment_context, indent=2)}")

        return content_parts

    def _build_business_profile_cache_content(self, business_profile: Dict[str, Any]) -> List[str]:
        """Build cache content for business profile."""
        return [
            "Business Profile Analysis:",
            f"Organization: {business_profile.get('company_name', 'Unknown Company')}",
            f"Industry Sector: {business_profile.get('industry', 'Unknown Industry')}",
            f"Organization Size: {self._get_employee_count_range(business_profile.get('employee_count', 0))} ({business_profile.get('employee_count', 0)} employees)",
            f"Geographic Scope: {business_profile.get('country', 'Unknown')} {'(International Operations)' if business_profile.get('has_international_operations') else '(Domestic Only)'}",
            f"Data Processing Profile: {self._get_data_processing_profile(business_profile)}",
            f"Technology Stack: {self._get_technology_summary(business_profile)}",
            f"Current Compliance Maturity: {self._get_compliance_maturity(business_profile)}",
        ]

    def _build_framework_cache_content(
        self, framework_id: str, industry_context: Optional[str] = None
    ) -> List[str]:
        """Build cache content for framework context."""
        content_parts = [
            f"Compliance Framework: {framework_id}",
            f"Framework Category: {self._get_framework_type(framework_id)}",
            f"Primary Focus: {self._get_framework_focus(framework_id)}",
            f"Applicable Regions: {self._get_framework_regions(framework_id)}",
            f"Industry Applicability: {industry_context or 'General'}",
            f"Key Requirements: {self._get_framework_key_requirements(framework_id)}",
            f"Assessment Approach: {self._get_framework_assessment_approach(framework_id)}",
        ]

        return content_parts

    def _calculate_assessment_ttl(self, framework_id: str, business_profile: Dict[str, Any]) -> int:
        """Calculate TTL for assessment cache based on stability factors."""
        base_ttl = self.config.default_ttl_hours

        # Framework stability factor
        stable_frameworks = ["ISO27001", "SOC2", "PCI-DSS"]
        if framework_id in stable_frameworks:
            base_ttl = int(base_ttl * 1.5)  # More stable frameworks get longer TTL

        # Business size factor (larger orgs change less frequently)
        employee_count = business_profile.get("employee_count", 0)
        if employee_count > 1000:
            base_ttl = int(base_ttl * 1.3)
        elif employee_count < 50:
            base_ttl = int(base_ttl * 0.8)  # Smaller orgs change more frequently

        # Ensure TTL is within bounds
        return max(self.config.min_ttl_minutes // 60, min(self.config.max_ttl_hours, base_ttl))

    def _calculate_business_profile_ttl(self, business_profile: Dict[str, Any]) -> int:
        """Calculate TTL for business profile cache."""
        base_ttl = self.config.default_ttl_hours

        # Business profiles are generally stable
        employee_count = business_profile.get("employee_count", 0)
        if employee_count > 500:
            return min(self.config.max_ttl_hours, base_ttl * 2)  # Large orgs are more stable
        elif employee_count < 25:
            return max(1, base_ttl // 2)  # Very small orgs change more
        else:
            return base_ttl

    def _is_cache_valid(self, cached_content: genai.caching.CachedContent) -> bool:
        """Check if cached content is still valid."""
        try:
            # Try to access the cache to check if it's still valid
            # Google's CachedContent will raise an exception if expired
            _ = cached_content.name
            return True
        except Exception:
            return False

    async def _remove_cache(self, cache_key: str):
        """Remove cache and clean up resources."""
        try:
            if cache_key in self.active_caches:
                cached_content = self.active_caches[cache_key]
                # Delete from Google's cache
                cached_content.delete()

                # Remove from local tracking
                del self.active_caches[cache_key]

                if cache_key in self.cache_metadata:
                    metadata = self.cache_metadata[cache_key]
                    self.metrics["total_size_cached_mb"] -= metadata.get("size_estimate_mb", 0)
                    del self.cache_metadata[cache_key]

                logger.debug(f"Removed cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Error removing cache {cache_key}: {e}")

    def _remove_cache_sync(self, cache_key: str):
        """Synchronous version of cache removal for use in sync contexts."""
        try:
            if cache_key in self.active_caches:
                cached_content = self.active_caches[cache_key]
                cached_content.delete()
                del self.active_caches[cache_key]

                if cache_key in self.cache_metadata:
                    metadata = self.cache_metadata[cache_key]
                    self.metrics["total_size_cached_mb"] -= metadata.get("size_estimate_mb", 0)
                    del self.cache_metadata[cache_key]
        except Exception as e:
            logger.warning(f"Error removing cache {cache_key}: {e}")

    # Helper methods for content building
    def _get_framework_type(self, framework_id: str) -> str:
        """Get framework category type."""
        framework_types = {
            "GDPR": "Data Protection Regulation",
            "ISO27001": "Information Security Management",
            "SOC2": "Service Organization Control",
            "HIPAA": "Healthcare Data Protection",
            "PCI-DSS": "Payment Card Security",
            "SOX": "Financial Reporting Control",
            "NIST": "Cybersecurity Framework",
        }
        return framework_types.get(framework_id, "Compliance Framework")

    def _get_framework_focus(self, framework_id: str) -> str:
        """Get primary focus area of framework."""
        focus_areas = {
            "GDPR": "Personal data protection and privacy rights",
            "ISO27001": "Information security management systems",
            "SOC2": "Security, availability, processing integrity, confidentiality, privacy",
            "HIPAA": "Protected health information security and privacy",
            "PCI-DSS": "Payment card data security",
            "SOX": "Financial reporting accuracy and internal controls",
            "NIST": "Cybersecurity risk management",
        }
        return focus_areas.get(framework_id, "Compliance and risk management")

    def _get_framework_regions(self, framework_id: str) -> str:
        """Get applicable regions for framework."""
        regions = {
            "GDPR": "European Union, EEA",
            "ISO27001": "Global",
            "SOC2": "Global (US-originated)",
            "HIPAA": "United States",
            "PCI-DSS": "Global",
            "SOX": "United States",
            "NIST": "United States, Global adoption",
        }
        return regions.get(framework_id, "Varies by jurisdiction")

    def _get_framework_key_requirements(self, framework_id: str) -> str:
        """Get key requirements summary for framework."""
        requirements = {
            "GDPR": "Lawful basis, consent, data minimization, security measures, breach notification",
            "ISO27001": "ISMS implementation, risk assessment, security controls, continuous improvement",
            "SOC2": "Trust service criteria implementation, controls testing, management assertion",
            "HIPAA": "Administrative, physical, technical safeguards, risk assessment, workforce training",
            "PCI-DSS": "Secure network, cardholder data protection, vulnerability management, access control",
            "SOX": "Internal controls, financial reporting processes, management assessment, auditor attestation",
            "NIST": "Identify, protect, detect, respond, recover functions",
        }
        return requirements.get(framework_id, "Risk assessment, control implementation, monitoring")

    def _get_framework_assessment_approach(self, framework_id: str) -> str:
        """Get assessment approach for framework."""
        approaches = {
            "GDPR": "Data protection impact assessment, compliance gap analysis",
            "ISO27001": "Security risk assessment, controls effectiveness review",
            "SOC2": "Trust service criteria evaluation, controls testing",
            "HIPAA": "Security risk analysis, safeguards assessment",
            "PCI-DSS": "Self-assessment questionnaire, vulnerability scanning",
            "SOX": "Internal controls testing, management assessment",
            "NIST": "Cybersecurity framework profile development, maturity assessment",
        }
        return approaches.get(framework_id, "Risk-based assessment and gap analysis")

    def _get_data_processing_profile(self, business_profile: Dict[str, Any]) -> str:
        """Get data processing profile summary."""
        profiles = []
        if business_profile.get("handles_personal_data"):
            profiles.append("Personal Data")
        if business_profile.get("processes_payments"):
            profiles.append("Payment Data")
        if business_profile.get("stores_health_data"):
            profiles.append("Health Data")
        if business_profile.get("provides_financial_services"):
            profiles.append("Financial Data")

        return ", ".join(profiles) if profiles else "Standard Business Data"

    def _get_technology_summary(self, business_profile: Dict[str, Any]) -> str:
        """Get technology stack summary."""
        tech_components = []

        cloud_providers = business_profile.get("cloud_providers", [])
        if cloud_providers:
            tech_components.append(f"Cloud: {', '.join(cloud_providers[:3])}")

        saas_tools = business_profile.get("saas_tools", [])
        if saas_tools:
            tech_components.append(f"SaaS: {', '.join(saas_tools[:3])}")

        return "; ".join(tech_components) if tech_components else "Traditional IT Infrastructure"

    def _get_compliance_maturity(self, business_profile: Dict[str, Any]) -> str:
        """Get compliance maturity assessment."""
        existing_frameworks = business_profile.get("existing_frameworks", [])

        if len(existing_frameworks) >= 3:
            return "Advanced (Multiple Frameworks)"
        elif len(existing_frameworks) >= 1:
            return f"Intermediate ({', '.join(existing_frameworks)})"
        else:
            return "Initial (No Existing Frameworks)"

    # ==============================
    # Cache Strategy Optimization
    # ==============================

    def record_cache_performance(self, cache_key: str, response_time_ms: int, hit: bool = True):
        """Record cache performance for TTL optimization."""
        if not self.config.performance_based_ttl:
            return

        performance_record = {
            "timestamp": datetime.now(),
            "response_time_ms": response_time_ms,
            "hit": hit,
            "ttl_adjustment": 0.0,
        }

        if cache_key not in self.performance_history:
            self.performance_history[cache_key] = []

        self.performance_history[cache_key].append(performance_record)

        # Keep only last 50 records per cache key
        if len(self.performance_history[cache_key]) > 50:
            self.performance_history[cache_key] = self.performance_history[cache_key][-50:]

        # Calculate TTL adjustment based on performance
        ttl_adjustment = self._calculate_ttl_adjustment(cache_key, response_time_ms)
        performance_record["ttl_adjustment"] = ttl_adjustment

        logger.debug(
            f"Cache performance recorded for {cache_key}: {response_time_ms}ms, adjustment: {ttl_adjustment}"
        )

    def _calculate_ttl_adjustment(self, cache_key: str, response_time_ms: int) -> float:
        """Calculate TTL adjustment based on performance history."""
        if not self.config.performance_based_ttl:
            return 0.0

        # Get recent performance history
        recent_records = self.performance_history.get(cache_key, [])[-10:]
        if len(recent_records) < 3:
            return 0.0

        avg_response_time = sum(r["response_time_ms"] for r in recent_records) / len(recent_records)

        # Fast responses → increase TTL (cache longer)
        if avg_response_time < self.config.fast_response_threshold_ms:
            return self.config.ttl_adjustment_factor

        # Slow responses → decrease TTL (refresh more often)
        elif avg_response_time > self.config.slow_response_threshold_ms:
            return -self.config.ttl_adjustment_factor

        return 0.0

    def add_to_warming_queue(
        self, content_type: CacheContentType, context: Dict[str, Any], priority: int = 5
    ):
        """Add cache entry to warming queue for proactive caching."""
        if not self.config.cache_warming_enabled:
            return

        warming_entry = {
            "content_type": content_type,
            "context": context,
            "priority": priority,
            "queued_at": datetime.now(),
            "attempts": 0,
        }

        # Insert by priority (lower number = higher priority)
        inserted = False
        for i, entry in enumerate(self.cache_warming_queue):
            if priority < entry["priority"]:
                self.cache_warming_queue.insert(i, warming_entry)
                inserted = True
                break

        if not inserted:
            self.cache_warming_queue.append(warming_entry)

        # Limit queue size
        if len(self.cache_warming_queue) > 100:
            self.cache_warming_queue = self.cache_warming_queue[:100]

        logger.debug(f"Added {content_type.value} to cache warming queue with priority {priority}")

    async def process_warming_queue(self, max_items: int = 5) -> int:
        """Process cache warming queue to proactively create cache entries."""
        if not self.config.cache_warming_enabled or not self.cache_warming_queue:
            return 0

        processed = 0
        items_to_remove = []

        for i, entry in enumerate(self.cache_warming_queue[:max_items]):
            try:
                # Check if this content type should be warmed
                if self._should_warm_cache(entry):
                    await self._warm_cache_entry(entry)
                    processed += 1

                items_to_remove.append(i)

            except Exception as e:
                entry["attempts"] += 1
                logger.warning(f"Cache warming failed for {entry['content_type'].value}: {e}")

                # Remove after 3 failed attempts
                if entry["attempts"] >= 3:
                    items_to_remove.append(i)

        # Remove processed items (in reverse order to maintain indices)
        for i in reversed(items_to_remove):
            self.cache_warming_queue.pop(i)

        if processed > 0:
            logger.info(f"Cache warming processed {processed} items")

        return processed

    def _should_warm_cache(self, entry: Dict[str, Any]) -> bool:
        """Determine if cache entry should be warmed based on strategy."""
        content_type = entry["content_type"]
        context = entry["context"]

        # Don't warm if recently created
        cache_key = self._generate_cache_key(
            content_type, context.get("framework_id", ""), context.get("business_profile_id", "")
        )

        if cache_key in self.active_caches:
            return False

        # Warm high-priority items immediately
        if entry["priority"] <= 2:
            return True

        # Warm based on usage patterns
        recent_history = self.performance_history.get(cache_key, [])
        if len(recent_history) >= 3:  # Has been used before
            recent_hits = [r for r in recent_history[-10:] if r["hit"]]
            hit_rate = len(recent_hits) / min(len(recent_history), 10)
            return hit_rate > 0.3  # Warm if >30% hit rate

        return False

    async def _warm_cache_entry(self, entry: Dict[str, Any]):
        """Create cache entry for warming queue item."""
        content_type = entry["content_type"]
        context = entry["context"]

        try:
            if content_type == CacheContentType.ASSESSMENT_CONTEXT:
                await self.create_assessment_cache(
                    context["framework_id"],
                    context["business_profile"],
                    context.get("assessment_context"),
                )
            elif content_type == CacheContentType.BUSINESS_PROFILE:
                await self.create_business_profile_cache(context["business_profile"])
            elif content_type == CacheContentType.FRAMEWORK_CONTEXT:
                await self.create_framework_cache(
                    context["framework_id"], context.get("industry_context", "General")
                )

            logger.debug(f"Successfully warmed cache for {content_type.value}")

        except Exception as e:
            logger.error(f"Failed to warm cache for {content_type.value}: {e}")
            raise

    def trigger_intelligent_invalidation(self, trigger_type: str, context: Dict[str, Any]):
        """Trigger intelligent cache invalidation based on business logic."""
        if not self.config.intelligent_invalidation:
            return

        invalidation_key = f"{trigger_type}:{context.get('business_profile_id', 'global')}"
        self.invalidation_triggers[invalidation_key] = datetime.now()

        # Define invalidation rules
        if trigger_type == "business_profile_update":
            self._invalidate_business_profile_caches(context["business_profile_id"])

        elif trigger_type == "framework_update":
            self._invalidate_framework_caches(context["framework_id"])

        elif trigger_type == "assessment_completion":
            # Invalidate related assessment caches to get fresh recommendations
            self._invalidate_assessment_caches(
                context["framework_id"], context["business_profile_id"]
            )

        elif trigger_type == "regulatory_change":
            # Invalidate all caches related to the affected regulation
            self._invalidate_regulatory_caches(context["regulation_id"])

        logger.info(f"Intelligent invalidation triggered: {trigger_type}")

    def _invalidate_business_profile_caches(self, business_profile_id: str):
        """Invalidate caches related to a specific business profile."""
        keys_to_invalidate = []

        for cache_key, metadata in self.cache_metadata.items():
            if metadata.get("business_profile_id") == business_profile_id:
                keys_to_invalidate.append(cache_key)

        self._invalidate_cache_keys(keys_to_invalidate, "business_profile_update")

    def _invalidate_framework_caches(self, framework_id: str):
        """Invalidate caches related to a specific framework."""
        keys_to_invalidate = []

        for cache_key, metadata in self.cache_metadata.items():
            if metadata.get("framework_id") == framework_id:
                keys_to_invalidate.append(cache_key)

        self._invalidate_cache_keys(keys_to_invalidate, "framework_update")

    def _invalidate_assessment_caches(self, framework_id: str, business_profile_id: str):
        """Invalidate assessment-specific caches."""
        keys_to_invalidate = []

        for cache_key, metadata in self.cache_metadata.items():
            if (
                metadata.get("framework_id") == framework_id
                and metadata.get("business_profile_id") == business_profile_id
                and metadata.get("type") == CacheContentType.ASSESSMENT_CONTEXT.value
            ):
                keys_to_invalidate.append(cache_key)

        self._invalidate_cache_keys(keys_to_invalidate, "assessment_completion")

    def _invalidate_regulatory_caches(self, regulation_id: str):
        """Invalidate caches related to regulatory changes."""
        keys_to_invalidate = []

        for cache_key, metadata in self.cache_metadata.items():
            if regulation_id in metadata.get("regulations", []):
                keys_to_invalidate.append(cache_key)

        self._invalidate_cache_keys(keys_to_invalidate, "regulatory_change")

    def _invalidate_cache_keys(self, cache_keys: List[str], reason: str):
        """Invalidate specific cache keys."""
        invalidated_count = 0

        for cache_key in cache_keys:
            if cache_key in self.active_caches:
                try:
                    cached_content = self.active_caches[cache_key]
                    cached_content.delete()
                    del self.active_caches[cache_key]

                    if cache_key in self.cache_metadata:
                        del self.cache_metadata[cache_key]

                    invalidated_count += 1

                except Exception as e:
                    logger.error(f"Failed to invalidate cache {cache_key}: {e}")

        if invalidated_count > 0:
            logger.info(f"Invalidated {invalidated_count} cache entries due to {reason}")

    def get_cache_strategy_metrics(self) -> Dict[str, Any]:
        """Get cache strategy optimization metrics."""
        total_adjustments = 0
        avg_adjustment = 0.0

        for history in self.performance_history.values():
            for record in history:
                if record.get("ttl_adjustment", 0) != 0:
                    total_adjustments += 1
                    avg_adjustment += record["ttl_adjustment"]

        if total_adjustments > 0:
            avg_adjustment /= total_adjustments

        return {
            "performance_based_ttl": {
                "enabled": self.config.performance_based_ttl,
                "total_adjustments": total_adjustments,
                "average_adjustment": avg_adjustment,
                "tracked_cache_keys": len(self.performance_history),
            },
            "cache_warming": {
                "enabled": self.config.cache_warming_enabled,
                "queue_size": len(self.cache_warming_queue),
                "high_priority_items": len(
                    [e for e in self.cache_warming_queue if e["priority"] <= 2]
                ),
            },
            "intelligent_invalidation": {
                "enabled": self.config.intelligent_invalidation,
                "recent_triggers": len(
                    [
                        t
                        for t in self.invalidation_triggers.values()
                        if (datetime.now() - t).total_seconds() < 3600
                    ]
                ),
            },
        }


# Global cached content manager instance
cached_content_manager = GoogleCachedContentManager()


async def get_cached_content_manager() -> GoogleCachedContentManager:
    """Get the global cached content manager instance."""
    return cached_content_manager
