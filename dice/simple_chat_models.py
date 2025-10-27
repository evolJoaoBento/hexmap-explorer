"""
Simple Chat System Models
Simplified chat table for regular messages, separate from dice requests
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from .models import Base, get_dice_session, init_dice_db

class SimpleChatMessage(Base):
    """Simple chat messages separate from dice system"""
    __tablename__ = 'simple_chat_messages'

    id = Column(Integer, primary_key=True)
    room_id = Column(String(100), nullable=False)  # Room identifier

    # Message content
    content = Column(Text, nullable=False)

    # Sender info
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=False)
    user_role = Column(String(50), default='player')  # dm, player

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_system_message = Column(Boolean, default=False)
    extra_data = Column(JSON, default=dict)

    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'content': self.content,
            'user_id': self.user_id,
            'username': self.username,
            'user_role': self.user_role,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_system_message': self.is_system_message,
            'extra_data': self.extra_data,
            'message_type': 'chat'  # For frontend compatibility
        }

def add_chat_message(room_id, content, user_id=None, username="Anonymous", user_role="player", is_system=False):
    """Add a simple chat message"""
    try:
        # Initialize DB first
        engine = init_simple_chat_db()
        session = get_dice_session(engine)

        message = SimpleChatMessage(
            room_id=room_id,
            content=content,
            user_id=user_id,
            username=username,
            user_role=user_role,
            is_system_message=is_system
        )
        session.add(message)
        session.commit()

        # Convert to dict before closing session
        message_dict = message.to_dict()
        session.close()
        return message_dict
    except Exception as e:
        print(f"Error adding chat message: {e}")
        if 'session' in locals():
            session.close()
        raise e

def get_chat_messages(room_id, limit=50, offset=0):
    """Get chat messages for a room"""
    try:
        # Initialize DB first
        engine = init_simple_chat_db()
        session = get_dice_session(engine)

        messages = session.query(SimpleChatMessage).filter(
            SimpleChatMessage.room_id == room_id
        ).order_by(SimpleChatMessage.timestamp.desc()).limit(limit).offset(offset).all()

        return list(reversed(messages))  # Return in chronological order
    finally:
        if 'session' in locals():
            session.close()

def init_simple_chat_db():
    """Initialize simple chat database"""
    engine = init_dice_db()
    Base.metadata.create_all(engine)
    return engine