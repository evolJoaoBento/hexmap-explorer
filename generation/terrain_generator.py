"""
Advanced terrain generation with realistic features
"""
import random
import math
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import noise


class TerrainType(Enum):
    """Terrain types with generation properties"""
    DEEP_OCEAN = "deep_ocean"
    OCEAN = "ocean" 
    SHALLOW_WATER = "shallow_water"
    BEACH = "beach"
    PLAINS = "plains"
    FOREST = "forest"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    HIGH_MOUNTAINS = "high_mountains"
    DESERT = "desert"
    SAVANNA = "savanna"
    JUNGLE = "jungle"
    SWAMP = "swamp"
    TUNDRA = "tundra"
    ICE = "ice"
    LAKE = "lake"
    RIVER = "river"
    
    
@dataclass
class TerrainProperties:
    """Properties for each terrain type"""
    color: Tuple[int, int, int]
    movement_cost: float
    description: str
    elevation_range: Tuple[float, float]  # Min, max elevation
    moisture_range: Tuple[float, float]  # Min, max moisture
    temperature_range: Tuple[float, float]  # Min, max temperature


# Terrain properties with realistic values
TERRAIN_PROPERTIES = {
    TerrainType.DEEP_OCEAN: TerrainProperties(
        color=(0, 43, 127), movement_cost=999, description="Deep ocean waters",
        elevation_range=(-1.0, -0.5), moisture_range=(0.8, 1.0), temperature_range=(-1.0, 1.0)
    ),
    TerrainType.OCEAN: TerrainProperties(
        color=(0, 89, 179), movement_cost=999, description="Ocean waters", 
        elevation_range=(-0.5, -0.2), moisture_range=(0.8, 1.0), temperature_range=(-1.0, 1.0)
    ),
    TerrainType.SHALLOW_WATER: TerrainProperties(
        color=(65, 105, 225), movement_cost=4, description="Shallow coastal waters",
        elevation_range=(-0.2, -0.05), moisture_range=(0.7, 1.0), temperature_range=(-1.0, 1.0)
    ),
    TerrainType.BEACH: TerrainProperties(
        color=(238, 214, 175), movement_cost=1.2, description="Sandy beach",
        elevation_range=(-0.05, 0.05), moisture_range=(0.3, 0.6), temperature_range=(0.2, 1.0)
    ),
    TerrainType.PLAINS: TerrainProperties(
        color=(144, 238, 144), movement_cost=1, description="Open grasslands",
        elevation_range=(0.05, 0.3), moisture_range=(0.2, 0.5), temperature_range=(0.2, 0.8)
    ),
    TerrainType.FOREST: TerrainProperties(
        color=(34, 139, 34), movement_cost=1.5, description="Dense woodland",
        elevation_range=(0.1, 0.5), moisture_range=(0.4, 0.8), temperature_range=(0.3, 0.7)
    ),
    TerrainType.HILLS: TerrainProperties(
        color=(160, 82, 45), movement_cost=1.5, description="Rolling hills",
        elevation_range=(0.3, 0.6), moisture_range=(0.2, 0.6), temperature_range=(0.1, 0.8)
    ),
    TerrainType.MOUNTAINS: TerrainProperties(
        color=(139, 137, 137), movement_cost=3, description="Rocky peaks",
        elevation_range=(0.6, 0.85), moisture_range=(0.1, 0.5), temperature_range=(-0.2, 0.6)
    ),
    TerrainType.HIGH_MOUNTAINS: TerrainProperties(
        color=(255, 255, 255), movement_cost=999, description="Impassable peaks",
        elevation_range=(0.85, 1.0), moisture_range=(0.0, 0.3), temperature_range=(-1.0, 0.2)
    ),
    TerrainType.DESERT: TerrainProperties(
        color=(238, 203, 173), movement_cost=2, description="Sandy dunes",
        elevation_range=(0.05, 0.4), moisture_range=(0.0, 0.2), temperature_range=(0.6, 1.0)
    ),
    TerrainType.SAVANNA: TerrainProperties(
        color=(196, 198, 93), movement_cost=1.2, description="Dry grasslands",
        elevation_range=(0.05, 0.3), moisture_range=(0.2, 0.4), temperature_range=(0.6, 0.9)
    ),
    TerrainType.JUNGLE: TerrainProperties(
        color=(0, 100, 0), movement_cost=2, description="Dense tropical forest",
        elevation_range=(0.05, 0.4), moisture_range=(0.7, 1.0), temperature_range=(0.7, 1.0)
    ),
    TerrainType.SWAMP: TerrainProperties(
        color=(47, 79, 79), movement_cost=3, description="Murky wetlands",
        elevation_range=(0.0, 0.2), moisture_range=(0.6, 1.0), temperature_range=(0.4, 0.8)
    ),
    TerrainType.TUNDRA: TerrainProperties(
        color=(176, 224, 230), movement_cost=2, description="Frozen wasteland",
        elevation_range=(0.05, 0.4), moisture_range=(0.2, 0.5), temperature_range=(-0.8, 0.0)
    ),
    TerrainType.ICE: TerrainProperties(
        color=(240, 255, 255), movement_cost=2.5, description="Permanent ice",
        elevation_range=(0.0, 1.0), moisture_range=(0.3, 0.7), temperature_range=(-1.0, -0.6)
    ),
    TerrainType.LAKE: TerrainProperties(
        color=(100, 149, 237), movement_cost=999, description="Freshwater lake",
        elevation_range=(0.1, 0.6), moisture_range=(0.8, 1.0), temperature_range=(-0.5, 0.9)
    ),
    TerrainType.RIVER: TerrainProperties(
        color=(70, 130, 180), movement_cost=2, description="Flowing river",
        elevation_range=(0.0, 0.8), moisture_range=(0.7, 1.0), temperature_range=(-0.5, 0.9)
    ),
}


