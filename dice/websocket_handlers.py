"""
WebSocket handlers for real-time dice request and chat system
Handles SocketIO events for live updates
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request, session, g
from functools import wraps
import jwt
import os

from .request_models import (
    ChatRoom, RoomMember, ChatMessage, DiceRequest,
    get_dice_session, init_request_db, MessageType
)

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Active connections tracking
active_connections = {}  # {user_id: {socket_id: socket_info}}
room_connections = {}    # {room_id: set(user_ids)}

def authenticate_socket(f):
    """Decorator to authenticate socket connections"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            emit('error', {'message': 'Authentication token required'})
            disconnect()
            return

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            session['user_id'] = payload.get('user_id')
            session['username'] = payload.get('username')
            session['authenticated'] = True
        except jwt.InvalidTokenError:
            emit('error', {'message': 'Invalid authentication token'})
            disconnect()
            return

        return f(*args, **kwargs)
    return decorated_function

def register_websocket_handlers(socketio):
    """Register all WebSocket handlers with the SocketIO instance"""

    @socketio.on('connect')
    def handle_connect():
        """Handle new socket connection"""
        print(f"Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to dice request system'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle socket disconnection"""
        user_id = session.get('user_id')
        if user_id and user_id in active_connections:
            if request.sid in active_connections[user_id]:
                del active_connections[user_id][request.sid]
                if not active_connections[user_id]:  # No more connections for this user
                    del active_connections[user_id]

                    # Remove from room connections
                    for room_id, user_set in room_connections.items():
                        user_set.discard(user_id)

                    # Notify rooms that user went offline
                    for room_id in room_connections:
                        socketio.emit('user_status_changed', {
                            'user_id': user_id,
                            'username': session.get('username'),
                            'status': 'offline'
                        }, room=room_id)

        print(f"Client disconnected: {request.sid}")

    @socketio.on('authenticate')
    @authenticate_socket
    def handle_authenticate(data):
        """Authenticate the socket connection"""
        user_id = session.get('user_id')
        username = session.get('username')

        # Track active connection
        if user_id not in active_connections:
            active_connections[user_id] = {}

        active_connections[user_id][request.sid] = {
            'connected_at': datetime.utcnow().isoformat(),
            'username': username
        }

        emit('authenticated', {
            'user_id': user_id,
            'username': username,
            'message': 'Successfully authenticated'
        })

        # Send pending dice requests
        from .request_models import get_user_requests, RequestStatus
        pending_requests = get_user_requests(user_id, RequestStatus.PENDING, 10)
        if pending_requests:
            emit('pending_requests', {
                'requests': [req.to_dict() for req in pending_requests],
                'count': len(pending_requests)
            })

    @socketio.on('join_room')
    @authenticate_socket
    def handle_join_room(data):
        """Join a chat room for real-time updates"""
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'message': 'room_id required'})
            return

        user_id = session.get('user_id')
        username = session.get('username')

        # Verify user is member of room
        db_session = get_dice_session()
        try:
            member = db_session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
                RoomMember.is_active == True
            ).first()

            if not member:
                emit('error', {'message': 'Not a member of this room'})
                return

            # Join the SocketIO room
            join_room(room_id)

            # Track room connection
            if room_id not in room_connections:
                room_connections[room_id] = set()
            room_connections[room_id].add(user_id)

            # Update last seen
            member.last_seen = datetime.utcnow()
            db_session.commit()

            emit('joined_room', {
                'room_id': room_id,
                'message': f'Joined room successfully'
            })

            # Notify other room members
            emit('user_joined', {
                'user_id': user_id,
                'username': username,
                'role': member.role
            }, room=room_id, include_self=False)

        except Exception as e:
            emit('error', {'message': str(e)})
        finally:
            db_session.close()

    @socketio.on('leave_room')
    @authenticate_socket
    def handle_leave_room(data):
        """Leave a chat room"""
        room_id = data.get('room_id')
        if not room_id:
            return

        user_id = session.get('user_id')
        username = session.get('username')

        leave_room(room_id)

        # Remove from tracking
        if room_id in room_connections:
            room_connections[room_id].discard(user_id)

        emit('left_room', {'room_id': room_id})

        # Notify other room members
        emit('user_left', {
            'user_id': user_id,
            'username': username
        }, room=room_id)

    @socketio.on('send_message')
    @authenticate_socket
    def handle_send_message(data):
        """Send a message to a room"""
        room_id = data.get('room_id')
        content = data.get('content')

        if not all([room_id, content]):
            emit('error', {'message': 'room_id and content required'})
            return

        user_id = session.get('user_id')
        username = session.get('username')

        db_session = get_dice_session()
        try:
            # Verify user is member of room
            member = db_session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
                RoomMember.is_active == True
            ).first()

            if not member:
                emit('error', {'message': 'Not a member of this room'})
                return

            # Create message
            from datetime import datetime
            message = ChatMessage(
                room_id=room_id,
                message_type=MessageType.TEXT,
                content=content,
                sender_id=user_id,
                sender_username=username,
                sender_role=member.role,
                target_user_id=data.get('target_user_id'),
                target_username=data.get('target_username'),
                is_whisper=data.get('is_whisper', False)
            )

            db_session.add(message)
            db_session.commit()

            # Broadcast message
            message_data = message.to_dict()

            if message.is_whisper:
                # Send only to target and sender
                if message.target_user_id and message.target_user_id in active_connections:
                    for socket_id in active_connections[message.target_user_id]:
                        socketio.emit('new_message', message_data, room=socket_id)
                # Send to sender
                emit('new_message', message_data)
            else:
                # Broadcast to entire room
                emit('new_message', message_data, room=room_id, include_self=False)
                emit('message_sent', message_data)

        except Exception as e:
            emit('error', {'message': str(e)})
        finally:
            db_session.close()

    @socketio.on('request_dice_roll')
    @authenticate_socket
    def handle_request_dice_roll(data):
        """Create a dice roll request"""
        expression = data.get('expression')
        target_id = data.get('target_id')
        room_id = data.get('room_id')

        if not all([expression, target_id]):
            emit('error', {'message': 'expression and target_id required'})
            return

        user_id = session.get('user_id')
        username = session.get('username')

        db_session = get_dice_session()
        try:
            # Verify permissions and create request
            from .engine import DiceRollEngine
            from datetime import datetime, timedelta

            engine = DiceRollEngine()
            parsed = engine.parse_expression(expression)
            if not parsed['is_valid']:
                emit('error', {'message': 'Invalid dice expression'})
                return

            # Get target username
            if room_id:
                target_member = db_session.query(RoomMember).filter(
                    RoomMember.room_id == room_id,
                    RoomMember.user_id == target_id,
                    RoomMember.is_active == True
                ).first()

                if not target_member:
                    emit('error', {'message': 'Target user not found in room'})
                    return

                target_username = target_member.username
            else:
                # Would need to query user table for username
                target_username = f"User {target_id}"

            # Create request
            dice_request = DiceRequest(
                expression=expression,
                description=data.get('description', f"Roll {expression}"),
                reason=data.get('reason'),
                requester_id=user_id,
                requester_username=username,
                target_id=target_id,
                target_username=target_username,
                room_id=room_id,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                **{k: data.get(k, v) for k, v in {
                    'priority': 'normal',
                    'allow_advantage': True,
                    'allow_disadvantage': True,
                    'require_reason': False,
                    'auto_submit': False
                }.items()}
            )

            db_session.add(dice_request)
            db_session.commit()

            request_data = dice_request.to_dict()

            # Notify target user
            if target_id in active_connections:
                for socket_id in active_connections[target_id]:
                    socketio.emit('dice_request_received', request_data, room=socket_id)

            # Notify room if applicable
            if room_id:
                emit('dice_request_created', request_data, room=room_id, include_self=False)

            emit('dice_request_sent', request_data)

        except Exception as e:
            emit('error', {'message': str(e)})
        finally:
            db_session.close()

    @socketio.on('respond_to_dice_request')
    @authenticate_socket
    def handle_respond_to_dice_request(data):
        """Respond to a dice request"""
        request_id = data.get('request_id')

        if not request_id:
            emit('error', {'message': 'request_id required'})
            return

        user_id = session.get('user_id')
        username = session.get('username')

        db_session = get_dice_session()
        try:
            from .request_models import RequestStatus
            from .models import DiceRoll
            from .engine import DiceRollEngine
            from datetime import datetime

            # Get the request
            dice_request = db_session.query(DiceRequest).filter(
                DiceRequest.id == request_id,
                DiceRequest.target_id == user_id,
                DiceRequest.status == RequestStatus.PENDING
            ).first()

            if not dice_request:
                emit('error', {'message': 'Request not found or already completed'})
                return

            # Validate parameters
            advantage = data.get('advantage', False)
            disadvantage = data.get('disadvantage', False)

            if advantage and not dice_request.allow_advantage:
                emit('error', {'message': 'Advantage not allowed'})
                return
            if disadvantage and not dice_request.allow_disadvantage:
                emit('error', {'message': 'Disadvantage not allowed'})
                return

            # Roll the dice
            engine = DiceRollEngine()
            result = engine.roll(dice_request.expression, advantage, disadvantage)

            # Save the roll
            db_roll = DiceRoll(
                user_id=user_id,
                username=username,
                expression=dice_request.expression,
                description=f"Response to: {dice_request.description}",
                raw_rolls=result.raw_rolls,
                modifiers=[(m[0], m[1]) for m in result.modifiers],
                total=result.total,
                source='dice_request_ws',
                is_critical=result.is_critical,
                is_fumble=result.is_fumble,
                advantage=advantage,
                disadvantage=disadvantage
            )
            db_session.add(db_roll)
            db_session.flush()

            # Update request
            dice_request.status = RequestStatus.COMPLETED
            dice_request.responded_at = datetime.utcnow()
            dice_request.roll_id = db_roll.id
            dice_request.response_total = result.total
            dice_request.response_breakdown = result.breakdown
            dice_request.player_comment = data.get('comment', '')

            db_session.commit()

            response_data = {
                'request': dice_request.to_dict(),
                'roll': {
                    'id': db_roll.id,
                    **result.to_dict()
                }
            }

            # Notify requester
            if dice_request.requester_id in active_connections:
                for socket_id in active_connections[dice_request.requester_id]:
                    socketio.emit('dice_request_completed', response_data, room=socket_id)

            # Notify room
            if dice_request.room_id:
                emit('dice_roll_result', response_data, room=dice_request.room_id, include_self=False)

            emit('dice_request_responded', response_data)

        except Exception as e:
            emit('error', {'message': str(e)})
        finally:
            db_session.close()

    @socketio.on('get_room_members')
    @authenticate_socket
    def handle_get_room_members(data):
        """Get online members of a room"""
        room_id = data.get('room_id')
        if not room_id:
            emit('error', {'message': 'room_id required'})
            return

        user_id = session.get('user_id')

        db_session = get_dice_session()
        try:
            # Verify user is member
            member = db_session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.user_id == user_id,
                RoomMember.is_active == True
            ).first()

            if not member:
                emit('error', {'message': 'Not a member of this room'})
                return

            # Get all room members
            members = db_session.query(RoomMember).filter(
                RoomMember.room_id == room_id,
                RoomMember.is_active == True
            ).all()

            # Add online status
            members_data = []
            for m in members:
                member_data = m.to_dict()
                member_data['online'] = m.user_id in active_connections
                members_data.append(member_data)

            emit('room_members', {
                'room_id': room_id,
                'members': members_data
            })

        except Exception as e:
            emit('error', {'message': str(e)})
        finally:
            db_session.close()

    @socketio.on('typing_start')
    @authenticate_socket
    def handle_typing_start(data):
        """User started typing"""
        room_id = data.get('room_id')
        if room_id:
            emit('user_typing', {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'typing': True
            }, room=room_id, include_self=False)

    @socketio.on('typing_stop')
    @authenticate_socket
    def handle_typing_stop(data):
        """User stopped typing"""
        room_id = data.get('room_id')
        if room_id:
            emit('user_typing', {
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'typing': False
            }, room=room_id, include_self=False)

    return {
        'active_connections': active_connections,
        'room_connections': room_connections
    }

