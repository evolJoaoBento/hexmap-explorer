"""
Dice Roll API Routes
Blueprint for dice roll endpoints
"""

from flask import Blueprint, request, jsonify, g
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import desc, func
import jwt
import os

from .models import DiceRoll, RollTemplate, RollStatistics, get_dice_session, init_dice_db
from .engine import DiceRollEngine

# Initialize dice roll database
dice_engine = init_dice_db()
roll_engine = DiceRollEngine()

# Create Blueprint
dice_api = Blueprint('dice_api', __name__, url_prefix='/api/dice')

# JWT Configuration - Use same secret as main auth system
from flask import current_app
JWT_ALGORITHM = 'HS256'

def get_jwt_secret():
    """Get JWT secret from Flask app config to match main auth system"""
    return current_app.config['SECRET_KEY']

def optional_auth(f):
    """Decorator for optional authentication - allows both authenticated and anonymous"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.user = None
        g.user_id = None
        g.username = None

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
                g.user_id = payload.get('user_id')
                g.username = payload.get('username')
                g.user = {'id': g.user_id, 'username': g.username}
            except jwt.InvalidTokenError:
                pass  # Invalid token, continue as anonymous

        return f(*args, **kwargs)
    return decorated_function

def require_auth(f):
    """Decorator for required authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authorization token provided'}), 401

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
            g.user_id = payload.get('user_id')
            g.username = payload.get('username')
            g.user = {'id': g.user_id, 'username': g.username}
        except jwt.InvalidTokenError as e:
            return jsonify({'error': 'Invalid authorization token'}), 401

        return f(*args, **kwargs)
    return decorated_function

# --- ROLL ENDPOINTS ---

@dice_api.route('/roll', methods=['POST'])
@require_auth
def roll_dice():
    """
    Roll dice based on expression
    Body: {
        "expression": "3d6+2",
        "description": "Attack roll",
        "advantage": false,
        "disadvantage": false,
        "campaign_id": "optional-campaign-id",
        "session_id": "optional-session-id"
    }
    """
    try:
        data = request.get_json()
        expression = data.get('expression')

        if not expression:
            return jsonify({'error': 'Expression required'}), 400

        # Validate expression length
        if len(expression) > 500:
            return jsonify({'error': 'Expression too long'}), 400

        # Parse and validate expression first
        parsed = roll_engine.parse_expression(expression)
        if not parsed['is_valid']:
            return jsonify({'error': 'Invalid dice expression'}), 400

        # Perform the roll
        advantage = data.get('advantage', False)
        disadvantage = data.get('disadvantage', False)
        result = roll_engine.roll(expression, advantage, disadvantage)

        # Save to database
        session = get_dice_session(dice_engine)
        try:
            db_roll = DiceRoll(
                user_id=g.user_id,
                username=g.username,
                expression=expression,
                description=data.get('description'),
                raw_rolls=result.raw_rolls,
                modifiers=[(m[0], m[1]) for m in result.modifiers],
                total=result.total,
                source=data.get('source', 'api'),
                campaign_id=data.get('campaign_id'),
                session_id=data.get('session_id'),
                is_critical=result.is_critical,
                is_fumble=result.is_fumble,
                advantage=advantage,
                disadvantage=disadvantage
            )
            session.add(db_roll)
            session.commit()

            # Update user statistics if authenticated
            if g.user_id:
                update_user_statistics(session, g.user_id, result, expression)

            response = {
                'id': db_roll.id,
                **result.to_dict()
            }
            return jsonify(response), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/roll/bulk', methods=['POST'])
@require_auth
def bulk_roll():
    """Roll the same expression multiple times"""
    try:
        data = request.get_json()
        expression = data.get('expression')
        count = data.get('count', 1)

        if not expression:
            return jsonify({'error': 'Expression required'}), 400

        if count < 1 or count > 100:
            return jsonify({'error': 'Count must be between 1 and 100'}), 400

        results = roll_engine.bulk_roll(expression, count)

        session = get_dice_session(dice_engine)
        try:
            saved_rolls = []
            for result in results:
                db_roll = DiceRoll(
                    user_id=g.user_id,
                    username=g.username,
                    expression=expression,
                    description=data.get('description'),
                    raw_rolls=result.raw_rolls,
                    modifiers=[(m[0], m[1]) for m in result.modifiers],
                    total=result.total,
                    source='api-bulk',
                    campaign_id=data.get('campaign_id'),
                    session_id=data.get('session_id')
                )
                session.add(db_roll)
                saved_rolls.append(db_roll)

            session.commit()

            response = {
                'count': count,
                'expression': expression,
                'results': [{'id': r.id, 'total': r.total, 'breakdown': results[i].breakdown}
                           for i, r in enumerate(saved_rolls)],
                'summary': {
                    'total': sum(r.total for r in results),
                    'average': sum(r.total for r in results) / count,
                    'min': min(r.total for r in results),
                    'max': max(r.total for r in results)
                }
            }
            return jsonify(response), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/history', methods=['GET'])
@optional_auth
def get_roll_history():
    """Get roll history (user's rolls if authenticated, recent public rolls otherwise)"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        campaign_id = request.args.get('campaign_id')

        if limit > 100:
            limit = 100

        session = get_dice_session(dice_engine)
        try:
            query = session.query(DiceRoll)

            if g.user_id:
                query = query.filter(DiceRoll.user_id == g.user_id)

            if campaign_id:
                query = query.filter(DiceRoll.campaign_id == campaign_id)

            rolls = query.order_by(desc(DiceRoll.timestamp)).limit(limit).offset(offset).all()

            return jsonify({
                'rolls': [r.to_dict() for r in rolls],
                'count': len(rolls),
                'offset': offset
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/statistics', methods=['GET'])
@require_auth
def get_statistics():
    """Get user's roll statistics"""
    try:
        session = get_dice_session(dice_engine)
        try:
            stats = session.query(RollStatistics).filter_by(user_id=g.user_id).first()

            if not stats:
                return jsonify({
                    'message': 'No statistics available yet',
                    'stats': {
                        'total_rolls': 0,
                        'critical_count': 0,
                        'fumble_count': 0
                    }
                }), 200

            return jsonify({'stats': stats.to_dict()}), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- TEMPLATE ENDPOINTS ---

