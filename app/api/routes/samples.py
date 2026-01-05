from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.api.routes.common import DataRow
from app.models import Comment, User, UserCommentRevision

router = APIRouter(prefix="/samples", tags=["/samples"])
from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)


class SampleResponse(BaseModel):
    sample: DataRow


@router.get("/samples/{sample_id}", response_model=SampleResponse)
async def get_sample(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    sample_id: str,
) -> Any:
    """
    Fetch a single sample by ID with revision status for the current user.
    """
    # Query to fetch the comment and join with revision info for the current user
    statement = (
        select(
            Comment,
            UserCommentRevision.expert_opinion,
            UserCommentRevision.created_at.label("revision_timestamp"),
            User.full_name.label("reviser_name"),
        )
        .where(Comment.id == sample_id)
        .outerjoin(
            UserCommentRevision,
            (UserCommentRevision.comment_id == Comment.id)
            & (UserCommentRevision.user_id == current_user.id),
        )
        .outerjoin(User, User.id == UserCommentRevision.user_id)
    )

    result = session.exec(statement).first()

    if not result:
        raise HTTPException(status_code=404, detail="Sample not found")

    comment, expert_opinion, revision_timestamp, reviser_name = result

    # Map the result to the DataRow schema
    data_row = DataRow(
        id=comment.id,
        preceding=comment.preceding,
        target=comment.target,
        following=comment.following,
        A1_Score=comment.A1_Score,
        A2_Score=comment.A2_Score,
        A3_Score=comment.A3_Score,
        principle_id=comment.principle_id,
        llm_justification=comment.llm_justification,
        llm_evidence_quote=comment.llm_evidence_quote,
        expert_opinion=expert_opinion,
        # Determine revision status based on existence of expert opinion
        is_revised=expert_opinion is not None,
        reviser_name=reviser_name,
        revision_timestamp=revision_timestamp,
    )

    return SampleResponse(sample=data_row)
