"""
Dice Roll System Package
Provides dice rolling functionality for tabletop RPG applications
"""

from .engine import DiceRollEngine, RollResult
from .models import DiceRoll, RollTemplate, RollStatistics, init_dice_db, get_dice_session
from .routes import dice_api
from .request_routes import dice_request_api
from .request_models import (
    DiceRequest, ChatMessage, ChatRoom, RoomMember, DiceRequestTemplate,
    RequestStatus, MessageType, init_request_db
)

__version__ = "1.0.0"
__all__ = [
    "DiceRollEngine",
    "RollResult",
    "DiceRoll",
    "RollTemplate",
    "RollStatistics",
    "init_dice_db",
    "get_dice_session",
    "dice_api",
    "dice_request_api",
    "DiceRequest",
    "ChatMessage",
    "ChatRoom",
    "RoomMember",
    "DiceRequestTemplate",
    "RequestStatus",
    "MessageType",
    "init_request_db"
]