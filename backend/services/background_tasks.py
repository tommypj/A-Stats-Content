"""
Background task handlers for asynchronous processing.

Simple synchronous processing for now. Can be upgraded to Celery/Redis queue later.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_session
from services import get_knowledge_service

logger = logging.getLogger(__name__)


async def process_document_task(
    source_id: str,
    user_id: str,
    file_path: str,
) -> bool:
    """
    Background task to process a document.

    This function is called asynchronously to process uploaded documents.
    It extracts text, generates chunks, creates embeddings, and stores
    them in ChromaDB.

    Args:
        source_id: ID of the KnowledgeSource record
        user_id: User ID (for collection isolation)
        file_path: Path to the uploaded file

    Returns:
        True if processing succeeded, False otherwise
    """
    logger.info(
        f"Starting background document processing: "
        f"source_id={source_id}, user_id={user_id}, file_path={file_path}"
    )

    db: Optional[AsyncSession] = None

    try:
        # Get database session
        async for session in get_session():
            db = session
            break

        if not db:
            logger.error("Failed to get database session")
            return False

        # Get knowledge service
        knowledge_service = get_knowledge_service()

        # Process the document
        success = await knowledge_service.process_document(
            source_id=source_id,
            user_id=user_id,
            file_path=file_path,
            db=db,
        )

        if success:
            logger.info(f"Successfully processed document {source_id}")
        else:
            logger.error(f"Failed to process document {source_id}")

        return success

    except Exception as e:
        logger.error(
            f"Exception in background document processing for {source_id}: {e}",
            exc_info=True,
        )
        return False

    finally:
        # Close database session
        if db:
            await db.close()


# Future: Add Celery/Redis integration for true background processing
# For now, these tasks run in the same process but can be called
# with asyncio.create_task() to run "in the background"

# Example Celery integration (commented out):
# from celery import Celery
# celery_app = Celery('tasks', broker='redis://localhost:6379/0')
#
# @celery_app.task
# def process_document_celery(source_id: str, user_id: str, file_path: str):
#     """Celery task wrapper."""
#     import asyncio
#     return asyncio.run(process_document_task(source_id, user_id, file_path))
