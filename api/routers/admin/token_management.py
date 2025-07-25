"""
Admin endpoints for token blacklist management.

Provides administrative tools for:
- Viewing blacklist statistics
- Managing blacklisted tokens
- Analyzing security patterns
- Performing maintenance operations
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from api.dependencies.auth import get_current_active_user
from api.dependencies.token_blacklist import get_token_blacklist
from database.user import User

router = APIRouter(prefix="/admin/tokens", tags=["admin", "token-management"])


class BlacklistStatsResponse(BaseModel):
    """Response model for blacklist statistics."""
    current_blacklisted_tokens: int
    total_blacklisted: int
    blacklisted_today: int
    expired_tokens_cleaned: int
    suspicious_patterns_detected: int
    bulk_operations_count: int
    last_cleanup: Optional[str]


class BlacklistEntryResponse(BaseModel):
    """Response model for blacklist entry details."""
    token_hash: str
    reason: str
    blacklisted_at: str
    expires_at: str
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict]


class TokenActionRequest(BaseModel):
    """Request model for token actions."""
    token: str
    reason: Optional[str] = "administrative_action"


class BulkTokenActionRequest(BaseModel):
    """Request model for bulk token actions."""
    user_id: str
    reason: str = "security_action"
    exclude_current_token: Optional[str] = None


def require_admin_role(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role for access."""
    # This should check for actual admin role in your user model
    # For now, we'll use a simple check
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/statistics", response_model=BlacklistStatsResponse)
async def get_blacklist_statistics(
    admin_user: User = Depends(require_admin_role)
):
    """Get comprehensive blacklist statistics."""
    blacklist = await get_token_blacklist()
    stats = await blacklist.get_blacklist_statistics()
    
    return BlacklistStatsResponse(**stats)


@router.get("/entry/{token_hash}")
async def get_blacklist_entry(
    token_hash: str,
    admin_user: User = Depends(require_admin_role)
) -> Optional[BlacklistEntryResponse]:
    """Get details for a specific blacklisted token by hash."""
    blacklist = await get_token_blacklist()
    
    # Note: We would need to store token hash mappings to implement this fully
    # This is a placeholder for the interface
    return {"message": "Token hash lookup requires additional implementation"}


@router.post("/blacklist")
async def blacklist_token_admin(
    request: TokenActionRequest,
    admin_user: User = Depends(require_admin_role)
):
    """Administratively blacklist a token."""
    blacklist = await get_token_blacklist()
    
    success = await blacklist.blacklist_token(
        token=request.token,
        reason=request.reason,
        user_id=str(admin_user.id),
        metadata={"admin_action": True, "admin_user": str(admin_user.id)}
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to blacklist token"
        )
    
    return {"message": "Token successfully blacklisted", "reason": request.reason}


@router.delete("/blacklist")
async def remove_token_from_blacklist(
    request: TokenActionRequest,
    admin_user: User = Depends(require_admin_role)
):
    """Remove a token from the blacklist."""
    blacklist = await get_token_blacklist()
    
    success = await blacklist.remove_token_from_blacklist(request.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found in blacklist"
        )
    
    return {"message": "Token removed from blacklist"}


@router.post("/blacklist/user")
async def blacklist_user_tokens(
    request: BulkTokenActionRequest,
    admin_user: User = Depends(require_admin_role)
):
    """Blacklist all tokens for a specific user."""
    blacklist = await get_token_blacklist()
    
    count = await blacklist.blacklist_user_tokens(
        user_id=request.user_id,
        reason=request.reason,
        exclude_current_token=request.exclude_current_token
    )
    
    return {
        "message": f"Blacklisted {count} tokens for user {request.user_id}",
        "tokens_blacklisted": count,
        "reason": request.reason
    }


@router.post("/cleanup")
async def cleanup_expired_tokens(
    admin_user: User = Depends(require_admin_role)
):
    """Manually trigger cleanup of expired tokens."""
    blacklist = await get_token_blacklist()
    
    cleaned_count = await blacklist.cleanup_expired_tokens()
    
    return {
        "message": f"Cleaned up {cleaned_count} expired tokens",
        "tokens_cleaned": cleaned_count,
        "cleanup_time": datetime.utcnow().isoformat()
    }


@router.get("/health")
async def get_blacklist_health(
    admin_user: User = Depends(require_admin_role)
):
    """Get health status of the token blacklist system."""
    try:
        blacklist = await get_token_blacklist()
        stats = await blacklist.get_blacklist_statistics()
        
        # Basic health checks
        health_status = "healthy"
        issues = []
        
        # Check for high blacklist volume (potential attack)
        if stats.get("blacklisted_today", 0) > 1000:
            health_status = "warning"
            issues.append("High blacklist volume detected")
        
        # Check for suspicious patterns
        if stats.get("suspicious_patterns_detected", 0) > 10:
            health_status = "warning"
            issues.append("Multiple suspicious patterns detected")
        
        return {
            "status": health_status,
            "issues": issues,
            "statistics": stats,
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "issues": [f"Blacklist system error: {str(e)}"],
            "last_check": datetime.utcnow().isoformat()
        }


@router.get("/patterns")
async def get_suspicious_patterns(
    hours: int = Query(24, description="Hours to look back for patterns"),
    admin_user: User = Depends(require_admin_role)
):
    """Get analysis of suspicious blacklisting patterns."""
    # This would require more sophisticated pattern analysis
    # For now, return a placeholder response
    return {
        "message": "Pattern analysis requires additional implementation",
        "analysis_period_hours": hours,
        "patterns_detected": 0,
        "recommendations": [
            "Implement IP-based pattern detection",
            "Add user behavior analysis",
            "Create automated alerting for mass blacklisting events"
        ]
    }