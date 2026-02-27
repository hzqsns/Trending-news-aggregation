from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.skill import Skill

router = APIRouter()


class SkillCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    skill_type: str
    config: dict
    is_enabled: bool = True


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    is_enabled: bool | None = None


@router.get("/")
async def list_skills(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Skill).order_by(Skill.id))
    return [s.to_dict() for s in result.scalars().all()]


@router.post("/")
async def create_skill(
    body: SkillCreate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    skill = Skill(
        name=body.name,
        slug=body.slug,
        description=body.description,
        skill_type=body.skill_type,
        config=body.config,
        is_enabled=body.is_enabled,
    )
    session.add(skill)
    await session.commit()
    await session.refresh(skill)
    return skill.to_dict()


@router.get("/{skill_id}")
async def get_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        return {"error": "Skill not found"}
    return skill.to_dict()


@router.put("/{skill_id}")
async def update_skill(
    skill_id: int,
    body: SkillUpdate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        return {"error": "Skill not found"}

    if skill.is_builtin:
        if body.is_enabled is not None:
            skill.is_enabled = body.is_enabled
        else:
            return {"error": "Cannot modify builtin skills (only is_enabled can be toggled)"}
    else:
        if body.name is not None:
            skill.name = body.name
        if body.description is not None:
            skill.description = body.description
        if body.config is not None:
            skill.config = body.config
        if body.is_enabled is not None:
            skill.is_enabled = body.is_enabled
    skill.updated_at = datetime.utcnow()
    await session.commit()
    return skill.to_dict()


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        return {"error": "Skill not found"}
    if skill.is_builtin:
        return {"error": "Cannot delete builtin skills"}
    await session.delete(skill)
    await session.commit()
    return {"ok": True}
