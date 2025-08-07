"""
Hex map data management
"""
import json
import random
from typing import Dict, List, Tuple
from core.hex import Hex, HexCoordinates
from travel.system import TravelSystem
from generation.manager import GenerationManager
from config.constants import TERRAIN_TYPES


class HexMap:
    """Hex map with travel system integration"""
    
    def __init__(self, generation_manager: GenerationManager):
        self.hexes: Dict[Tuple[int, int, int], Hex] = {}
        self.gen_manager = generation_manager
        self.current_position = (0, 0, 0)
        self.travel_system = TravelSystem()
        self.coords = HexCoordinates()
    
    def create_hex(self, q: int, r: int, s: int) -> Hex:
        """Create a hex with terrain based on neighbors"""
        neighbors = self.coords.get_neighbors(q, r, s)
        neighbor_terrains = []
        
        for nq, nr, ns in neighbors:
            if (nq, nr, ns) in self.hexes:
                neighbor_terrains.append(self.hexes[(nq, nr, ns)].terrain)
        
        # Use neighbor terrain 60% of the time for coherent regions
        if neighbor_terrains and random.random() < 0.6:
            terrain = random.choice(neighbor_terrains)
        else:
            terrain = random.choice(list(TERRAIN_TYPES.keys()))
        
        return Hex(q, r, s, terrain, "Awaiting description...", generating=True)
    
    def initialize_map(self):
        """Initialize starting area with generation"""
        # Create starting hex
        start_hex = self.create_hex(0, 0, 0)
        start_hex.explored = True
        start_hex.visible = True
        self.hexes[(0, 0, 0)] = start_hex
        
        hexes_to_generate = [(start_hex, (0, 0))]
        
        # Create visible neighbors
        for q, r, s in self.coords.get_neighbors(0, 0, 0):
            hex_obj = self.create_hex(q, r, s)
            hex_obj.visible = True
            self.hexes[(q, r, s)] = hex_obj
            hexes_to_generate.append((hex_obj, (q, r)))
        
        self.gen_manager.start_generation(hexes_to_generate, "scouting")
    
    def get_adjacent_explored(self, q: int, r: int, s: int) -> List[Tuple[int, int, int]]:
        """Get adjacent hexes that are explored"""
        neighbors = self.coords.get_neighbors(q, r, s)
        return [coord for coord in neighbors 
                if coord in self.hexes and self.hexes[coord].explored]
    
    def calculate_distances(self):
        """Calculate distance from current position to all hexes"""
        curr_q, curr_r, curr_s = self.current_position
        for (q, r, s), hex_obj in self.hexes.items():
            hex_obj.distance_from_current = self.coords.distance(
                curr_q, curr_r, curr_s, q, r, s
            )
    
    def rest_and_scout(self):
        """Rest and reveal hexes within 2-hex radius"""
        self.travel_system.rest()
        
        curr_q, curr_r, curr_s = self.current_position
        hexes_to_generate = []
        
        for q, r, s in self.coords.get_hexes_within_radius(curr_q, curr_r, curr_s, 2):
            if (q, r, s) not in self.hexes:
                new_hex = self.create_hex(q, r, s)
                new_hex.visible = True
                self.hexes[(q, r, s)] = new_hex
                hexes_to_generate.append((new_hex, (q, r)))
            else:
                self.hexes[(q, r, s)].visible = True
        
        if hexes_to_generate:
            self.gen_manager.start_generation(hexes_to_generate, "resting")
    
    def navigate_to_hex(self, q: int, r: int, s: int):
        """Navigate to an already explored hex"""
        if (q, r, s) in self.hexes and self.hexes[(q, r, s)].explored:
            hex_obj = self.hexes[(q, r, s)]
            
            if not self.travel_system.can_move_to(hex_obj.terrain):
                return False, "Not enough movement points!"
            
            self.travel_system.move_to_hex(hex_obj.terrain)
            self.current_position = (q, r, s)
            
            # Make neighbors visible
            for nq, nr, ns in self.coords.get_neighbors(q, r, s):
                if (nq, nr, ns) in self.hexes:
                    self.hexes[(nq, nr, ns)].visible = True
            
            self.calculate_distances()
            return True, None
        return False, "Cannot navigate to unexplored hex!"
    
    def explore_hex(self, q: int, r: int, s: int):
        """Explore a hex and generate neighbors"""
        if (q, r, s) not in self.hexes:
            return False, "Hex doesn't exist!"
        
        hex_obj = self.hexes[(q, r, s)]
        if hex_obj.generating:
            return False, "Still generating..."
        
        if not self.travel_system.can_move_to(hex_obj.terrain):
            return False, f"Need {TERRAIN_TYPES[hex_obj.terrain]['movement_cost']} movement points!"
        
        # Move to the hex
        self.travel_system.move_to_hex(hex_obj.terrain)
        hex_obj.explored = True
        self.current_position = (q, r, s)
        
        # Generate new neighbors
        hexes_to_generate = []
        for nq, nr, ns in self.coords.get_neighbors(q, r, s):
            if (nq, nr, ns) not in self.hexes:
                new_hex = self.create_hex(nq, nr, ns)
                new_hex.visible = True
                self.hexes[(nq, nr, ns)] = new_hex
                hexes_to_generate.append((new_hex, (nq, nr)))
            else:
                self.hexes[(nq, nr, ns)].visible = True
        
        if hexes_to_generate:
            self.gen_manager.start_generation(hexes_to_generate, "scouting")
        
        self.calculate_distances()
        return True, None
    
    def save_to_json(self, filename: str):
        """Save map to JSON file"""
        map_data = {
            "current_position": self.current_position,
            "hexes": [hex_obj.to_dict() for hex_obj in self.hexes.values()],
            "travel_data": self.travel_system.get_save_data()
        }
        with open(filename, 'w') as f:
            json.dump(map_data, f, indent=2)
    
    def load_from_json(self, filename: str):
        """Load map from JSON file"""
        with open(filename, 'r') as f:
            map_data = json.load(f)
        
        self.hexes.clear()
        self.current_position = tuple(map_data["current_position"])
        
        # Load hexes
        for hex_data in map_data["hexes"]:
            hex_obj = Hex.from_dict(hex_data)
            self.hexes[(hex_obj.q, hex_obj.r, hex_obj.s)] = hex_obj
        
        # Load travel system data
        if "travel_data" in map_data:
            self.travel_system.load_from_data(map_data["travel_data"])
        
        self.calculate_distances()