# Utility functions for emitting events from API endpoints

def notify_dice_request_created(socketio, dice_request):
    """Notify about new dice request"""
    from .request_models import RequestStatus

    if dice_request.status != RequestStatus.PENDING:
        return

    request_data = dice_request.to_dict()

    # Notify target user
    if dice_request.target_id in active_connections:
        for socket_id in active_connections[dice_request.target_id]:
            socketio.emit('dice_request_received', request_data, room=socket_id)

    # Notify room
    if dice_request.room_id:
        socketio.emit('dice_request_created', request_data, room=dice_request.room_id)

def notify_dice_request_completed(socketio, dice_request, roll_result):
    """Notify about completed dice request"""
    response_data = {
        'request': dice_request.to_dict(),
        'roll': roll_result
    }

    # Notify requester
    if dice_request.requester_id in active_connections:
        for socket_id in active_connections[dice_request.requester_id]:
            socketio.emit('dice_request_completed', response_data, room=socket_id)

    # Notify room
    if dice_request.room_id:
        socketio.emit('dice_roll_result', response_data, room=dice_request.room_id)

def notify_message_sent(socketio, message):
    """Notify about new chat message"""
    message_data = message.to_dict()

    if message.is_whisper:
        # Send to target and sender only
        if message.target_user_id and message.target_user_id in active_connections:
            for socket_id in active_connections[message.target_user_id]:
                socketio.emit('new_message', message_data, room=socket_id)
    else:
        # Broadcast to room
        socketio.emit('new_message', message_data, room=message.room_id)

from datetime import datetime