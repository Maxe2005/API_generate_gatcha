"""
Module: monster_image_model

Description:
Modèle SQLAlchemy pour gérer plusieurs images par monstre.
Lié à Monster car les images sont associées aux monstres structurés.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class MonsterImage(Base):
    """
    Table pour stocker plusieurs images par monstre.
    Permet de gérer différentes variations visuelles pour un même monstre.
    Lié à Monster (table structurée des monstres validés).
    """

    __tablename__ = "monster_images"

    # Identifiant unique de l'image
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Référence au monstre (via monsters)
    monster_id = Column(
        Integer,
        ForeignKey("monsters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Informations de l'image
    image_name = Column(String, nullable=False)  # Nom de l'image (sans extension)
    image_url = Column(String, nullable=False)  # URL MinIO complète
    raw_image_key = Column(
        String, nullable=True
    )  # Clé d'objet de l'image 4K brute (usage interne uniquement)
    prompt = Column(Text, nullable=False)  # Prompt utilisé pour générer l'image

    # Image par défaut
    is_default = Column(Boolean, default=False, nullable=False)

    # Métadonnées
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relations
    monster = relationship("Monster", back_populates="images")
