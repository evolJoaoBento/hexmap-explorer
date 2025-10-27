"""
Secure session management for Hex Explorer
"""
import uuid
import time
from typing import Optional, Dict, Any
from flask import current_app
from flask_login import current_user
from models import db, GameSession

class SecureSessionManager:
    """Manages game sessions with proper authorization and persistence"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Any] = {}
    
    def create_session(self, session_name: str, session_type: str = 'game') -> str:
        """Create a new secure session"""
        if not current_user.is_authenticated:
            raise ValueError("User must be authenticated to create session")
        
        # Generate cryptographically secure session ID
        session_id = f"{session_type}_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Create database record
        db_session = GameSession(
            session_id=session_id,
            name=session_name,
            owner_id=current_user.id,
            players={str(current_user.id): {
                'name': current_user.username,
                'color': current_user.color,
                'role': current_user.role
            }}
        )
        
        try:
            db.session.add(db_session)
            db.session.commit()
            
            # Store in active sessions
            self.active_sessions[session_id] = {
                'owner_id': current_user.id,
                'created_at': time.time(),
                'last_accessed': time.time(),
                'session_type': session_type
            }
            
            current_app.logger.info(f"Created session {session_id} for user {current_user.id}")
            return session_id
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get session if user has access"""
        if not current_user.is_authenticated:
            return None
        
        # Get from database
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return None
        
        # Check authorization
        if not self.has_access(session_id, current_user.id):
            current_app.logger.warning(f"User {current_user.id} attempted unauthorized access to session {session_id}")
            return None
        
        # Update last accessed time
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['last_accessed'] = time.time()
        
        return session
    
    def has_access(self, session_id: str, user_id: int) -> bool:
        """Check if user has access to session"""
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return False
        
        # Owner has full access
        if session.owner_id == user_id:
            return True
        
        # Check if user is in players list
        players = session.players or {}
        return str(user_id) in players
    
    def is_owner(self, session_id: str, user_id: int) -> bool:
        """Check if user owns the session"""
        session = GameSession.query.filter_by(session_id=session_id).first()
        return session and session.owner_id == user_id
    
    def add_player(self, session_id: str, user_id: int, player_data: Dict[str, Any]) -> bool:
        """Add player to session (owner only)"""
        if not self.is_owner(session_id, current_user.id):
            return False
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return False
        
        players = session.players or {}
        players[str(user_id)] = player_data
        session.players = players
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to add player to session {session_id}: {e}")
            return False
    
    def remove_player(self, session_id: str, user_id: int) -> bool:
        """Remove player from session (owner only)"""
        if not self.is_owner(session_id, current_user.id):
            return False
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return False
        
        players = session.players or {}
        if str(user_id) in players:
            del players[str(user_id)]
            session.players = players
            
            try:
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to remove player from session {session_id}: {e}")
                return False
        
        return True
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session (owner only)"""
        if not self.is_owner(session_id, current_user.id):
            return False
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return False
        
        # Only allow specific fields to be updated
        allowed_fields = ['name', 'map_data', 'settings']
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(session, field, value)
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session (owner only)"""
        if not self.is_owner(session_id, current_user.id):
            return False
        
        session = GameSession.query.filter_by(session_id=session_id).first()
        if not session:
            return True  # Already deleted
        
        try:
            db.session.delete(session)
            db.session.commit()
            
            # Remove from active sessions
            self.active_sessions.pop(session_id, None)
            
            current_app.logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def list_user_sessions(self, user_id: int) -> list:
        """List sessions accessible to user"""
        sessions = GameSession.query.filter(
            (GameSession.owner_id == user_id) |
            (GameSession.players.contains({str(user_id): {}}))
        ).filter_by(is_active=True).all()
        
        return [session.to_dict() for session in sessions]
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up inactive sessions"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0
        
        for session_id, session_info in list(self.active_sessions.items()):
            if session_info['last_accessed'] < cutoff_time:
                # Mark as inactive in database
                session = GameSession.query.filter_by(session_id=session_id).first()
                if session:
                    session.is_active = False
                    try:
                        db.session.commit()
                        cleaned_count += 1
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.error(f"Failed to cleanup session {session_id}: {e}")
                
                # Remove from active sessions
                del self.active_sessions[session_id]
        
        current_app.logger.info(f"Cleaned up {cleaned_count} inactive sessions")
        return cleaned_count

# Global session manager instance
session_manager = SecureSessionManager()