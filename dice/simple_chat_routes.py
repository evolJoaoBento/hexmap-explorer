"""
Simple Chat Routes
Basic chat functionality separate from dice requests
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from .simple_chat_models import SimpleChatMessage, add_chat_message, get_chat_messages, init_simple_chat_db
from .routes import optional_auth, require_auth

# Initialize simple chat database (will be called when needed)
# init_simple_chat_db()

# Create Blueprint
simple_chat_api = Blueprint('simple_chat_api', __name__, url_prefix='/api/chat')

@simple_chat_api.route('/rooms/<room_id>/messages', methods=['GET'])
@require_auth
def get_room_messages(room_id):
    """Get messages for a room - combines chat and dice messages"""
    try:
        limit = min(request.args.get('limit', 50, type=int), 100)
        offset = request.args.get('offset', 0, type=int)

        # Get regular chat messages
        chat_messages = get_chat_messages(room_id, limit, offset)

        # Get dice request messages from the dice system
        from .request_models import ChatMessage, MessageType, get_dice_session
        dice_session = get_dice_session()
        try:
            dice_messages = dice_session.query(ChatMessage).filter(
                ChatMessage.room_id == room_id
            ).order_by(ChatMessage.created_at.desc()).limit(limit).offset(offset).all()
        finally:
            dice_session.close()

        # Combine and sort by timestamp
        all_messages = []

        # Add chat messages
        for msg in chat_messages:
            all_messages.append(msg.to_dict())

        # Add dice messages
        for msg in dice_messages:
            msg_dict = msg.to_dict()
            msg_dict['timestamp'] = msg.created_at.isoformat() if msg.created_at else None
            all_messages.append(msg_dict)

        # Sort by timestamp
        all_messages.sort(key=lambda x: x.get('timestamp', ''))

        return jsonify({
            'messages': all_messages[-limit:],  # Get latest messages
            'count': len(all_messages)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@simple_chat_api.route('/rooms/<room_id>/messages', methods=['POST'])
@require_auth
def send_message(room_id):
    """Send a chat message"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': 'Message content required'}), 400

        # Get user info from authentication (required now)
        user_id = g.user_id  # Will always be present with require_auth
        # Allow custom username from request, fallback to authenticated username
        username = data.get('username') or g.username
        user_role = data.get('user_role', 'player')

        # Ensure username is not None
        if not username or username == 'None':
            username = 'Anonymous'

        # Add message
        message = add_chat_message(
            room_id=room_id,
            content=content,
            user_id=user_id,
            username=username,
            user_role=user_role
        )

        return jsonify(message), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@simple_chat_api.route('/rooms', methods=['POST'])
@require_auth
def create_room():
    """Create a new chat room"""
    try:
        data = request.get_json() or {}
        room_id = data.get('room_id')

        if not room_id:
            return jsonify({'error': 'room_id is required'}), 400

        # Room names should be clean
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', room_id):
            return jsonify({'error': 'room_id can only contain letters, numbers, hyphens, and underscores'}), 400

        created_by = g.username
        description = data.get('description', f'Room created by {created_by}')

        # Add system message about room creation
        add_chat_message(
            room_id=room_id,
            content=f"Room '{room_id}' created by {created_by}",
            username="System",
            user_role="system",
            is_system=True
        )

        return jsonify({
            'message': 'Room created successfully',
            'room_id': room_id,
            'created_by': created_by,
            'description': description
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@simple_chat_api.route('/rooms/<room_id>/join', methods=['POST'])
@require_auth
def join_room(room_id):
    """Join a chat room (simplified - just return success)"""
    try:
        data = request.get_json() or {}
        # Allow custom username from request, fallback to authenticated username
        username = data.get('username') or g.username
        user_role = data.get('user_role', 'player')

        # Add system message about joining
        add_chat_message(
            room_id=room_id,
            content=f"{username} joined the room",
            username="System",
            user_role="system",
            is_system=True
        )

        return jsonify({
            'message': 'Joined room successfully',
            'room_id': room_id,
            'username': username,
            'user_role': user_role
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@simple_chat_api.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'service': 'simple-chat'}), 200