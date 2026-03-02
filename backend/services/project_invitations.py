"""
Project invitation background service.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import InvitationStatus, ProjectInvitation

logger = logging.getLogger(__name__)


async def expire_old_invitations(db: AsyncSession) -> int:
    """
    Mark expired project invitations as EXPIRED.

    This function should be called periodically (e.g., via cron job or scheduler)
    to update invitation statuses.

    Args:
        db: Database session

    Returns:
        Number of invitations marked as expired
    """
    # Find pending invitations that have passed their expiration date
    result = await db.execute(
        select(ProjectInvitation).where(
            ProjectInvitation.status == InvitationStatus.PENDING.value,
            ProjectInvitation.expires_at < datetime.now(UTC),
        )
    )
    expired_invitations = result.scalars().all()

    # Update status to EXPIRED
    expired_count = 0
    for invitation in expired_invitations:
        invitation.status = InvitationStatus.EXPIRED.value
        expired_count += 1

    if expired_count > 0:
        await db.commit()
        logger.info(f"Marked {expired_count} project invitations as expired")

    return expired_count


async def cleanup_old_invitations(db: AsyncSession, days_old: int = 30) -> int:
    """
    Delete old accepted/revoked/expired invitations.

    This is optional cleanup to keep the database tidy.
    Only deletes invitations that were accepted/revoked/expired more than N days ago.

    Args:
        db: Database session
        days_old: Delete invitations older than this many days (default: 30)

    Returns:
        Number of invitations deleted
    """
    from datetime import timedelta

    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

    # Find old non-pending invitations
    result = await db.execute(
        select(ProjectInvitation).where(
            ProjectInvitation.status.in_(
                [
                    InvitationStatus.ACCEPTED.value,
                    InvitationStatus.REVOKED.value,
                    InvitationStatus.EXPIRED.value,
                ]
            ),
            ProjectInvitation.updated_at < cutoff_date,
        )
    )
    old_invitations = result.scalars().all()

    # Delete old invitations
    deleted_count = 0
    for invitation in old_invitations:
        await db.delete(invitation)
        deleted_count += 1

    if deleted_count > 0:
        await db.commit()
        logger.info(f"Deleted {deleted_count} old project invitations")

    return deleted_count
