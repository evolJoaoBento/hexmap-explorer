"""
Travel system mechanics for hex map exploration
"""
import random
from config.constants import TERRAIN_TYPES, TRANSPORTATION_MODES


class TravelSystem:
    """Enhanced travel system with mounts and vehicles"""
    
    def __init__(self):
        self.current_pace = "normal"
        self.current_transport = "on_foot"
        self.hours_traveled = 0
        self.movement_points = 8
        self.max_movement = 8
        self.is_resting = False
        self.exhaustion_level = 0
        self.days_traveled = 0
        self.supplies = 10
        self.mount_exhaustion = 0
        
        # Special conditions
        self.has_ranger = False
        self.has_outlander = False
        self.has_navigator = False
        self.favored_terrain = None
        
        self._update_movement_points()
    
    def _update_movement_points(self):
        """Update movement points based on current transport and pace"""
        transport = TRANSPORTATION_MODES[self.current_transport]
        base_movement = transport["base_hexes_per_8h"][self.current_pace]
        
        if self.has_navigator:
            base_movement = int(base_movement * 1.1)
        
        self.max_movement = base_movement
        if not self.is_resting:
            ratio = self.movement_points / (self.max_movement or 1)
            self.movement_points = base_movement * ratio
    
    def get_movement_cost(self, terrain: str) -> float:
        """Get movement cost for terrain type with transport modifiers"""
        base_cost = TERRAIN_TYPES[terrain]["movement_cost"]
        transport = TRANSPORTATION_MODES[self.current_transport]
        
        transport_modifier = transport["terrain_modifiers"].get(terrain, 1.0)
        
        if transport_modifier >= 999:
            return 999
        
        if self.has_ranger and terrain == self.favored_terrain:
            transport_modifier *= 0.5
        
        if self.has_ranger and self.current_transport == "on_foot":
            return min(base_cost * transport_modifier, 1.0)
        
        return base_cost * transport_modifier
    
    def can_move_to(self, terrain: str) -> bool:
        """Check if enough movement points to enter terrain"""
        cost = self.get_movement_cost(terrain)
        if cost >= 999:
            return False
        return self.movement_points >= cost
    
    def move_to_hex(self, terrain: str):
        """Consume movement points for entering a hex"""
        cost = self.get_movement_cost(terrain)
        if self.can_move_to(terrain):
            self.movement_points -= cost
            self.hours_traveled += (cost / self.max_movement) * 8
            
            # Random supply consumption
            if random.random() < 0.1:
                self.supplies = max(0, self.supplies - 0.1)
            
            return True
        return False
    
    def rest(self):
        """Take a long rest - restore movement and reduce exhaustion"""
        self._update_movement_points()
        self.movement_points = self.max_movement
        self.hours_traveled = 0
        self.days_traveled += 1
        
        if self.exhaustion_level > 0:
            self.exhaustion_level -= 1
        if self.mount_exhaustion > 0:
            self.mount_exhaustion -= 1
        
        self.supplies = max(0, self.supplies - 1)
        self.is_resting = True
    
    def forced_march(self):
        """Add extra movement but risk exhaustion"""
        transport = TRANSPORTATION_MODES[self.current_transport]
        
        if not transport["requires_rest"]:
            return False
        
        if self.hours_traveled >= 8:
            dc = 10 + (self.hours_traveled - 8)
            if random.random() < 0.3:  # Simplified exhaustion check
                if transport["exhaustion_resistant"]:
                    self.mount_exhaustion += 1
                else:
                    self.exhaustion_level += 1
        
        self.movement_points += 2
        self.hours_traveled += 2
        return True
    
    def change_pace(self, new_pace: str):
        """Change travel pace"""
        if new_pace in ["slow", "normal", "fast"]:
            self.current_pace = new_pace
            self._update_movement_points()
    
    def change_transport(self, new_transport: str):
        """Change transportation mode"""
        if new_transport in TRANSPORTATION_MODES:
            self.current_transport = new_transport
            self._update_movement_points()
            return True
        return False
    
    def get_effective_exhaustion(self) -> int:
        """Get the exhaustion that affects the party"""
        transport = TRANSPORTATION_MODES[self.current_transport]
        if transport["exhaustion_resistant"]:
            return self.mount_exhaustion
        return self.exhaustion_level
    
    def resupply(self, days: int):
        """Add supplies"""
        self.supplies = min(30, self.supplies + days)
    
    def toggle_ranger(self):
        """Toggle ranger in party"""
        self.has_ranger = not self.has_ranger
    
    def toggle_navigator(self):
        """Toggle navigator/cartographer in party"""
        self.has_navigator = not self.has_navigator
        self._update_movement_points()
    
    def toggle_outlander(self):
        """Toggle outlander background"""
        self.has_outlander = not self.has_outlander
    
    def set_favored_terrain(self, terrain: str):
        """Set ranger's favored terrain"""
        if terrain in TERRAIN_TYPES or terrain is None:
            self.favored_terrain = terrain
    
    def get_save_data(self) -> dict:
        """Get travel system data for saving"""
        return {
            "days": self.days_traveled,
            "hours": self.hours_traveled,
            "movement": self.movement_points,
            "pace": self.current_pace,
            "exhaustion": self.exhaustion_level,
            "transport": self.current_transport,
            "supplies": self.supplies,
            "mount_exhaustion": self.mount_exhaustion,
            "has_ranger": self.has_ranger,
            "has_navigator": self.has_navigator,
            "has_outlander": self.has_outlander,
            "favored_terrain": self.favored_terrain
        }
    
    def load_from_data(self, data: dict):
        """Load travel system data"""
        self.days_traveled = data.get("days", 0)
        self.hours_traveled = data.get("hours", 0)
        self.movement_points = data.get("movement", 8)
        self.current_pace = data.get("pace", "normal")
        self.exhaustion_level = data.get("exhaustion", 0)
        self.current_transport = data.get("transport", "on_foot")
        self.supplies = data.get("supplies", 10)
        self.mount_exhaustion = data.get("mount_exhaustion", 0)
        self.has_ranger = data.get("has_ranger", False)
        self.has_navigator = data.get("has_navigator", False)
        self.has_outlander = data.get("has_outlander", False)
        self.favored_terrain = data.get("favored_terrain", None)
        self._update_movement_points()
