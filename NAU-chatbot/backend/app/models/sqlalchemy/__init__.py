"""Public SQLAlchemy persistence model surface."""

from app.models.sqlalchemy.academic import (
    Accreditation,
    Formation,
    FormationElement,
    Parcours,
    RegleOrientation,
    Specialisation,
    Tarif,
)
from app.models.sqlalchemy.base import Base, TimestampMixin
from app.models.sqlalchemy.identity import Conversation, ConversationMessage, UserAccount

__all__ = [
    "Accreditation",
    "Base",
    "Formation",
    "FormationElement",
    "Conversation",
    "ConversationMessage",
    "Parcours",
    "RegleOrientation",
    "Specialisation",
    "Tarif",
    "TimestampMixin",
    "UserAccount",
]
