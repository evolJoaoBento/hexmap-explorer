"""
Core hex data structures and coordinate operations
"""
import math
from dataclasses import dataclass, asdict
from typing import List, Tuple


@dataclass
class Hex:
    """Represents a single hex tile with terrain and state information"""
    q: int
    r: int
    s: int
    terrain: str
    description: str
    explored: bool = False
    visible: bool = False
    generating: bool = False
    distance_from_current: int = 999
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Remove runtime-only fields
        data.pop('generating', None)
        data.pop('distance_from_current', None)
        return data
    
    @classmethod
    def from_dict(cls, data):
        """Create Hex from dictionary (JSON deserialization)"""
        return cls(**data, generating=False, distance_from_current=999)
    
    def __str__(self):
        return f"Hex({self.q}, {self.r}, {self.s}) - {self.terrain}"


class HexCoordinates:
    """Utility class for hex coordinate operations"""
    
    @staticmethod
    def get_neighbors(q: int, r: int, s: int) -> List[Tuple[int, int, int]]:
        """Get all 6 neighbors of a hex coordinate"""
        directions = [
            (1, 0, -1), (1, -1, 0), (0, -1, 1),
            (-1, 0, 1), (-1, 1, 0), (0, 1, -1)
        ]
        return [(q + dq, r + dr, s + ds) for dq, dr, ds in directions]
    
    @staticmethod
    def get_hexes_within_radius(q: int, r: int, s: int, radius: int) -> List[Tuple[int, int, int]]:
        """Get all hex coordinates within a given radius"""
        hexes = []
        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                ds = -dq - dr
                hexes.append((q + dq, r + dr, s + ds))
        return hexes
    
    @staticmethod
    def distance(q1: int, r1: int, s1: int, q2: int, r2: int, s2: int) -> int:
        """Calculate distance between two hex coordinates"""
        return (abs(q1 - q2) + abs(r1 - r2) + abs(s1 - s2)) // 2
    
    @staticmethod
    def hex_to_pixel(q: int, r: int, hex_size: float, center_x: float, center_y: float) -> Tuple[float, float]:
        """Convert hex coordinates to pixel coordinates"""
        x = hex_size * (3/2 * q)
        y = hex_size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
        return (x + center_x, y + center_y)
    
    @staticmethod
    def pixel_to_hex(x: float, y: float, hex_size: float, center_x: float, center_y: float) -> Tuple[int, int, int]:
        """Convert pixel coordinates to hex coordinates"""
        x = (x - center_x) / hex_size
        y = (y - center_y) / hex_size
        
        q = (2/3) * x
        r = (-1/3) * x + (math.sqrt(3)/3) * y
        
        # Round and handle floating point errors
        rq = round(q)
        rr = round(r)
        rs = round(-q - r)
        
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - (-q - r))
        
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        
        return (rq, rr, -rq - rr)