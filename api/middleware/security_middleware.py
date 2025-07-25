"""
Comprehensive security middleware for ruleIQ backend
"""

import time
import uuid
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.context import request_id_var, user_id_var
from config.logging_config import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers"""
        start_time = time.time()
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Log request details
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Add security headers to response
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = request_id
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s"
            }
        )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old requests
        window_start = current_time - self.window_seconds
        self.requests[client_ip] = [
            req_time for req_time in self.requests.get(client_ip, [])
            if req_time > window_start
        ]
        
        # Check rate limit
        if len(self.requests.get(client_ip, [])) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path
                }
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware with security checks"""
    
    def __init__(self, app, allowed_origins: list):
        super().__init__(app)
        self.allowed_origins = allowed_origins
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS preflight and requests"""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            if origin and origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        # Handle actual requests
        response = await call_next(request)
        
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Detailed request logging middleware"""
    
    async def dispatch(self, request: Request, call_next):
        """Log detailed request information"""
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        
        # Log request body for debugging (be careful with sensitive data)
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) > 1000:  # Truncate large bodies
                    body = body[:1000] + b"..."
            except Exception:
                body = b"<could not read body>"
        
        logger.info(
            "Request details",
            extra={
                "request_id": request_id,
                "user_id": str(user_id) if user_id else None,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers),
                "body_length": len(body) if body else 0
            }
        )
        
        return await call_next(request)