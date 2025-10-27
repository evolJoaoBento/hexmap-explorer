"""
Dice Request System API Routes
Handles DM-to-Player dice roll requests and chat integration
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_
from sqlalchemy.exc import SQLAlchemyError
import uuid

from .models import DiceRoll, get_dice_session, init_dice_db
from .engine import DiceRollEngine
from .request_models import (
    DiceRequest, ChatMessage, ChatRoom, RoomMember, DiceRequestTemplate,
    RequestStatus, MessageType, get_user_requests, get_room_messages,
    create_system_message, cleanup_expired_requests, init_request_db
)

# Initialize request database
request_engine = init_request_db()
roll_engine = DiceRollEngine()

# Create Blueprint for request system
dice_request_api = Blueprint('dice_request_api', __name__, url_prefix='/api/dice/requests')

# Import auth decorators from main routes
from .routes import optional_auth, require_auth

# --- DICE REQUEST ENDPOINTS ---

@dice_request_api.route('', methods=['POST'])
@require_auth
def create_dice_request():
    """Create a dice roll request (DM → Player)"""
    try:
        data = request.get_json()

        # Required fields
        expression = data.get('expression')
        target_id = data.get('target_id')
        target_username = data.get('target_username')

        if not all([expression, target_id]):
            return jsonify({'error': 'expression and target_id are required'}), 400

        # Validate expression
        from .engine import DiceRollEngine
        engine = DiceRollEngine()
        parsed = engine.parse_expression(expression)
        if not parsed['is_valid']:
            return jsonify({'error': 'Invalid dice expression'}), 400

        session = get_dice_session(request_engine)
        try:
            # Check if target user exists and is in the same room (if room specified)
            room_id = data.get('room_id')
            if room_id:
                member = session.query(RoomMember).filter(
                    RoomMember.room_id == room_id,
                    RoomMember.user_id == target_id,
                    RoomMember.is_active == True
                ).first()
                if not member:
                    return jsonify({'error': 'Target user not found in room'}), 400

            # Set expiration time
            expires_at = None
            timeout_minutes = data.get('timeout_minutes', 15)  # Default 15 minutes
            if timeout_minutes:
                expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)

            # Create the request
            dice_request = DiceRequest(
                expression=expression,
                description=data.get('description', f"Roll {expression}"),
                reason=data.get('reason'),
                requester_id=g.user_id,
                requester_username=g.username,
                target_id=target_id,
                target_username=target_username,
                campaign_id=data.get('campaign_id'),
                session_id=data.get('session_id'),
                room_id=room_id,
                priority=data.get('priority', 'normal'),
                allow_advantage=data.get('allow_advantage', True),
                allow_disadvantage=data.get('allow_disadvantage', True),
                require_reason=data.get('require_reason', False),
                auto_submit=data.get('auto_submit', False),
                expires_at=expires_at,
                extra_data=data.get('extra_data', {})
            )

            session.add(dice_request)
            session.commit()

            # Create chat message if in a room
            if room_id:
                message_content = f"🎲 **Dice Request**: {dice_request.description}\n"
                message_content += f"**Roll**: `{expression}`\n"
                if dice_request.reason:
                    message_content += f"**Reason**: {dice_request.reason}\n"
                message_content += f"**For**: {target_username}"

                chat_message = ChatMessage(
                    room_id=room_id,
                    message_type=MessageType.DICE_REQUEST,
                    content=message_content,
                    sender_id=g.user_id,
                    sender_username=g.username,
                    sender_role="dm",  # Assuming requester is DM
                    dice_request_id=dice_request.id,
                    target_user_id=target_id,
                    target_username=target_username
                )
                session.add(chat_message)
                session.commit()

            return jsonify({
                'request': dice_request.to_dict(),
                'message': 'Dice request created successfully'
            }), 201

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/pending', methods=['GET'])
@require_auth
def get_pending_requests():
    """Get pending dice requests for the current user"""
    try:
        session = get_dice_session(request_engine)
        try:
            # Clean up expired requests first
            cleanup_expired_requests()

            # Get pending requests for this user
            requests = session.query(DiceRequest).filter(
                DiceRequest.target_id == g.user_id,
                DiceRequest.status == RequestStatus.PENDING
            ).order_by(DiceRequest.created_at.desc()).all()

            return jsonify({
                'requests': [req.to_dict() for req in requests],
                'count': len(requests)
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/<request_id>/respond', methods=['POST'])
@require_auth
def respond_to_request(request_id):
    """Respond to a dice request by rolling"""
    try:
        data = request.get_json() or {}

        session = get_dice_session(request_engine)
        try:
            # Get the request
            dice_request = session.query(DiceRequest).filter(
                DiceRequest.id == request_id,
                DiceRequest.target_id == g.user_id,  # Only target can respond
                DiceRequest.status == RequestStatus.PENDING
            ).first()

            if not dice_request:
                return jsonify({'error': 'Request not found or already completed'}), 404

            # Check if expired
            if dice_request.expires_at and dice_request.expires_at < datetime.utcnow():
                dice_request.status = RequestStatus.EXPIRED
                session.commit()
                return jsonify({'error': 'Request has expired'}), 410

            # Get roll parameters
            advantage = data.get('advantage', False)
            disadvantage = data.get('disadvantage', False)
            player_comment = data.get('comment', '')

            # Validate advantage/disadvantage permissions
            if advantage and not dice_request.allow_advantage:
                return jsonify({'error': 'Advantage not allowed for this request'}), 400
            if disadvantage and not dice_request.allow_disadvantage:
                return jsonify({'error': 'Disadvantage not allowed for this request'}), 400

            # Perform the roll
            result = roll_engine.roll(dice_request.expression, advantage, disadvantage)

            # Save the roll
            db_roll = DiceRoll(
                user_id=g.user_id,
                username=g.username,
                expression=dice_request.expression,
                description=f"Response to: {dice_request.description}",
                raw_rolls=result.raw_rolls,
                modifiers=[(m[0], m[1]) for m in result.modifiers],
                total=result.total,
                source='dice_request',
                campaign_id=dice_request.campaign_id,
                session_id=dice_request.session_id,
                is_critical=result.is_critical,
                is_fumble=result.is_fumble,
                advantage=advantage,
                disadvantage=disadvantage
            )
            session.add(db_roll)
            session.flush()  # Get the roll ID

            # Update the request
            dice_request.status = RequestStatus.COMPLETED
            dice_request.responded_at = datetime.utcnow()
            dice_request.roll_id = db_roll.id
            dice_request.response_total = result.total
            dice_request.response_breakdown = result.breakdown
            dice_request.player_comment = player_comment

            session.commit()

            # Create response message in chat
            if dice_request.room_id:
                response_content = f"🎯 **Roll Result**: {result.total}\n"
                response_content += f"**Expression**: `{dice_request.expression}`\n"
                response_content += f"**Breakdown**: {result.breakdown}\n"
                if result.is_critical:
                    response_content += "🔥 **CRITICAL HIT!**\n"
                elif result.is_fumble:
                    response_content += "💥 **CRITICAL MISS!**\n"
                if player_comment:
                    response_content += f"**Comment**: {player_comment}\n"
                response_content += f"*In response to: {dice_request.description}*"

                chat_message = ChatMessage(
                    room_id=dice_request.room_id,
                    message_type=MessageType.DICE_RESPONSE,
                    content=response_content,
                    sender_id=g.user_id,
                    sender_username=g.username,
                    sender_role="player",
                    dice_request_id=dice_request.id,
                    roll_id=db_roll.id,
                    reply_to_id=None  # Could link to original request message
                )
                session.add(chat_message)
                session.commit()

            return jsonify({
                'request': dice_request.to_dict(),
                'roll': {
                    'id': db_roll.id,
                    **result.to_dict()
                }
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/<request_id>/cancel', methods=['POST'])
@require_auth
def cancel_request(request_id):
    """Cancel a dice request (requester only)"""
    try:
        session = get_dice_session(request_engine)
        try:
            dice_request = session.query(DiceRequest).filter(
                DiceRequest.id == request_id,
                DiceRequest.requester_id == g.user_id,  # Only requester can cancel
                DiceRequest.status == RequestStatus.PENDING
            ).first()

            if not dice_request:
                return jsonify({'error': 'Request not found or cannot be cancelled'}), 404

            dice_request.status = RequestStatus.CANCELLED
            session.commit()

            # Create system message
            if dice_request.room_id:
                create_system_message(
                    dice_request.room_id,
                    f"Dice request '{dice_request.description}' was cancelled by {g.username}.",
                    {'cancelled_request_id': request_id}
                )

            return jsonify({
                'message': 'Request cancelled successfully',
                'request': dice_request.to_dict()
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/history', methods=['GET'])
@require_auth
def get_request_history():
    """Get request history for the user"""
    try:
        status = request.args.get('status')  # pending, completed, cancelled, expired
        limit = min(request.args.get('limit', 50, type=int), 100)

        requests = get_user_requests(g.user_id, status, limit)

        return jsonify({
            'requests': [req.to_dict() for req in requests],
            'count': len(requests)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- CHAT ROOM ENDPOINTS ---

@dice_request_api.route('/rooms', methods=['GET'])
@require_auth
def get_user_rooms():
    """Get rooms the user is a member of"""
    try:
        session = get_dice_session(request_engine)
        try:
            rooms = session.query(ChatRoom).join(RoomMember).filter(
                RoomMember.user_id == g.user_id,
                RoomMember.is_active == True
            ).all()

            return jsonify({
                'rooms': [room.to_dict() for room in rooms]
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/rooms', methods=['POST'])
@require_auth
def create_room():
    """Create a new chat room"""
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'error': 'Room name is required'}), 400

        session = get_dice_session(request_engine)
        try:
            room = ChatRoom(
                name=name,
                description=data.get('description'),
                room_type=data.get('room_type', 'campaign'),
                is_public=data.get('is_public', False),
                max_members=data.get('max_members', 50),
                campaign_id=data.get('campaign_id'),
                session_id=data.get('session_id'),
                created_by=g.user_id,
                allow_dice_requests=data.get('allow_dice_requests', True),
                allow_public_rolls=data.get('allow_public_rolls', True),
                dice_request_timeout=data.get('dice_request_timeout', 300)
            )
            session.add(room)
            session.flush()

            # Add creator as member with DM role
            member = RoomMember(
                room_id=room.id,
                user_id=g.user_id,
                username=g.username,
                role='dm',
                can_request_rolls=True,
                can_see_all_rolls=True
            )
            session.add(member)
            session.commit()

            return jsonify({
                'room': room.to_dict(),
                'message': 'Room created successfully'
            }), 201

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/rooms/<room_id>/join', methods=['POST'])
@require_auth
def join_room(room_id):
    """Join a chat room"""
    try:
        data = request.get_json() or {}
        role = data.get('role', 'player')

        session = get_dice_session(request_engine)
        try:
            # Check if room exists
            room = session.query(ChatRoom).filter(ChatRoom.id == room_id).first()
            if not room:
                return jsonify({'error': 'Room not found'}), 404

            # Check if already a member
            existing = session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == g.user_id
            ).first()

            if existing:
                if existing.is_active:
                    return jsonify({'error': 'Already a member of this room'}), 409
                else:
                    # Reactivate membership
                    existing.is_active = True
                    existing.last_seen = datetime.utcnow()
            else:
                # Create new membership
                member = RoomMember(
                    room_id=room_id,
                    user_id=g.user_id,
                    username=g.username,
                    role=role,
                    can_request_rolls=role in ['dm', 'gm'],
                    can_see_all_rolls=True
                )
                session.add(member)

            session.commit()

            # Create system message
            create_system_message(
                room_id,
                f"{g.username} joined the room as {role}.",
                {'user_id': g.user_id, 'action': 'join'}
            )

            return jsonify({'message': 'Joined room successfully'}), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/rooms/<room_id>/messages', methods=['GET'])
@require_auth
def get_room_messages_api(room_id):
    """Get messages for a room"""
    try:
        limit = min(request.args.get('limit', 100, type=int), 200)
        before_id = request.args.get('before_id')

        session = get_dice_session(request_engine)
        try:
            # Verify user is member of room
            member = session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == g.user_id,
                RoomMember.is_active == True
            ).first()

            if not member:
                return jsonify({'error': 'Not a member of this room'}), 403

            # Get messages
            messages = get_room_messages(room_id, limit, before_id)

            # Filter whispers (only show if user is sender or target)
            filtered_messages = []
            for msg in messages:
                if msg.is_whisper:
                    if msg.sender_id == g.user_id or msg.target_user_id == g.user_id:
                        filtered_messages.append(msg.to_dict())
                else:
                    filtered_messages.append(msg.to_dict())

            return jsonify({
                'messages': list(reversed(filtered_messages)),  # Reverse for chronological order
                'count': len(filtered_messages)
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/rooms/<room_id>/messages', methods=['POST'])
@require_auth
def send_message(room_id):
    """Send a message to a room"""
    try:
        data = request.get_json()
        content = data.get('content')

        if not content:
            return jsonify({'error': 'Message content is required'}), 400

        session = get_dice_session(request_engine)
        try:
            # Verify user is member of room
            member = session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == g.user_id,
                RoomMember.is_active == True
            ).first()

            if not member:
                return jsonify({'error': 'Not a member of this room'}), 403

            message = ChatMessage(
                room_id=room_id,
                message_type=MessageType.TEXT,
                content=content,
                sender_id=g.user_id,
                sender_username=g.username,
                sender_role=member.role,
                target_user_id=data.get('target_user_id'),
                target_username=data.get('target_username'),
                is_whisper=data.get('is_whisper', False),
                reply_to_id=data.get('reply_to_id')
            )

            session.add(message)
            session.commit()

            return jsonify({
                'message': message.to_dict()
            }), 201

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- REQUEST TEMPLATE ENDPOINTS ---

@dice_request_api.route('/templates', methods=['GET'])
@require_auth
def get_request_templates():
    """Get dice request templates"""
    try:
        session = get_dice_session(request_engine)
        try:
            templates = session.query(DiceRequestTemplate).filter(
                or_(
                    DiceRequestTemplate.created_by == g.user_id,
                    DiceRequestTemplate.is_public == True
                )
            ).order_by(DiceRequestTemplate.name).all()

            return jsonify({
                'templates': [template.to_dict() for template in templates]
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/templates', methods=['POST'])
@require_auth
def create_request_template():
    """Create a dice request template"""
    try:
        data = request.get_json()
        name = data.get('name')
        expression = data.get('expression')

        if not all([name, expression]):
            return jsonify({'error': 'name and expression are required'}), 400

        # Validate expression
        parsed = roll_engine.parse_expression(expression)
        if not parsed['is_valid']:
            return jsonify({'error': 'Invalid dice expression'}), 400

        session = get_dice_session(request_engine)
        try:
            template = DiceRequestTemplate(
                name=name,
                expression=expression,
                description=data.get('description'),
                reason_template=data.get('reason_template'),
                allow_advantage=data.get('allow_advantage', True),
                allow_disadvantage=data.get('allow_disadvantage', True),
                priority=data.get('priority', 'normal'),
                created_by=g.user_id,
                is_public=data.get('is_public', False),
                category=data.get('category')
            )

            session.add(template)
            session.commit()

            return jsonify(template.to_dict()), 201

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- UTILITY ENDPOINTS ---

@dice_request_api.route('/cleanup', methods=['POST'])
@require_auth
def cleanup_expired():
    """Clean up expired requests (admin/DM only)"""
    try:
        # TODO: Add admin check
        count = cleanup_expired_requests()

        return jsonify({
            'message': f'Cleaned up {count} expired requests'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_request_api.route('/stats', methods=['GET'])
@require_auth
def get_request_stats():
    """Get request statistics for the user"""
    try:
        session = get_dice_session(request_engine)
        try:
            # Get counts by status
            stats = {}
            for status in RequestStatus:
                sent_count = session.query(DiceRequest).filter(
                    DiceRequest.requester_id == g.user_id,
                    DiceRequest.status == status
                ).count()

                received_count = session.query(DiceRequest).filter(
                    DiceRequest.target_id == g.user_id,
                    DiceRequest.status == status
                ).count()

                stats[f'{status.value}_sent'] = sent_count
                stats[f'{status.value}_received'] = received_count

            return jsonify({'stats': stats}), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500