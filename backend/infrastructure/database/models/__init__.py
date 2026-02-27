"""
SQLAlchemy database models.
"""

from .base import Base, TimestampMixin
from .user import User, UserRole, UserStatus, SubscriptionTier
from .content import Outline, Article, ArticleRevision, GeneratedImage, ContentStatus, ContentTone
from .analytics import GSCConnection, KeywordRanking, PagePerformance, DailyAnalytics, ContentDecayAlert
from .knowledge import KnowledgeSource, KnowledgeChunk, KnowledgeQuery, SourceStatus
from .social import (
    SocialAccount,
    ScheduledPost,
    PostTarget,
    Platform,
    PostStatus,
)
from .admin import AdminAuditLog, AuditAction, AuditTargetType
from .project import Project, ProjectMember, ProjectInvitation, ProjectMemberRole, InvitationStatus
from .generation import GenerationLog, AdminAlert
from .aeo import AEOScore, AEOCitation
from .bulk import ContentTemplate, BulkJob, BulkJobItem
from .revenue import ConversionGoal, ContentConversion, RevenueReport
from .agency import AgencyProfile, ClientWorkspace, ReportTemplate, GeneratedReport
from .keyword_cache import KeywordResearchCache

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "UserStatus",
    "SubscriptionTier",
    "Outline",
    "Article",
    "ArticleRevision",
    "GeneratedImage",
    "ContentStatus",
    "ContentTone",
    "GSCConnection",
    "KeywordRanking",
    "PagePerformance",
    "DailyAnalytics",
    "ContentDecayAlert",
    "KnowledgeSource",
    "KnowledgeChunk",
    "KnowledgeQuery",
    "SourceStatus",
    "SocialAccount",
    "ScheduledPost",
    "PostTarget",
    "Platform",
    "PostStatus",
    "AdminAuditLog",
    "AuditAction",
    "AuditTargetType",
    "Project",
    "ProjectMember",
    "ProjectInvitation",
    "ProjectMemberRole",
    "InvitationStatus",
    "GenerationLog",
    "AdminAlert",
    "AEOScore",
    "AEOCitation",
    "ContentTemplate",
    "BulkJob",
    "BulkJobItem",
    "ConversionGoal",
    "ContentConversion",
    "RevenueReport",
    "AgencyProfile",
    "ClientWorkspace",
    "ReportTemplate",
    "GeneratedReport",
    "KeywordResearchCache",
]