class TerrainGenerator:
    """Advanced terrain generator using multiple noise layers"""
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed else random.randint(0, 1000000)
        random.seed(self.seed)
        
        # Different seeds for different noise layers
        self.elevation_seed = self.seed
        self.moisture_seed = self.seed + 1000
        self.temperature_seed = self.seed + 2000
        self.detail_seed = self.seed + 3000
        
        # Test noise library functionality
        self._test_noise_library()
        
        # Generation parameters
        self.scale = 0.015  # Base scale for noise
        self.octaves = 6  # Number of noise layers
        self.persistence = 0.5  # How much each octave contributes
        self.lacunarity = 2.0  # Frequency multiplier between octaves
        
        # Water bodies tracking
        self.lakes: List[Tuple[int, int, int]] = []
        self.rivers: List[List[Tuple[int, int, int]]] = []
    
    def _test_noise_library(self):
        """Test if noise library works without hanging"""
        try:
            print("Testing noise library...")
            # Simple test that shouldn't hang
            test_value = noise.pnoise2(1.0, 1.0, octaves=1, persistence=0.5, lacunarity=2.0, base=0)
            print(f"Noise library test successful: {test_value}")
        except Exception as e:
            print(f"Noise library test failed: {e}")
            raise Exception(f"Noise library not working: {e}")
        
    def get_elevation(self, x: float, y: float) -> float:
        """Get elevation at a point using layered Perlin noise"""
        # Continental shelf - large scale features
        continental = noise.pnoise2(
            x * self.scale * 0.3, 
            y * self.scale * 0.3,
            octaves=4,
            persistence=0.5,
            lacunarity=2.0,
            base=self.elevation_seed
        )
        
        # Mountain ranges - medium scale
        mountains = noise.pnoise2(
            x * self.scale * 1.5,
            y * self.scale * 1.5, 
            octaves=6,
            persistence=0.7,
            lacunarity=2.5,
            base=self.elevation_seed + 100
        )
        
        # Fine detail
        detail = noise.pnoise2(
            x * self.scale * 5,
            y * self.scale * 5,
            octaves=2,
            persistence=0.3,
            lacunarity=3.0,
            base=self.detail_seed
        )
        
        # Combine layers with adjusted weights
        elevation = (continental * 0.7 + mountains * 0.25 + detail * 0.05)
        
        # Create more pronounced continents and oceans
        # Shift elevation to create more land
        elevation = elevation * 1.2 + 0.1
        
        # Apply gentle falloff at map edges for island-like continents
        distance_from_center = math.sqrt(x**2 + y**2) / 150
        if distance_from_center > 0.7:
            elevation -= (distance_from_center - 0.7) * 0.3
            
        # Normalize to -1 to 1 range
        return max(-1.0, min(1.0, elevation))
    
    def get_moisture(self, x: float, y: float, elevation: float) -> float:
        """Get moisture level based on position and elevation"""
        base_moisture = noise.pnoise2(
            x * self.scale * 1.5,
            y * self.scale * 1.5,
            octaves=4,
            persistence=0.6,
            lacunarity=2.0,
            base=self.moisture_seed
        )
        
        # Higher elevation = less moisture
        elevation_modifier = max(0, 1 - elevation * 1.5)
        
        # Coastal areas have more moisture
        if -0.1 < elevation < 0.1:
            elevation_modifier += 0.3
            
        moisture = base_moisture * 0.7 + elevation_modifier * 0.3
        return max(0.0, min(1.0, (moisture + 1) / 2))
    
    def get_temperature(self, x: float, y: float, elevation: float) -> float:
        """Get temperature based on latitude and elevation"""
        # Latitude effect (y-axis represents north-south)
        # Create more pronounced temperature zones
        latitude = abs(y / 30)  # Scale for map size
        if latitude < 0.3:  # Equatorial zone
            latitude_temp = 0.9
        elif latitude < 0.6:  # Temperate zone
            latitude_temp = 0.5 - (latitude - 0.3) * 1.5
        else:  # Arctic zone
            latitude_temp = -0.2 - (latitude - 0.6) * 2.0
        
        # Add some noise for variation
        temp_noise = noise.pnoise2(
            x * self.scale * 0.5,
            y * self.scale * 0.5,
            octaves=3,
            persistence=0.4,
            lacunarity=2.0,
            base=self.temperature_seed
        )
        
        # Higher elevation = colder
        elevation_modifier = -max(0, elevation) * 0.6
        
        temperature = latitude_temp + (temp_noise * 0.3) + elevation_modifier
        return max(-1.0, min(1.0, temperature))
    
    def determine_terrain(self, elevation: float, moisture: float, temperature: float) -> TerrainType:
        """Determine terrain type based on environmental factors"""
        
        # Water terrains based on elevation
        if elevation < -0.5:
            return TerrainType.DEEP_OCEAN
        elif elevation < -0.2:
            return TerrainType.OCEAN
        elif elevation < -0.05:
            return TerrainType.SHALLOW_WATER
        elif elevation < 0.05:
            # Beach/coastal area
            if temperature < -0.5:
                return TerrainType.TUNDRA
            elif moisture > 0.7:
                return TerrainType.SWAMP
            else:
                return TerrainType.BEACH
                
        # Land terrains based on elevation, moisture, and temperature
        if elevation > 0.85:
            return TerrainType.HIGH_MOUNTAINS
        elif elevation > 0.6:
            if temperature < -0.3:
                return TerrainType.HIGH_MOUNTAINS
            else:
                return TerrainType.MOUNTAINS
        elif elevation > 0.3:
            # Hills and highlands
            if temperature < -0.5:
                return TerrainType.TUNDRA
            elif temperature < 0.0:
                if moisture > 0.5:
                    return TerrainType.FOREST
                else:
                    return TerrainType.HILLS
            elif moisture < 0.3:
                return TerrainType.DESERT
            elif moisture > 0.6:
                return TerrainType.FOREST
            else:
                return TerrainType.HILLS
        else:
            # Lowlands
            if temperature < -0.7:
                return TerrainType.ICE
            elif temperature < -0.3:
                return TerrainType.TUNDRA
            elif temperature < 0.3:
                # Temperate zone
                if moisture < 0.2:
                    return TerrainType.PLAINS
                elif moisture < 0.5:
                    return TerrainType.PLAINS
                elif moisture < 0.8:
                    return TerrainType.FOREST
                else:
                    return TerrainType.SWAMP
            else:
                # Warm/tropical zone
                if moisture < 0.2:
                    return TerrainType.DESERT
                elif moisture < 0.4:
                    return TerrainType.SAVANNA
                elif moisture < 0.7:
                    return TerrainType.SAVANNA
                elif moisture < 0.9:
                    return TerrainType.JUNGLE
                else:
                    return TerrainType.SWAMP
    
    def generate_terrain(self, q: int, r: int, s: int) -> Tuple[str, Dict]:
        """Generate terrain for a hex coordinate"""
        # Convert hex to cartesian for noise functions
        x = q + r * 0.5
        y = r * 0.866  # sqrt(3)/2
        
        # Get environmental values
        elevation = self.get_elevation(x, y)
        moisture = self.get_moisture(x, y, elevation)
        temperature = self.get_temperature(x, y, elevation)
        
        # Determine terrain type
        terrain_type = self.determine_terrain(elevation, moisture, temperature)
        
        # Check for lakes (depressions in land)
        if 0.1 < elevation < 0.4 and moisture > 0.8 and random.random() < 0.1:
            terrain_type = TerrainType.LAKE
            self.lakes.append((q, r, s))
            
        # Check for rivers (following elevation gradients)
        if 0.05 < elevation < 0.6 and moisture > 0.6 and random.random() < 0.05:
            terrain_type = TerrainType.RIVER
            
        # Get properties
        props = TERRAIN_PROPERTIES[terrain_type]
        
        # Convert to legacy format
        terrain_data = {
            "terrain": terrain_type.value,
            "color": props.color,
            "movement_cost": props.movement_cost,
            "description": props.description,
            "elevation": elevation,
            "moisture": moisture, 
            "temperature": temperature
        }
        
        return terrain_type.value, terrain_data
    
    def smooth_terrain_transitions(self, hexes: Dict[Tuple[int, int, int], any]) -> None:
        """Apply smoothing to ensure realistic transitions between biomes"""
        # This would be called after initial generation to smooth harsh transitions
        # For now, the noise-based generation should create smooth transitions naturally
        pass
    
    def generate_river(self, start_q: int, start_r: int, start_s: int, 
                      hexes: Dict[Tuple[int, int, int], any]) -> List[Tuple[int, int, int]]:
        """Generate a river flowing from high to low elevation"""
        river_path = [(start_q, start_r, start_s)]
        current = (start_q, start_r, start_s)
        
        # Rivers flow downhill until they reach water or edge of map
        max_length = 50
        for _ in range(max_length):
            neighbors = self.get_neighbors(*current)
            
            # Find lowest neighbor
            lowest = None
            lowest_elevation = float('inf')
            
            for neighbor in neighbors:
                if neighbor in hexes:
                    hex_data = hexes[neighbor]
                    if hasattr(hex_data, 'elevation'):
                        if hex_data.elevation < lowest_elevation:
                            lowest_elevation = hex_data.elevation
                            lowest = neighbor
                            
            if lowest and lowest not in river_path:
                river_path.append(lowest)
                current = lowest
                
                # Stop if we reach water
                if lowest in hexes:
                    terrain = hexes[lowest].terrain if hasattr(hexes[lowest], 'terrain') else None
                    if terrain in ['ocean', 'deep_ocean', 'lake', 'shallow_water']:
                        break
            else:
                break
                
        return river_path
    
    def get_neighbors(self, q: int, r: int, s: int) -> List[Tuple[int, int, int]]:
        """Get neighboring hex coordinates"""
        return [
            (q+1, r, s-1), (q+1, r-1, s), (q, r-1, s+1),
            (q-1, r, s+1), (q-1, r+1, s), (q, r+1, s-1)
        ]


# Compatibility function for existing code
def create_terrain_generator(seed: Optional[int] = None) -> TerrainGenerator:
    """Create a terrain generator instance"""
    return TerrainGenerator(seed)