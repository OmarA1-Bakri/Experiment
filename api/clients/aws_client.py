"""
AWS API client for collecting infrastructure and security evidence
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from typing import Dict, List, Any, Optional
import json
from datetime import datetime, timedelta

from .base_api_client import (
    BaseAPIClient,
    APICredentials,
    EvidenceItem,
    BaseEvidenceCollector,
    APIException,
    AuthType,
)
from config.logging_config import get_logger

logger = get_logger(__name__)


class AWSAPIException(APIException):
    """AWS-specific API exception"""

    pass


class AWSAPIClient(BaseAPIClient):
    """AWS API client for collecting infrastructure and security evidence"""

    def __init__(self, credentials: APICredentials):
        super().__init__(credentials)
        self.aws_session: Optional[boto3.Session] = None
        self.region = credentials.region or "us-east-1"

    @property
    def provider_name(self) -> str:
        return "aws"

    def get_base_url(self) -> str:
        return ""  # Not used for boto3

    async def authenticate(self) -> bool:
        """Authenticate using AWS credentials (Access Key, Role Assumption, etc.)"""
        try:
            if self.credentials.auth_type == AuthType.API_KEY:
                # Access key authentication
                self.aws_session = boto3.Session(
                    aws_access_key_id=self.credentials.credentials["access_key_id"],
                    aws_secret_access_key=self.credentials.credentials["secret_access_key"],
                    region_name=self.region,
                )

            elif self.credentials.auth_type == AuthType.ROLE_ASSUMPTION:
                # STS role assumption
                sts_client = boto3.client("sts")

                assume_role_params = {
                    "RoleArn": self.credentials.credentials["role_arn"],
                    "RoleSessionName": "ruleiq-evidence-collection",
                }

                # Add external ID if provided
                if "external_id" in self.credentials.credentials:
                    assume_role_params["ExternalId"] = self.credentials.credentials["external_id"]

                response = sts_client.assume_role(**assume_role_params)

                credentials = response["Credentials"]
                self.aws_session = boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                    region_name=self.region,
                )

                # Update credentials expiration
                self.credentials.expires_at = credentials["Expiration"]

            else:
                raise AWSAPIException(f"Unsupported AWS auth type: {self.credentials.auth_type}")

            # Test authentication by getting caller identity
            sts = self.aws_session.client("sts")
            caller_identity = sts.get_caller_identity()

            logger.info(
                f"AWS authentication successful for account: {caller_identity.get('Account')}"
            )
            return True

        except (ClientError, NoCredentialsError, BotoCoreError) as e:
            logger.error(f"AWS authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during AWS authentication: {e}")
            return False

    async def refresh_credentials(self) -> bool:
        """Refresh AWS credentials if using role assumption"""
        if self.credentials.auth_type == AuthType.ROLE_ASSUMPTION:
            return await self.authenticate()
        return True

    def get_evidence_collector(self, evidence_type: str):
        """Get AWS evidence collector for specific evidence type"""
        if not self.aws_session:
            return None

        collectors = {
            "iam_policies": AWSIAMEvidenceCollector(self),
            "iam_users": AWSIAMEvidenceCollector(self),
            "iam_roles": AWSIAMEvidenceCollector(self),
            "security_groups": AWSSecurityGroupCollector(self),
            "vpc_configuration": AWSVPCCollector(self),
            "cloudtrail_logs": AWSCloudTrailCollector(self),
            "config_rules": AWSConfigCollector(self),
            "guardduty_findings": AWSGuardDutyCollector(self),
            "inspector_findings": AWSInspectorCollector(self),
            "compliance_reports": AWSComplianceCollector(self),
            "s3_buckets": AWSS3Collector(self),
            "ec2_instances": AWSEC2Collector(self),
        }
        return collectors.get(evidence_type)

    def get_supported_evidence_types(self) -> List[str]:
        """Get list of supported evidence types for AWS"""
        return [
            "iam_policies",
            "iam_users",
            "iam_roles",
            "security_groups",
            "vpc_configuration",
            "cloudtrail_logs",
            "config_rules",
            "guardduty_findings",
            "inspector_findings",
            "compliance_reports",
            "s3_buckets",
            "ec2_instances",
        ]

    def get_health_endpoint(self) -> str:
        return "/health"  # Custom health check method

    async def health_check(self) -> Dict[str, Any]:
        """AWS-specific health check using STS get_caller_identity"""
        try:
            if not await self.ensure_authenticated():
                raise AWSAPIException("Authentication failed")

            start_time = datetime.utcnow()

            # Use STS get_caller_identity as health check
            sts = self.aws_session.client("sts")
            caller_identity = sts.get_caller_identity()

            response_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "status": "healthy",
                "response_time": response_time,
                "provider": self.provider_name,
                "timestamp": datetime.utcnow(),
                "account_id": caller_identity.get("Account"),
                "user_id": caller_identity.get("UserId"),
                "arn": caller_identity.get("Arn"),
                "region": self.region,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": self.provider_name,
                "timestamp": datetime.utcnow(),
                "region": self.region,
            }


class AWSIAMEvidenceCollector(BaseEvidenceCollector):
    """Collect IAM-related evidence from AWS"""

    async def collect(self, **kwargs) -> List[EvidenceItem]:
        """Collect IAM policies, users, roles, and access patterns"""
        evidence = []

        try:
            iam = self.api_client.aws_session.client("iam")

            # Collect IAM policies
            evidence.extend(await self._collect_iam_policies(iam))

            # Collect IAM users
            evidence.extend(await self._collect_iam_users(iam))

            # Collect IAM roles
            evidence.extend(await self._collect_iam_roles(iam))

        except ClientError as e:
            self.logger.error(f"Error collecting IAM evidence: {e}")
            raise AWSAPIException(f"Failed to collect IAM evidence: {e}")

        return evidence

    async def _collect_iam_policies(self, iam_client) -> List[EvidenceItem]:
        """Collect IAM policies"""
        evidence = []

        try:
            # Get custom policies only (exclude AWS managed policies for now)
            policies_paginator = iam_client.get_paginator("list_policies")

            for page in policies_paginator.paginate(Scope="Local"):
                for policy in page["Policies"]:
                    try:
                        # Get the policy document
                        policy_version = iam_client.get_policy_version(
                            PolicyArn=policy["Arn"], VersionId=policy["DefaultVersionId"]
                        )

                        # Get entities attached to this policy
                        entities = iam_client.list_entities_for_policy(PolicyArn=policy["Arn"])

                        evidence_item = self.create_evidence_item(
                            evidence_type="iam_policy",
                            resource_id=policy["Arn"],
                            resource_name=policy["PolicyName"],
                            data={
                                "policy_name": policy["PolicyName"],
                                "policy_id": policy["PolicyId"],
                                "arn": policy["Arn"],
                                "path": policy["Path"],
                                "policy_document": policy_version["PolicyVersion"]["Document"],
                                "default_version_id": policy["DefaultVersionId"],
                                "attachment_count": policy["AttachmentCount"],
                                "permissions_boundary_usage_count": policy.get(
                                    "PermissionsBoundaryUsageCount", 0
                                ),
                                "is_attachable": policy["IsAttachable"],
                                "description": policy.get("Description", ""),
                                "create_date": policy["CreateDate"].isoformat(),
                                "update_date": policy["UpdateDate"].isoformat(),
                                "attached_users": [
                                    user["UserName"] for user in entities.get("PolicyUsers", [])
                                ],
                                "attached_groups": [
                                    group["GroupName"] for group in entities.get("PolicyGroups", [])
                                ],
                                "attached_roles": [
                                    role["RoleName"] for role in entities.get("PolicyRoles", [])
                                ],
                            },
                            compliance_controls=[
                                "CC6.1",
                                "CC6.2",
                                "CC6.3",
                            ],  # SOC 2 Logical Access controls
                            quality_score=self._calculate_policy_quality_score(
                                policy, policy_version["PolicyVersion"]["Document"]
                            ),
                        )

                        evidence.append(evidence_item)

                    except ClientError as e:
                        self.logger.warning(
                            f"Failed to get details for policy {policy['PolicyName']}: {e}"
                        )
                        continue

        except ClientError as e:
            self.logger.error(f"Error collecting IAM policies: {e}")

        return evidence

    async def _collect_iam_users(self, iam_client) -> List[EvidenceItem]:
        """Collect IAM users"""
        evidence = []

        try:
            users_paginator = iam_client.get_paginator("list_users")

            for page in users_paginator.paginate():
                for user in page["Users"]:
                    try:
                        # Get user policies and groups
                        user_policies = iam_client.list_attached_user_policies(
                            UserName=user["UserName"]
                        )
                        user_groups = iam_client.get_groups_for_user(UserName=user["UserName"])

                        # Get access keys
                        access_keys = iam_client.list_access_keys(UserName=user["UserName"])

                        # Get MFA devices
                        mfa_devices = iam_client.list_mfa_devices(UserName=user["UserName"])

                        # Get login profile (console access)
                        has_console_access = False
                        try:
                            iam_client.get_login_profile(UserName=user["UserName"])
                            has_console_access = True
                        except ClientError:
                            pass  # No console access

                        evidence_item = self.create_evidence_item(
                            evidence_type="iam_user",
                            resource_id=user["Arn"],
                            resource_name=user["UserName"],
                            data={
                                "user_name": user["UserName"],
                                "user_id": user["UserId"],
                                "arn": user["Arn"],
                                "path": user["Path"],
                                "create_date": user["CreateDate"].isoformat(),
                                "password_last_used": user.get("PasswordLastUsed", "").isoformat()
                                if user.get("PasswordLastUsed")
                                else None,
                                "has_console_access": has_console_access,
                                "attached_policies": [
                                    policy["PolicyName"]
                                    for policy in user_policies["AttachedPolicies"]
                                ],
                                "groups": [group["GroupName"] for group in user_groups["Groups"]],
                                "access_keys": [
                                    {
                                        "access_key_id": key["AccessKeyId"],
                                        "status": key["Status"],
                                        "create_date": key["CreateDate"].isoformat(),
                                    }
                                    for key in access_keys["AccessKeyMetadata"]
                                ],
                                "mfa_devices": [
                                    {
                                        "serial_number": device["SerialNumber"],
                                        "enable_date": device["EnableDate"].isoformat(),
                                    }
                                    for device in mfa_devices["MFADevices"]
                                ],
                                "tags": user.get("Tags", []),
                            },
                            compliance_controls=[
                                "CC6.1",
                                "CC6.2",
                                "CC6.7",
                            ],  # SOC 2 user access controls
                            quality_score=self._calculate_user_quality_score(
                                user, mfa_devices["MFADevices"], access_keys["AccessKeyMetadata"]
                            ),
                        )

                        evidence.append(evidence_item)

                    except ClientError as e:
                        self.logger.warning(
                            f"Failed to get details for user {user['UserName']}: {e}"
                        )
                        continue

        except ClientError as e:
            self.logger.error(f"Error collecting IAM users: {e}")

        return evidence

    async def _collect_iam_roles(self, iam_client) -> List[EvidenceItem]:
        """Collect IAM roles"""
        evidence = []

        try:
            roles_paginator = iam_client.get_paginator("list_roles")

            for page in roles_paginator.paginate():
                for role in page["Roles"]:
                    try:
                        # Get role policies
                        role_policies = iam_client.list_attached_role_policies(
                            RoleName=role["RoleName"]
                        )

                        # Get inline policies
                        inline_policies = iam_client.list_role_policies(RoleName=role["RoleName"])

                        evidence_item = self.create_evidence_item(
                            evidence_type="iam_role",
                            resource_id=role["Arn"],
                            resource_name=role["RoleName"],
                            data={
                                "role_name": role["RoleName"],
                                "role_id": role["RoleId"],
                                "arn": role["Arn"],
                                "path": role["Path"],
                                "assume_role_policy_document": role["AssumeRolePolicyDocument"],
                                "description": role.get("Description", ""),
                                "max_session_duration": role.get("MaxSessionDuration", 3600),
                                "create_date": role["CreateDate"].isoformat(),
                                "last_used": role.get("RoleLastUsed", {})
                                .get("LastUsedDate", "")
                                .isoformat()
                                if role.get("RoleLastUsed", {}).get("LastUsedDate")
                                else None,
                                "last_used_region": role.get("RoleLastUsed", {}).get("Region"),
                                "attached_policies": [
                                    policy["PolicyName"]
                                    for policy in role_policies["AttachedPolicies"]
                                ],
                                "inline_policies": inline_policies["PolicyNames"],
                                "tags": role.get("Tags", []),
                            },
                            compliance_controls=[
                                "CC6.1",
                                "CC6.3",
                            ],  # SOC 2 role-based access controls
                            quality_score=self._calculate_role_quality_score(role),
                        )

                        evidence.append(evidence_item)

                    except ClientError as e:
                        self.logger.warning(
                            f"Failed to get details for role {role['RoleName']}: {e}"
                        )
                        continue

        except ClientError as e:
            self.logger.error(f"Error collecting IAM roles: {e}")

        return evidence

    def _calculate_policy_quality_score(self, policy: Dict, policy_document: Any) -> float:
        """Calculate quality score for IAM policy"""
        score = 1.0

        # Check if policy has description
        if not policy.get("Description"):
            score -= 0.1

        # Check if policy document follows least privilege
        if isinstance(policy_document, dict):
            statements = policy_document.get("Statement", [])
            if isinstance(statements, dict):
                statements = [statements]

            for statement in statements:
                # Check for overly broad permissions
                if statement.get("Effect") == "Allow":
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]

                    # Penalize wildcard actions
                    if "*" in actions:
                        score -= 0.3

                    # Check for overly broad resources
                    resources = statement.get("Resource", [])
                    if isinstance(resources, str):
                        resources = [resources]

                    if "*" in resources and "*" in actions:
                        score -= 0.4  # Very dangerous combination

        return max(0.0, score)

    def _calculate_user_quality_score(
        self, user: Dict, mfa_devices: List, access_keys: List
    ) -> float:
        """Calculate quality score for IAM user"""
        score = 1.0

        # Check if user has MFA enabled
        if not mfa_devices:
            score -= 0.3

        # Check for old access keys
        for key in access_keys:
            key_age = (datetime.utcnow() - key["CreateDate"].replace(tzinfo=None)).days
            if key_age > 90:  # Keys older than 90 days
                score -= 0.2

        # Check if user has used password recently (if they have console access)
        if user.get("PasswordLastUsed"):
            last_used = user["PasswordLastUsed"].replace(tzinfo=None)
            days_since_login = (datetime.utcnow() - last_used).days
            if days_since_login > 90:  # Inactive user
                score -= 0.2

        return max(0.0, score)

    def _calculate_role_quality_score(self, role: Dict) -> float:
        """Calculate quality score for IAM role"""
        score = 1.0

        # Check if role has description
        if not role.get("Description"):
            score -= 0.1

        # Check assume role policy for security
        assume_policy = role.get("AssumeRolePolicyDocument", {})
        if isinstance(assume_policy, dict):
            statements = assume_policy.get("Statement", [])
            if isinstance(statements, dict):
                statements = [statements]

            for statement in statements:
                principal = statement.get("Principal", {})
                if principal == "*" or (
                    isinstance(principal, dict) and principal.get("AWS") == "*"
                ):
                    score -= 0.5  # Very dangerous - allows any AWS account to assume

        return max(0.0, score)


class AWSCloudTrailCollector(BaseEvidenceCollector):
    """Collect CloudTrail audit logs for compliance evidence"""

    async def collect(
        self, start_time: datetime = None, event_types: List[str] = None, **kwargs
    ) -> List[EvidenceItem]:
        """Collect CloudTrail events for audit evidence"""
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)  # Last 7 days by default

        evidence = []

        try:
            cloudtrail = self.api_client.aws_session.client("cloudtrail")

            # Configure lookup attributes for event filtering
            lookup_attributes = []
            if event_types:
                for event_type in event_types:
                    lookup_attributes.append(
                        {"AttributeKey": "EventName", "AttributeValue": event_type}
                    )
            else:
                # Default to security-relevant events
                security_events = [
                    "CreateUser",
                    "DeleteUser",
                    "AttachUserPolicy",
                    "DetachUserPolicy",
                    "CreateRole",
                    "DeleteRole",
                    "AttachRolePolicy",
                    "DetachRolePolicy",
                    "CreateAccessKey",
                    "DeleteAccessKey",
                    "UpdateAccessKey",
                    "ConsoleLogin",
                    "AssumeRole",
                    "CreateLoginProfile",
                    "DeleteLoginProfile",
                ]

                for event in security_events:
                    lookup_attributes.append({"AttributeKey": "EventName", "AttributeValue": event})

            # Collect events (CloudTrail lookup_events has limitations, so we'll collect in batches)
            for lookup_attr in lookup_attributes[:5]:  # Limit to avoid API limits
                try:
                    response = cloudtrail.lookup_events(
                        LookupAttributes=[lookup_attr],
                        StartTime=start_time,
                        EndTime=datetime.utcnow(),
                        MaxItems=100,  # Limit per event type
                    )

                    for event in response["Events"]:
                        # Parse CloudTrail event
                        event_detail = json.loads(event.get("CloudTrailEvent", "{}"))

                        evidence_item = self.create_evidence_item(
                            evidence_type="audit_log",
                            resource_id=event["EventId"],
                            resource_name=event["EventName"],
                            data={
                                "event_id": event["EventId"],
                                "event_name": event["EventName"],
                                "event_time": event["EventTime"].isoformat(),
                                "username": event.get("Username"),
                                "user_identity": event_detail.get("userIdentity", {}),
                                "source_ip_address": event_detail.get("sourceIPAddress"),
                                "user_agent": event_detail.get("userAgent"),
                                "aws_region": event_detail.get("awsRegion"),
                                "event_source": event_detail.get("eventSource"),
                                "event_type": event_detail.get("eventType"),
                                "api_version": event_detail.get("apiVersion"),
                                "request_parameters": event_detail.get("requestParameters", {}),
                                "response_elements": event_detail.get("responseElements", {}),
                                "resources": event.get("Resources", []),
                                "error_code": event_detail.get("errorCode"),
                                "error_message": event_detail.get("errorMessage"),
                            },
                            compliance_controls=[
                                "CC6.1",
                                "CC7.2",
                                "CC7.3",
                            ],  # SOC 2 monitoring and logging
                            quality_score=self._calculate_log_quality_score(event_detail),
                        )

                        evidence.append(evidence_item)

                except ClientError as e:
                    self.logger.warning(
                        f"Failed to collect events for {lookup_attr['AttributeValue']}: {e}"
                    )
                    continue

        except ClientError as e:
            self.logger.error(f"Error collecting CloudTrail evidence: {e}")
            raise AWSAPIException(f"Failed to collect CloudTrail evidence: {e}")

        return evidence

    def _calculate_log_quality_score(self, event_detail: Dict) -> float:
        """Calculate quality score for audit log entry"""
        score = 1.0

        # Check if essential fields are present
        required_fields = ["userIdentity", "sourceIPAddress", "eventTime", "eventSource"]
        missing_fields = [field for field in required_fields if not event_detail.get(field)]

        if missing_fields:
            score -= 0.2 * len(missing_fields)

        # Check if it's an error event
        if event_detail.get("errorCode"):
            score += 0.1  # Error events are more valuable for security monitoring

        return max(0.0, score)


class AWSSecurityGroupCollector(BaseEvidenceCollector):
    """Collect Security Group configurations for network security evidence"""

    async def collect(self, **kwargs) -> List[EvidenceItem]:
        """Collect security group configurations"""
        evidence = []

        try:
            ec2 = self.api_client.aws_session.client("ec2")

            # Get all security groups
            response = ec2.describe_security_groups()

            for sg in response["SecurityGroups"]:
                evidence_item = self.create_evidence_item(
                    evidence_type="security_group",
                    resource_id=sg["GroupId"],
                    resource_name=sg["GroupName"],
                    data={
                        "group_id": sg["GroupId"],
                        "group_name": sg["GroupName"],
                        "description": sg["Description"],
                        "vpc_id": sg.get("VpcId"),
                        "owner_id": sg["OwnerId"],
                        "inbound_rules": [
                            {
                                "ip_protocol": rule.get("IpProtocol"),
                                "from_port": rule.get("FromPort"),
                                "to_port": rule.get("ToPort"),
                                "ip_ranges": rule.get("IpRanges", []),
                                "ipv6_ranges": rule.get("Ipv6Ranges", []),
                                "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                                "prefix_list_ids": rule.get("PrefixListIds", []),
                            }
                            for rule in sg.get("IpPermissions", [])
                        ],
                        "outbound_rules": [
                            {
                                "ip_protocol": rule.get("IpProtocol"),
                                "from_port": rule.get("FromPort"),
                                "to_port": rule.get("ToPort"),
                                "ip_ranges": rule.get("IpRanges", []),
                                "ipv6_ranges": rule.get("Ipv6Ranges", []),
                                "user_id_group_pairs": rule.get("UserIdGroupPairs", []),
                                "prefix_list_ids": rule.get("PrefixListIds", []),
                            }
                            for rule in sg.get("IpPermissionsEgress", [])
                        ],
                        "tags": sg.get("Tags", []),
                    },
                    compliance_controls=["CC6.1", "CC6.6"],  # SOC 2 network security controls
                    quality_score=self._calculate_security_group_quality_score(sg),
                )

                evidence.append(evidence_item)

        except ClientError as e:
            self.logger.error(f"Error collecting security group evidence: {e}")
            raise AWSAPIException(f"Failed to collect security group evidence: {e}")

        return evidence

    def _calculate_security_group_quality_score(self, sg: Dict) -> float:
        """Calculate quality score for security group"""
        score = 1.0

        # Check for overly permissive rules
        for rule in sg.get("IpPermissions", []):
            for ip_range in rule.get("IpRanges", []):
                if ip_range.get("CidrIp") == "0.0.0.0/0":
                    # Penalize rules open to the internet
                    if rule.get("FromPort") == 22 or rule.get("FromPort") == 3389:  # SSH or RDP
                        score -= 0.5  # Very dangerous
                    else:
                        score -= 0.2  # Moderately dangerous

        # Check if security group has description
        if not sg.get("Description") or sg["Description"] == sg["GroupName"]:
            score -= 0.1

        return max(0.0, score)


# Additional collectors can be implemented similarly
class AWSVPCCollector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for VPC configuration collection
        return []


class AWSConfigCollector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for AWS Config rules collection
        return []


class AWSGuardDutyCollector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for GuardDuty findings collection
        return []


class AWSInspectorCollector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for Inspector findings collection
        return []


class AWSComplianceCollector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for compliance reports collection
        return []


class AWSS3Collector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for S3 bucket security collection
        return []


class AWSEC2Collector(BaseEvidenceCollector):
    async def collect(self, **kwargs) -> List[EvidenceItem]:
        # Implementation for EC2 instance collection
        return []
