"""
Base API client for all enterprise integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import asyncio
import aiohttp
import time
import hashlib
from datetime import datetime
from enum import Enum

from config.logging_config import get_logger

logger = get_logger(__name__)


class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    ROLE_ASSUMPTION = "role_assumption"
    CERTIFICATE = "certificate"


@dataclass
class APICredentials:
    provider: str
    auth_type: AuthType
    credentials: Dict[str, Any]
    expires_at: Optional[datetime] = None
    scopes: Optional[List[str]] = None
    region: Optional[str] = None


@dataclass
class APIRequest:
    method: str
    endpoint: str
    params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    timeout: int = 30
    retry_attempts: int = 3


@dataclass
class APIResponse:
    status_code: int
    data: Any
    headers: Dict[str, str]
    response_time: float
    request_id: str


@dataclass
class EvidenceItem:
    evidence_type: str
    resource_id: str
    resource_name: str
    data: Dict[str, Any]
    compliance_controls: List[str]
    collection_timestamp: datetime
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class EvidenceQuality(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class CollectionResult:
    success: bool
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    collection_metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    total_collected: int = 0


class APIException(Exception):
    """Base API exception"""

    pass


class APITimeoutException(APIException):
    """API timeout exception"""

    pass


class APIConnectionException(APIException):
    """API connection exception"""

    pass


class APIAuthenticationException(APIException):
    """API authentication exception"""

    pass


class APIRateLimitException(APIException):
    """API rate limit exception"""

    pass


class UnsupportedEvidenceTypeException(APIException):
    """Unsupported evidence type exception"""

    pass


class BaseAPIClient(ABC):
    """Base class for all enterprise API clients"""

    def __init__(self, credentials: APICredentials):
        self.credentials = credentials
        self.base_url = self.get_base_url()
        self.session: Optional[aiohttp.ClientSession] = None
        self.authenticated = False
        self.last_auth_check = None
        self.request_count = 0
        self.error_count = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name"""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """Get base URL for API"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the API"""
        pass

    @abstractmethod
    async def refresh_credentials(self) -> bool:
        """Refresh authentication credentials"""
        pass

    @abstractmethod
    def get_evidence_collector(self, evidence_type: str):
        """Get evidence collector for specific evidence type"""
        pass

    @abstractmethod
    def get_health_endpoint(self) -> str:
        """Get provider-specific health check endpoint"""
        pass

    async def ensure_authenticated(self) -> bool:
        """Ensure client is authenticated"""
        now = datetime.utcnow()

        # Check if we need to re-authenticate
        if (
            not self.authenticated
            or not self.last_auth_check
            or (now - self.last_auth_check).total_seconds() > 3600
        ):  # Re-auth every hour
            self.authenticated = await self.authenticate()
            self.last_auth_check = now

        return self.authenticated

    async def make_request(self, request: APIRequest) -> APIResponse:
        """Make authenticated API request with retry logic"""

        # Ensure authentication
        if not await self.ensure_authenticated():
            raise APIAuthenticationException(f"Authentication failed for {self.provider_name}")

        # Execute request with retry logic
        last_exception = None

        for attempt in range(request.retry_attempts):
            try:
                response = await self._execute_request(request)
                self.request_count += 1
                return response

            except APIRateLimitException as e:
                # Handle rate limiting with exponential backoff
                if attempt < request.retry_attempts - 1:
                    wait_time = (2**attempt) + (attempt * 0.1)  # Exponential backoff with jitter
                    logger.warning(
                        f"Rate limited by {self.provider_name}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                    last_exception = e
                    continue
                else:
                    raise e

            except (APITimeoutException, APIConnectionException) as e:
                # Handle timeouts and connection errors with retry
                if attempt < request.retry_attempts - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Request failed for {self.provider_name}, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    last_exception = e
                    continue
                else:
                    raise e

            except Exception as e:
                # Don't retry on other exceptions
                self.error_count += 1
                raise e

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise APIException(f"All retry attempts failed for {self.provider_name}")

    async def _execute_request(self, request: APIRequest) -> APIResponse:
        """Execute HTTP request with full error handling"""

        if not self.session:
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(timeout=timeout)

        start_time = time.time()
        request_id = self._generate_request_id(request)

        try:
            # Prepare headers
            headers = await self._prepare_headers(request.headers or {})

            # Log request for debugging
            logger.debug(
                f"Making {request.method} request to {self.provider_name}: {request.endpoint}"
            )

            # Execute request
            url = f"{self.base_url}{request.endpoint}" if self.base_url else request.endpoint

            async with self.session.request(
                method=request.method,
                url=url,
                params=request.params,
                headers=headers,
                json=request.body if request.method not in ["GET", "DELETE"] else None,
                timeout=aiohttp.ClientTimeout(total=request.timeout),
            ) as response:
                response_time = time.time() - start_time

                # Handle different response types
                if response.status == 429:
                    raise APIRateLimitException(f"Rate limited by {self.provider_name}")
                elif response.status == 401:
                    self.authenticated = False
                    raise APIAuthenticationException(
                        f"Authentication failed for {self.provider_name}"
                    )
                elif response.status >= 500:
                    raise APIConnectionException(
                        f"Server error from {self.provider_name}: {response.status}"
                    )
                elif response.status >= 400:
                    error_text = await response.text()
                    raise APIException(
                        f"Client error from {self.provider_name}: {response.status} - {error_text}"
                    )

                # Parse response data
                response_data = await self._parse_response(response)

                # Log successful request
                logger.debug(
                    f"Successful {request.method} request to {self.provider_name}: {response.status}"
                )

                return APIResponse(
                    status_code=response.status,
                    data=response_data,
                    headers=dict(response.headers),
                    response_time=response_time,
                    request_id=request_id,
                )

        except asyncio.TimeoutError:
            raise APITimeoutException(
                f"Request to {self.provider_name} timed out after {request.timeout}s"
            )
        except aiohttp.ClientError as e:
            raise APIConnectionException(f"Connection error to {self.provider_name}: {str(e)}")
        except Exception as e:
            if isinstance(
                e,
                (
                    APIException,
                    APITimeoutException,
                    APIConnectionException,
                    APIAuthenticationException,
                    APIRateLimitException,
                ),
            ):
                raise e
            else:
                raise APIException(f"Unexpected error calling {self.provider_name}: {str(e)}")

    async def _parse_response(self, response: aiohttp.ClientResponse) -> Any:
        """Parse API response data"""
        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            return await response.json()
        elif "text/" in content_type:
            return await response.text()
        else:
            return await response.read()

    async def _prepare_headers(self, additional_headers: Dict[str, str] = None) -> Dict[str, str]:
        """Prepare headers with authentication - to be implemented by subclasses"""
        headers = {
            "User-Agent": "ruleIQ-compliance-collector/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _generate_request_id(self, request: APIRequest) -> str:
        """Generate unique request ID for tracking"""
        request_data = f"{request.method}:{request.endpoint}:{time.time()}"
        return hashlib.md5(request_data.encode()).hexdigest()[:12]

    async def collect_evidence(self, evidence_type: str, **kwargs) -> List[EvidenceItem]:
        """Collect specific evidence type from this API"""
        evidence_collector = self.get_evidence_collector(evidence_type)
        if not evidence_collector:
            supported_types = self.get_supported_evidence_types()
            raise UnsupportedEvidenceTypeException(
                f"{evidence_type} not supported by {self.provider_name}. "
                f"Supported types: {', '.join(supported_types)}"
            )

        return await evidence_collector.collect(**kwargs)

    def get_supported_evidence_types(self) -> List[str]:
        """Get list of supported evidence types for this provider"""
        # This should be implemented by subclasses
        return []

    async def health_check(self) -> Dict[str, Any]:
        """Check API health and connectivity"""
        try:
            start_time = time.time()

            # Use a simple health check endpoint
            health_request = APIRequest("GET", self.get_health_endpoint())
            await self.make_request(health_request)

            response_time = time.time() - start_time

            return {
                "status": "healthy",
                "response_time": response_time,
                "provider": self.provider_name,
                "timestamp": datetime.utcnow(),
                "request_count": self.request_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(self.request_count, 1),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": self.provider_name,
                "timestamp": datetime.utcnow(),
                "request_count": self.request_count,
                "error_count": self.error_count,
            }

    async def close(self):
        """Close the API client and cleanup resources"""
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class BaseEvidenceCollector(ABC):
    """Base class for evidence collectors"""

    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = get_logger(f"{self.__class__.__name__}")

    @abstractmethod
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        """Collect evidence items"""
        pass

    def create_evidence_item(
        self,
        evidence_type: str,
        resource_id: str,
        resource_name: str,
        data: Dict[str, Any],
        compliance_controls: List[str],
        quality_score: float = 1.0,
        metadata: Dict[str, Any] = None,
    ) -> EvidenceItem:
        """Helper method to create evidence items"""
        return EvidenceItem(
            evidence_type=evidence_type,
            resource_id=resource_id,
            resource_name=resource_name,
            data=data,
            compliance_controls=compliance_controls,
            collection_timestamp=datetime.utcnow(),
            quality_score=quality_score,
            metadata=metadata or {},
        )
