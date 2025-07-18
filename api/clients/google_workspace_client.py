"""
Google Workspace API Client for compliance evidence collection.
Follows the foundation architecture pattern for enterprise API integrations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from .base_api_client import (
    BaseAPIClient,
    APICredentials,
    AuthType,
    CollectionResult,
    EvidenceQuality,
)

# Mock Google API imports for graceful degradation
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

    class Credentials:
        def __init__(self, *args, **kwargs):
            self.expired = False
            self.refresh_token = None
            self.valid = True
            self.token = "mock_token"

        @classmethod
        def from_authorized_user_info(cls, info, scopes):
            return cls()

        def refresh(self, request):
            pass

    class Request:
        pass

    def build(*args, **kwargs):
        return MockGoogleService()

    class HttpError(Exception):
        pass

    class MockGoogleService:
        def activities(self):
            return self

        def users(self):
            return self

        def groups(self):
            return self

        def list(self, **kwargs):
            return self

        def execute(self):
            return {"items": []}


logger = logging.getLogger(__name__)


class GoogleWorkspaceCredentials(BaseModel):
    """Google Workspace OAuth2 credentials."""

    client_id: str = Field(..., description="Google OAuth2 client ID")
    client_secret: str = Field(..., description="Google OAuth2 client secret")
    refresh_token: str = Field(..., description="OAuth2 refresh token")
    access_token: Optional[str] = Field(None, description="Current access token")
    domain: str = Field(..., description="Google Workspace domain")

    class Config:
        extra = "allow"


class GoogleWorkspaceAPIClient(BaseAPIClient):
    """Google Workspace API client for compliance evidence collection."""

    SCOPES = [
        "https://www.googleapis.com/auth/admin.reports.audit.readonly",
        "https://www.googleapis.com/auth/admin.directory.user.readonly",
        "https://www.googleapis.com/auth/admin.directory.group.readonly",
        "https://www.googleapis.com/auth/admin.directory.domain.readonly",
        "https://www.googleapis.com/auth/admin.security.readonly",
    ]

    def __init__(self, credentials: APICredentials):
        super().__init__(credentials)
        self.service_cache = {}
        self.credentials_obj: Optional[Credentials] = None

    def get_base_url(self) -> str:
        """Google APIs use different base URLs per service."""
        return "https://www.googleapis.com"

    async def authenticate(self) -> bool:
        """Authenticate with Google Workspace using OAuth2."""
        try:
            if not GOOGLE_AVAILABLE:
                logger.warning("Google API libraries not available - using mock authentication")
                self.authenticated = True
                return True

            # Parse credentials
            if self.credentials.auth_type != AuthType.OAUTH2:
                raise ValueError("Google Workspace requires OAuth2 authentication")

            creds_data = self.credentials.credentials
            workspace_creds = GoogleWorkspaceCredentials(**creds_data)

            # Create Google credentials object
            self.credentials_obj = Credentials(
                token=workspace_creds.access_token,
                refresh_token=workspace_creds.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=workspace_creds.client_id,
                client_secret=workspace_creds.client_secret,
                scopes=self.SCOPES,
            )

            # Refresh token if needed
            if self.credentials_obj.expired and self.credentials_obj.refresh_token:
                self.credentials_obj.refresh(Request())
                logger.info("Google Workspace credentials refreshed")

            self.authenticated = self.credentials_obj.valid
            return self.authenticated

        except Exception as e:
            logger.error(f"Google Workspace authentication failed: {e}")
            self.authenticated = False
            return False

    async def test_connection(self) -> Tuple[bool, str]:
        """Test connection to Google Workspace."""
        try:
            if not await self.authenticate():
                return False, "Authentication failed"

            if not GOOGLE_AVAILABLE:
                return True, "Mock connection successful"

            # Test with a simple API call
            service = build("admin", "directory_v1", credentials=self.credentials_obj)
            service.domains().list(customer="my_customer").execute()

            return True, "Connection successful"

        except Exception as e:
            logger.error(f"Google Workspace connection test failed: {e}")
            return False, str(e)

    def _get_service(self, service_name: str, version: str):
        """Get cached Google API service."""
        key = f"{service_name}_{version}"
        if key not in self.service_cache:
            if not GOOGLE_AVAILABLE:
                self.service_cache[key] = MockGoogleService()
            else:
                self.service_cache[key] = build(
                    service_name, version, credentials=self.credentials_obj
                )
        return self.service_cache[key]

    async def collect_users_evidence(self) -> CollectionResult:
        """Collect user directory evidence."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")

            service = self._get_service("admin", "directory_v1")

            # Get users
            users_result = service.users().list(customer="my_customer", maxResults=500).execute()
            users = users_result.get("users", [])

            # Calculate quality score
            total_users = len(users)
            mfa_enabled = sum(1 for user in users if user.get("isEnforcedIn2Sv", False))
            suspended_users = sum(1 for user in users if user.get("suspended", False))

            quality_score = self._calculate_users_quality(total_users, mfa_enabled, suspended_users)

            evidence_data = {
                "users": users,
                "summary": {
                    "total_users": total_users,
                    "active_users": total_users - suspended_users,
                    "suspended_users": suspended_users,
                    "mfa_enabled_users": mfa_enabled,
                    "mfa_compliance_rate": (mfa_enabled / total_users * 100)
                    if total_users > 0
                    else 0,
                },
            }

            return CollectionResult(
                evidence_type="user_directory",
                source_system="google_workspace",
                resource_id="users",
                resource_name="Google Workspace Users",
                data=evidence_data,
                quality=quality_score,
                compliance_controls=["CC6.1", "CC6.2", "CC6.7"],
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to collect users evidence: {e}")
            raise

    async def collect_groups_evidence(self) -> CollectionResult:
        """Collect groups and access control evidence."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")

            service = self._get_service("admin", "directory_v1")

            # Get groups
            groups_result = service.groups().list(customer="my_customer", maxResults=200).execute()
            groups = groups_result.get("groups", [])

            # Get group memberships
            group_memberships = {}
            for group in groups:
                try:
                    members_result = service.members().list(groupKey=group["id"]).execute()
                    group_memberships[group["id"]] = members_result.get("members", [])
                except Exception as e:
                    logger.warning(f"Failed to get members for group {group['id']}: {e}")
                    group_memberships[group["id"]] = []

            quality_score = self._calculate_groups_quality(groups, group_memberships)

            evidence_data = {
                "groups": groups,
                "group_memberships": group_memberships,
                "summary": {
                    "total_groups": len(groups),
                    "security_groups": len(
                        [g for g in groups if "security" in g.get("name", "").lower()]
                    ),
                    "distribution_groups": len(
                        [g for g in groups if "distribution" in g.get("name", "").lower()]
                    ),
                },
            }

            return CollectionResult(
                evidence_type="access_groups",
                source_system="google_workspace",
                resource_id="groups",
                resource_name="Google Workspace Groups",
                data=evidence_data,
                quality=quality_score,
                compliance_controls=["CC6.1", "CC6.2", "CC6.3"],
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to collect groups evidence: {e}")
            raise

    async def collect_admin_logs_evidence(self) -> CollectionResult:
        """Collect admin activity logs evidence."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")

            service = self._get_service("admin", "reports_v1")

            # Get admin activities from last 7 days
            start_time = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            activities_result = (
                service.activities()
                .list(userKey="all", applicationName="admin", startTime=start_time, maxResults=1000)
                .execute()
            )

            activities = activities_result.get("items", [])

            quality_score = self._calculate_logs_quality(activities)

            evidence_data = {
                "activities": activities,
                "summary": {
                    "total_events": len(activities),
                    "date_range": f"Last 7 days from {start_time}",
                    "unique_users": len(
                        set(act.get("actor", {}).get("email", "") for act in activities)
                    ),
                    "event_types": list(
                        set(
                            event.get("name", "")
                            for act in activities
                            for event in act.get("events", [])
                        )
                    ),
                },
            }

            return CollectionResult(
                evidence_type="admin_activity_logs",
                source_system="google_workspace",
                resource_id="admin_logs",
                resource_name="Google Workspace Admin Logs",
                data=evidence_data,
                quality=quality_score,
                compliance_controls=["CC7.1", "CC7.2", "CC7.3"],
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to collect admin logs evidence: {e}")
            raise

    async def collect_login_logs_evidence(self) -> CollectionResult:
        """Collect user login logs evidence."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")

            service = self._get_service("admin", "reports_v1")

            # Get login activities from last 7 days
            start_time = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            activities_result = (
                service.activities()
                .list(userKey="all", applicationName="login", startTime=start_time, maxResults=1000)
                .execute()
            )

            activities = activities_result.get("items", [])

            quality_score = self._calculate_logs_quality(activities)

            # Analyze login patterns
            successful_logins = []
            failed_logins = []

            for activity in activities:
                for event in activity.get("events", []):
                    if "login_success" in event.get("name", ""):
                        successful_logins.append(activity)
                    elif "login_failure" in event.get("name", ""):
                        failed_logins.append(activity)

            evidence_data = {
                "activities": activities,
                "summary": {
                    "total_events": len(activities),
                    "successful_logins": len(successful_logins),
                    "failed_logins": len(failed_logins),
                    "date_range": f"Last 7 days from {start_time}",
                    "unique_users": len(
                        set(act.get("actor", {}).get("email", "") for act in activities)
                    ),
                },
            }

            return CollectionResult(
                evidence_type="user_access_logs",
                source_system="google_workspace",
                resource_id="login_logs",
                resource_name="Google Workspace Login Logs",
                data=evidence_data,
                quality=quality_score,
                compliance_controls=["CC6.1", "CC6.2", "CC7.2"],
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to collect login logs evidence: {e}")
            raise

    async def collect_domain_evidence(self) -> CollectionResult:
        """Collect domain and security settings evidence."""
        try:
            if not await self.authenticate():
                raise Exception("Authentication failed")

            service = self._get_service("admin", "directory_v1")

            # Get domain information
            domains_result = service.domains().list(customer="my_customer").execute()
            domains = domains_result.get("domains", [])

            quality_score = self._calculate_domain_quality(domains)

            evidence_data = {
                "domains": domains,
                "summary": {
                    "total_domains": len(domains),
                    "primary_domain": next(
                        (d["domainName"] for d in domains if d.get("isPrimary")), None
                    ),
                    "verified_domains": len([d for d in domains if d.get("verified")]),
                },
            }

            return CollectionResult(
                evidence_type="domain_configuration",
                source_system="google_workspace",
                resource_id="domains",
                resource_name="Google Workspace Domains",
                data=evidence_data,
                quality=quality_score,
                compliance_controls=["CC6.1", "CC6.6"],
                collected_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to collect domain evidence: {e}")
            raise

    def _calculate_users_quality(
        self, total_users: int, mfa_enabled: int, suspended: int
    ) -> EvidenceQuality:
        """Calculate quality score for users evidence."""
        if total_users == 0:
            return EvidenceQuality.LOW

        mfa_rate = mfa_enabled / total_users
        suspension_rate = suspended / total_users

        # High quality: >80% MFA, <5% suspended
        if mfa_rate > 0.8 and suspension_rate < 0.05:
            return EvidenceQuality.HIGH
        # Medium quality: >50% MFA, <10% suspended
        elif mfa_rate > 0.5 and suspension_rate < 0.1:
            return EvidenceQuality.MEDIUM
        else:
            return EvidenceQuality.LOW

    def _calculate_groups_quality(self, groups: List[Dict], memberships: Dict) -> EvidenceQuality:
        """Calculate quality score for groups evidence."""
        if not groups:
            return EvidenceQuality.LOW

        # Check for proper group organization
        has_security_groups = any("security" in g.get("name", "").lower() for g in groups)
        has_proper_naming = sum(1 for g in groups if len(g.get("name", "")) > 5) / len(groups) > 0.8

        if has_security_groups and has_proper_naming:
            return EvidenceQuality.HIGH
        elif has_security_groups or has_proper_naming:
            return EvidenceQuality.MEDIUM
        else:
            return EvidenceQuality.LOW

    def _calculate_logs_quality(self, activities: List[Dict]) -> EvidenceQuality:
        """Calculate quality score for log evidence."""
        if not activities:
            return EvidenceQuality.LOW

        # Quality based on log volume and recency
        recent_events = sum(
            1
            for act in activities
            if (
                datetime.utcnow()
                - datetime.fromisoformat(act.get("id", {}).get("time", "").replace("Z", "+00:00"))
            ).days
            < 3
        )

        if recent_events > 50:
            return EvidenceQuality.HIGH
        elif recent_events > 10:
            return EvidenceQuality.MEDIUM
        else:
            return EvidenceQuality.LOW

    def _calculate_domain_quality(self, domains: List[Dict]) -> EvidenceQuality:
        """Calculate quality score for domain evidence."""
        if not domains:
            return EvidenceQuality.LOW

        verified_domains = sum(1 for d in domains if d.get("verified"))
        verification_rate = verified_domains / len(domains)

        if verification_rate == 1.0:
            return EvidenceQuality.HIGH
        elif verification_rate > 0.8:
            return EvidenceQuality.MEDIUM
        else:
            return EvidenceQuality.LOW

    def get_supported_evidence_types(self) -> List[str]:
        """Get list of supported evidence types."""
        return [
            "user_directory",
            "access_groups",
            "admin_activity_logs",
            "user_access_logs",
            "domain_configuration",
        ]

    async def collect_all_evidence(self) -> List[CollectionResult]:
        """Collect all available evidence types."""
        results = []

        evidence_collectors = [
            self.collect_users_evidence,
            self.collect_groups_evidence,
            self.collect_admin_logs_evidence,
            self.collect_login_logs_evidence,
            self.collect_domain_evidence,
        ]

        # Run collectors in parallel
        for collector in evidence_collectors:
            try:
                result = await collector()
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to collect evidence with {collector.__name__}: {e}")
                continue

        return results
