"""
Dice Roll Database Models
Separate SQLite database for dice roll functionality
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from datetime import datetime
import os

Base = declarative_base()

class DiceRoll(Base):
    """Records individual dice roll requests and results"""
    __tablename__ = 'dice_rolls'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)  # Links to auth database user
    username = Column(String(100), nullable=True)  # Cached username

    # Roll details
    expression = Column(String(500), nullable=False)  # e.g., "3d6+2"
    description = Column(Text, nullable=True)  # Optional description

    # Results
    raw_rolls = Column(JSON, nullable=False)  # Individual dice results
    modifiers = Column(JSON, nullable=True)  # Applied modifiers
    total = Column(Integer, nullable=False)  # Final result

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50), default='api')  # api, web, plugin
    campaign_id = Column(String(100), nullable=True)  # Optional campaign context
    session_id = Column(String(100), nullable=True)  # Optional session context

    # Special flags
    is_critical = Column(Boolean, default=False)  # Natural 20 on d20
    is_fumble = Column(Boolean, default=False)  # Natural 1 on d20
    advantage = Column(Boolean, default=False)  # Roll with advantage
    disadvantage = Column(Boolean, default=False)  # Roll with disadvantage

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'expression': self.expression,
            'description': self.description,
            'raw_rolls': self.raw_rolls,
            'modifiers': self.modifiers,
            'total': self.total,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'source': self.source,
            'campaign_id': self.campaign_id,
            'session_id': self.session_id,
            'is_critical': self.is_critical,
            'is_fumble': self.is_fumble,
            'advantage': self.advantage,
            'disadvantage': self.disadvantage
        }

class RollTemplate(Base):
    """Saved roll templates for quick access"""
    __tablename__ = 'roll_templates'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    name = Column(String(100), nullable=False)
    expression = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # attack, save, skill, etc.
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'expression': self.expression,
            'description': self.description,
            'category': self.category,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class RollStatistics(Base):
    """Aggregated statistics for users"""
    __tablename__ = 'roll_statistics'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)

    # Counters
    total_rolls = Column(Integer, default=0)
    total_d20_rolls = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    fumble_count = Column(Integer, default=0)

    # Averages
    average_roll = Column(Float, default=0.0)
    highest_roll = Column(Integer, default=0)
    lowest_roll = Column(Integer, default=0)

    # Dice type distribution
    dice_distribution = Column(JSON, default=dict)  # {"d6": 100, "d20": 50, ...}

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'total_rolls': self.total_rolls,
            'total_d20_rolls': self.total_d20_rolls,
            'critical_count': self.critical_count,
            'fumble_count': self.fumble_count,
            'average_roll': self.average_roll,
            'highest_roll': self.highest_roll,
            'lowest_roll': self.lowest_roll,
            'dice_distribution': self.dice_distribution,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

# Database setup
def init_dice_db(db_path='dice_rolls.db'):
    """Initialize the dice roll database"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine

def get_dice_session(engine=None):
    """Get a database session for dice rolls"""
    if engine is None:
        engine = init_dice_db()
    Session = sessionmaker(bind=engine)
    return Session()