"""
Input validation schemas for Hex Explorer API endpoints
"""
from marshmallow import Schema, fields, validate, ValidationError, pre_load
import re

class HexCoordinateSchema(Schema):
    """Validate hex coordinates with reasonable bounds"""
    q = fields.Int(required=True, validate=validate.Range(min=-1000, max=1000))
    r = fields.Int(required=True, validate=validate.Range(min=-1000, max=1000))
    s = fields.Int(required=True, validate=validate.Range(min=-1000, max=1000))
    
    def validate_hex_sum(self, data, **kwargs):
        """Validate that q + r + s = 0 (hex coordinate constraint)"""
        if data['q'] + data['r'] + data['s'] != 0:
            raise ValidationError("Invalid hex coordinates: q + r + s must equal 0")

class SessionIdSchema(Schema):
    """Validate session ID format"""
    session_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Session ID contains invalid characters')
        ]
    )

class SessionNameSchema(Schema):
    """Validate session name"""
    session_name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9\s_-]+$', error='Session name contains invalid characters')
        ]
    )
    
    @pre_load
    def strip_whitespace(self, data, **kwargs):
        if 'session_name' in data:
            data['session_name'] = data['session_name'].strip()
        return data

class UpdatePlayerPositionSchema(HexCoordinateSchema):
    """Schema for updating player position"""
    pass

class CreateMapSessionSchema(Schema):
    """Schema for creating a new map session"""
    seed = fields.Int(validate=validate.Range(min=1, max=2147483647), missing=None)
    name = fields.Str(
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^[a-zA-Z0-9\s_-]+$', error='Name contains invalid characters')
        ],
        missing='Generated Map'
    )
    
    @pre_load
    def strip_whitespace(self, data, **kwargs):
        if 'name' in data:
            data['name'] = data['name'].strip()
        return data

class UpdateHexTerrainSchema(SessionIdSchema, HexCoordinateSchema):
    """Schema for updating hex terrain"""
    terrain = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(r'^[a-z_]+$', error='Terrain must contain only lowercase letters and underscores')
        ]
    )

class TeleportPlayerSchema(SessionIdSchema):
    """Schema for teleporting a player"""
    player_name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(r'^[a-zA-Z0-9\s_-]+$', error='Player name contains invalid characters')
        ]
    )
    target_hex = fields.Nested(HexCoordinateSchema, required=True)

class GenerateHexMapSchema(SessionIdSchema):
    """Schema for generating hex map"""
    seed = fields.Int(validate=validate.Range(min=1, max=2147483647), missing=None)

class UpdateSessionNameSchema(SessionIdSchema, SessionNameSchema):
    """Schema for updating session name"""
    pass

class SaveMapForGameSchema(SessionIdSchema):
    """Schema for saving map for game"""
    map_data = fields.Dict(required=True)
    
    @pre_load
    def validate_map_data(self, data, **kwargs):
        """Basic validation of map data structure"""
        if 'map_data' in data:
            map_data = data['map_data']
            if not isinstance(map_data, dict):
                raise ValidationError('map_data must be a dictionary')
            
            # Check for required keys
            if 'hexes' not in map_data:
                raise ValidationError('map_data must contain hexes')
            
            # Limit number of hexes to prevent DoS
            hexes = map_data.get('hexes', [])
            if len(hexes) > 10000:
                raise ValidationError('Too many hexes (max 10,000 allowed)')
        
        return data

class GenerateDescriptionSchema(HexCoordinateSchema):
    """Schema for generating hex description"""
    pass

class ForceSyncWorldSchema(SessionIdSchema):
    """Schema for force sync world"""
    hexes = fields.List(fields.Dict(), required=True, validate=validate.Length(max=10000))
    north_direction = fields.Float(validate=validate.Range(min=0, max=360), missing=0)
    
    @pre_load
    def validate_hex_data(self, data, **kwargs):
        """Validate hex data structure"""
        if 'hexes' in data:
            for i, hex_data in enumerate(data['hexes']):
                if not isinstance(hex_data, dict):
                    raise ValidationError(f'Hex {i} must be a dictionary')
                
                # Check required fields
                required_fields = ['q', 'r', 's', 'terrain']
                for field in required_fields:
                    if field not in hex_data:
                        raise ValidationError(f'Hex {i} missing required field: {field}')
                
                # Validate coordinates
                try:
                    q, r, s = hex_data['q'], hex_data['r'], hex_data['s']
                    if not all(isinstance(coord, int) for coord in [q, r, s]):
                        raise ValidationError(f'Hex {i} coordinates must be integers')
                    if q + r + s != 0:
                        raise ValidationError(f'Hex {i} invalid coordinates: q+r+s must equal 0')
                    if not all(-1000 <= coord <= 1000 for coord in [q, r, s]):
                        raise ValidationError(f'Hex {i} coordinates out of bounds')
                except (KeyError, TypeError, ValueError) as e:
                    raise ValidationError(f'Hex {i} coordinate validation error: {str(e)}')
        
        return data

def validate_request_data(schema_class, request_data):
    """
    Helper function to validate request data against a schema
    
    Args:
        schema_class: Marshmallow schema class
        request_data: Data to validate
        
    Returns:
        tuple: (validated_data, error_response)
               If validation passes: (data, None)
               If validation fails: (None, error_dict)
    """
    schema = schema_class()
    
    try:
        validated_data = schema.load(request_data)
        return validated_data, None
    except ValidationError as err:
        error_response = {
            'success': False,
            'error': 'Validation failed',
            'details': err.messages
        }
        return None, error_response
    except Exception as e:
        error_response = {
            'success': False,
            'error': 'Validation error',
            'details': str(e)
        }
        return None, error_response

# Sanitization helpers
def sanitize_string(value, max_length=100):
    """Sanitize string input to prevent XSS and injection"""
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\'\&\x00-\x1f\x7f-\x9f]', '', value)
    
    # Limit length
    return sanitized[:max_length].strip()

def sanitize_session_id(session_id):
    """Sanitize session ID to ensure it's safe"""
    if not isinstance(session_id, str):
        return None
    
    # Only allow alphanumeric, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        return None
    
    return session_id[:100]  # Limit length