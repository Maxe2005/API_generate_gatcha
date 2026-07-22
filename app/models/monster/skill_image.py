"""
Module: models.monster.skill_image

Description:
Modèle SQLAlchemy pour les cartes de compétence (images générées par IA
illustrant une compétence, en conservant l'identité visuelle du monstre).

Chaque carte de compétence est rattachée explicitement à l'image de monstre
(`MonsterImage`) qui a servi de référence pour la produire via
`source_monster_image_id` : un monstre pouvant avoir plusieurs images, une
compétence peut donc avoir plusieurs cartes, groupées par image source.
`is_default` est scopé au sein de ce groupe (skill_id, source_monster_image_id),
pas au niveau de la compétence entière.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class SkillImage(Base):
    """
    Table pour stocker les cartes de compétence générées par IA.
    Rattachée à Skill (compétence) et à MonsterImage (image de monstre source).
    """

    __tablename__ = "skill_images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Image de monstre utilisée comme référence visuelle pour produire cette
    # carte. Détermine le "groupe" auquel appartient la carte : si l'image
    # par défaut du monstre change, un nouveau groupe de cartes doit être
    # généré pour rester visuellement cohérent.
    source_monster_image_id = Column(
        Integer,
        ForeignKey("monster_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    image_url = Column(String, nullable=False)
    raw_image_key = Column(String, nullable=True)
    prompt = Column(Text, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=True)

    # Image par défaut au sein du groupe (skill_id, source_monster_image_id)
    is_default = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    skill = relationship("Skill", back_populates="images")
    source_monster_image = relationship("MonsterImage")