@dice_api.route('/templates', methods=['GET'])
@optional_auth
def get_templates():
    """Get roll templates (user's private + public)"""
    try:
        session = get_dice_session(dice_engine)
        try:
            query = session.query(RollTemplate)

            # Get user's templates and public templates
            if g.user_id:
                query = query.filter(
                    (RollTemplate.user_id == g.user_id) | (RollTemplate.is_public == True)
                )
            else:
                query = query.filter(RollTemplate.is_public == True)

            templates = query.all()

            return jsonify({
                'templates': [t.to_dict() for t in templates]
            }), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/templates', methods=['POST'])
@require_auth
def create_template():
    """Create a new roll template"""
    try:
        data = request.get_json()
        name = data.get('name')
        expression = data.get('expression')

        if not name or not expression:
            return jsonify({'error': 'Name and expression required'}), 400

        # Validate expression
        parsed = roll_engine.parse_expression(expression)
        if not parsed['is_valid']:
            return jsonify({'error': 'Invalid dice expression'}), 400

        session = get_dice_session(dice_engine)
        try:
            template = RollTemplate(
                user_id=g.user_id,
                name=name,
                expression=expression,
                description=data.get('description'),
                category=data.get('category'),
                is_public=data.get('is_public', False)
            )
            session.add(template)
            session.commit()

            return jsonify(template.to_dict()), 201

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/templates/<int:template_id>', methods=['DELETE'])
@require_auth
def delete_template(template_id):
    """Delete a roll template"""
    try:
        session = get_dice_session(dice_engine)
        try:
            template = session.query(RollTemplate).filter_by(
                id=template_id,
                user_id=g.user_id
            ).first()

            if not template:
                return jsonify({'error': 'Template not found'}), 404

            session.delete(template)
            session.commit()

            return jsonify({'message': 'Template deleted'}), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/templates/<int:template_id>/roll', methods=['POST'])
@optional_auth
def roll_template(template_id):
    """Roll using a template"""
    try:
        session = get_dice_session(dice_engine)
        try:
            template = session.query(RollTemplate).filter_by(id=template_id).first()

            if not template:
                return jsonify({'error': 'Template not found'}), 404

            # Check access
            if not template.is_public and template.user_id != g.user_id:
                return jsonify({'error': 'Access denied'}), 403

            # Roll using template expression
            data = request.get_json() or {}
            result = roll_engine.roll(template.expression,
                                    data.get('advantage', False),
                                    data.get('disadvantage', False))

            # Save roll
            db_roll = DiceRoll(
                user_id=g.user_id,
                username=g.username,
                expression=template.expression,
                description=f"Template: {template.name}",
                raw_rolls=result.raw_rolls,
                modifiers=[(m[0], m[1]) for m in result.modifiers],
                total=result.total,
                source='template',
                campaign_id=data.get('campaign_id'),
                session_id=data.get('session_id')
            )
            session.add(db_roll)
            session.commit()

            response = {
                'id': db_roll.id,
                'template_name': template.name,
                **result.to_dict()
            }
            return jsonify(response), 200

        finally:
            session.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- UTILITY ENDPOINTS ---

@dice_api.route('/parse', methods=['POST'])
def parse_expression():
    """Parse and validate a dice expression without rolling"""
    try:
        data = request.get_json()
        expression = data.get('expression')

        if not expression:
            return jsonify({'error': 'Expression required'}), 400

        parsed = roll_engine.parse_expression(expression)
        return jsonify(parsed), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dice_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'dice-api'}), 200

# --- HELPER FUNCTIONS ---

def update_user_statistics(session, user_id, result, expression):
    """Update user statistics after a roll"""
    try:
        stats = session.query(RollStatistics).filter_by(user_id=user_id).first()

        if not stats:
            stats = RollStatistics(user_id=user_id, dice_distribution={})
            session.add(stats)

        # Update counters
        stats.total_rolls += 1

        # Check for d20 rolls
        if 'd20' in expression.lower():
            stats.total_d20_rolls += 1
            if result.is_critical:
                stats.critical_count += 1
            if result.is_fumble:
                stats.fumble_count += 1

        # Update averages
        if stats.total_rolls == 1:
            stats.average_roll = float(result.total)
            stats.highest_roll = result.total
            stats.lowest_roll = result.total
        else:
            stats.average_roll = ((stats.average_roll * (stats.total_rolls - 1)) + result.total) / stats.total_rolls
            stats.highest_roll = max(stats.highest_roll, result.total)
            stats.lowest_roll = min(stats.lowest_roll, result.total)

        # Update dice distribution
        for dice_key in result.raw_rolls.keys():
            dice_type = dice_key.split('k')[0].split('d')[1] if 'd' in dice_key else None
            if dice_type:
                dice_type = f"d{dice_type}"
                if dice_type not in stats.dice_distribution:
                    stats.dice_distribution[dice_type] = 0
                stats.dice_distribution[dice_type] += 1

        stats.last_updated = datetime.utcnow()
        session.commit()

    except Exception as e:
        print(f"Error updating statistics: {e}")
        session.rollback()