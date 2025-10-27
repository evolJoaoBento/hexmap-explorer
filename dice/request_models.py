"""
Dice Request and Chat System Models
Extends the dice system with request/response flow and chat functionality
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

from .models import Base, get_dice_session, init_dice_db

class RequestStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class MessageType(enum.Enum):
    TEXT = "text"
    DICE_REQUEST = "dice_request"
    DICE_RESPONSE = "dice_response"
    SYSTEM = "system"

class DiceRequest(Base):
    """Dice roll requests from DM to players"""
    __tablename__ = 'dice_requests'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Request details
    expression = Column(String(500), nullable=False)  # e.g., "3d6+2"
    description = Column(Text, nullable=True)         # "Make an attack roll"
    reason = Column(Text, nullable=True)              # "You're attacking the orc"

    # Participants
    requester_id = Column(Integer, nullable=False)    # DM user ID
    requester_username = Column(String(100))          # Cached DM username
    target_id = Column(Integer, nullable=False)       # Player user ID
    target_username = Column(String(100))             # Cached player username

    # Context
    campaign_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)
    room_id = Column(String(36), nullable=True)       # Chat room

    # Status
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    priority = Column(String(20), default="normal")   # low, normal, high, urgent

    # Options
    allow_advantage = Column(Boolean, default=True)
    allow_disadvantage = Column(Boolean, default=True)
    require_reason = Column(Boolean, default=False)   # Player must explain their roll
    auto_submit = Column(Boolean, default=False)      # Auto-submit roll without confirmation

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)      # Optional expiration
    responded_at = Column(DateTime, nullable=True)

    # Response (when completed)
    roll_id = Column(Integer, ForeignKey('dice_rolls.id'), nullable=True)  # Links to actual roll
    response_total = Column(Integer, nullable=True)   # Cached total for quick access
    response_breakdown = Column(Text, nullable=True)  # Cached breakdown
    player_comment = Column(Text, nullable=True)      # Player's comment on the roll

    # Extra data
    extra_data = Column(JSON, default=dict)           # Extra data (modifiers, conditions, etc.)

    def to_dict(self):
        return {
            'id': self.id,
            'expression': self.expression,
            'description': self.description,
            'reason': self.reason,
            'requester_id': self.requester_id,
            'requester_username': self.requester_username,
            'target_id': self.target_id,
            'target_username': self.target_username,
            'campaign_id': self.campaign_id,
            'session_id': self.session_id,
            'room_id': self.room_id,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'allow_advantage': self.allow_advantage,
            'allow_disadvantage': self.allow_disadvantage,
            'require_reason': self.require_reason,
            'auto_submit': self.auto_submit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'roll_id': self.roll_id,
            'response_total': self.response_total,
            'response_breakdown': self.response_breakdown,
            'player_comment': self.player_comment,
            'extra_data': self.extra_data
        }

class ChatRoom(Base):
    """Chat rooms for grouping users"""
    __tablename__ = 'chat_rooms'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Room settings
    room_type = Column(String(50), default="campaign")  # campaign, session, private, public
    is_public = Column(Boolean, default=False)
    max_members = Column(Integer, default=50)

    # Context
    campaign_id = Column(String(100), nullable=True)
    session_id = Column(String(100), nullable=True)

    # Ownership
    created_by = Column(Integer, nullable=False)        # User ID of creator
    created_at = Column(DateTime, default=datetime.utcnow)

    # Settings
    allow_dice_requests = Column(Boolean, default=True)
    allow_public_rolls = Column(Boolean, default=True)
    dice_request_timeout = Column(Integer, default=300)  # 5 minutes default

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'room_type': self.room_type,
            'is_public': self.is_public,
            'max_members': self.max_members,
            'campaign_id': self.campaign_id,
            'session_id': self.session_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'allow_dice_requests': self.allow_dice_requests,
            'allow_public_rolls': self.allow_public_rolls,
            'dice_request_timeout': self.dice_request_timeout
        }

class RoomMember(Base):
    """Room membership tracking"""
    __tablename__ = 'room_members'

    id = Column(Integer, primary_key=True)
    room_id = Column(String(36), ForeignKey('chat_rooms.id'), nullable=False)
    user_id = Column(Integer, nullable=False)
    username = Column(String(100))  # Cached

    # Role and permissions
    role = Column(String(50), default="player")        # dm, player, observer
    can_request_rolls = Column(Boolean, default=False) # Can request dice rolls
    can_see_all_rolls = Column(Boolean, default=True)  # Can see everyone's rolls
    is_active = Column(Boolean, default=True)

    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'username': self.username,
            'role': self.role,
            'can_request_rolls': self.can_request_rolls,
            'can_see_all_rolls': self.can_see_all_rolls,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

class ChatMessage(Base):
    """Chat messages including dice requests and responses"""
    __tablename__ = 'chat_messages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(36), ForeignKey('chat_rooms.id'), nullable=False)

    # Message details
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    content = Column(Text, nullable=False)

    # Sender
    sender_id = Column(Integer, nullable=True)         # Null for system messages
    sender_username = Column(String(100))
    sender_role = Column(String(50))                   # dm, player, system

    # References
    dice_request_id = Column(String(36), ForeignKey('dice_requests.id'), nullable=True)
    roll_id = Column(Integer, ForeignKey('dice_rolls.id'), nullable=True)
    reply_to_id = Column(String(36), ForeignKey('chat_messages.id'), nullable=True)

    # Targeting (for dice requests)
    target_user_id = Column(Integer, nullable=True)   # Who this message is for
    target_username = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime, nullable=True)

    # Message metadata
    is_whisper = Column(Boolean, default=False)       # Only visible to target and sender
    is_system = Column(Boolean, default=False)
    message_data = Column(JSON, default=dict)         # Extra data

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'message_type': self.message_type.value if self.message_type else None,
            'content': self.content,
            'sender_id': self.sender_id,
            'sender_username': self.sender_username,
            'sender_role': self.sender_role,
            'dice_request_id': self.dice_request_id,
            'roll_id': self.roll_id,
            'reply_to_id': self.reply_to_id,
            'target_user_id': self.target_user_id,
            'target_username': self.target_username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'is_whisper': self.is_whisper,
            'is_system': self.is_system,
            'message_data': self.message_data
        }

class DiceRequestTemplate(Base):
    """Templates for commonly requested dice rolls"""
    __tablename__ = 'dice_request_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    expression = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    reason_template = Column(Text, nullable=True)      # "Make a {skill} check"

    # Settings
    allow_advantage = Column(Boolean, default=True)
    allow_disadvantage = Column(Boolean, default=True)
    priority = Column(String(20), default="normal")

    # Ownership
    created_by = Column(Integer, nullable=False)
    is_public = Column(Boolean, default=False)
    category = Column(String(50), nullable=True)       # attack, save, skill, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'expression': self.expression,
            'description': self.description,
            'reason_template': self.reason_template,
            'allow_advantage': self.allow_advantage,
            'allow_disadvantage': self.allow_disadvantage,
            'priority': self.priority,
            'created_by': self.created_by,
            'is_public': self.is_public,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Helper functions

def get_user_requests(user_id, status=None, limit=50):
    """Get dice requests for a user"""
    session = get_dice_session()
    try:
        query = session.query(DiceRequest).filter(
            (DiceRequest.requester_id == user_id) |
            (DiceRequest.target_id == user_id)
        )

        if status:
            if isinstance(status, str):
                status = RequestStatus(status)
            query = query.filter(DiceRequest.status == status)

        return query.order_by(DiceRequest.created_at.desc()).limit(limit).all()
    finally:
        session.close()

def get_room_messages(room_id, limit=100, before_id=None):
    """Get messages for a room"""
    session = get_dice_session()
    try:
        query = session.query(ChatMessage).filter(ChatMessage.room_id == room_id)

        if before_id:
            query = query.filter(ChatMessage.created_at <
                session.query(ChatMessage.created_at).filter(
                    ChatMessage.id == before_id
                ).scalar()
            )

        return query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    finally:
        session.close()

def create_system_message(room_id, content, message_data=None):
    """Create a system message"""
    session = get_dice_session()
    try:
        message = ChatMessage(
            room_id=room_id,
            message_type=MessageType.SYSTEM,
            content=content,
            sender_username="System",
            sender_role="system",
            is_system=True,
            message_data=message_data or {}
        )
        session.add(message)
        session.commit()
        return message
    finally:
        session.close()

def cleanup_expired_requests():
    """Clean up expired dice requests"""
    session = get_dice_session()
    try:
        expired_requests = session.query(DiceRequest).filter(
            DiceRequest.expires_at < datetime.utcnow(),
            DiceRequest.status == RequestStatus.PENDING
        ).all()

        for request in expired_requests:
            request.status = RequestStatus.EXPIRED

            # Create system message about expiration
            if request.room_id:
                create_system_message(
                    request.room_id,
                    f"Dice request '{request.description}' for {request.target_username} has expired.",
                    {'expired_request_id': request.id}
                )

        session.commit()
        return len(expired_requests)
    finally:
        session.close()

# Initialize request database tables
def init_request_db():
    """Initialize dice request database tables"""
    engine = init_dice_db()  # This also creates the dice tables
    Base.metadata.create_all(engine)
    return engine