"""
Minecraft-style 6D biome generation system adapted for hex coordinates
"""
import math
from typing import Dict, Tuple, List
from dataclasses import dataclass


@dataclass
class BiomeParameters:
    """6D parameters used for biome selection"""
    temperature: float      # -1.0 to 1.0
    humidity: float        # -1.0 to 1.0  
    continentalness: float # -1.0 to 1.0 (ocean to inland)
    erosion: float         # -1.0 to 1.0 (mountainous to flat)
    weirdness: float       # -1.0 to 1.0 (normal to weird)
    depth: float           # 0.0+ (surface level, increases underground)


@dataclass
class Continent:
    """Represents a single continent in the world"""
    center_q: int          # Q coordinate of continent center
    center_r: int          # R coordinate of continent center  
    center_s: int          # S coordinate of continent center
    radius: int            # Radius of continent in hexes
    coastal_zone: int      # Size of coastal transition zone
    continent_id: str      # Unique identifier (main, north, south, etc.)


class MinecraftBiomeGenerator:
    """Generates biomes using Minecraft's 6D parameter system"""
    
    def __init__(self, seed: int = None):
        self.seed = seed or 12345
        
        # Parse seed for multi-continent configuration
        seed_str = str(abs(self.seed)).ljust(8, '0')  # Ensure 8 digits
        
        # Extract continent configuration from different parts of seed
        main_size_digits = int(seed_str[:4])  # First 4: main continent size
        num_continents_digit = int(seed_str[4:6]) % 5 + 2  # Digits 5-6: 2-6 continents
        spacing_digits = int(seed_str[6:8])  # Last 2: spacing pattern
        
        # Calculate main continent size
        main_radius = 50 + (main_size_digits % 8000) // 40  # 50-250 range
        
        # Generate multiple continents
        self.continents = self._generate_continents(main_radius, num_continents_digit, spacing_digits)
        
        print(f"World generation: {len(self.continents)} continents generated")
        for i, continent in enumerate(self.continents):
            print(f"  {continent.continent_id}: center ({continent.center_q},{continent.center_r},{continent.center_s}), radius {continent.radius}")
        
        # Keep old variables for compatibility (use main continent)
        main_continent = self.continents[0]
        self.ocean_boundary = main_continent.radius
        self.coastal_zone = main_continent.coastal_zone
        
        # Define biome intervals in 6D space
        # Each biome has ranges for each parameter
        self.biome_intervals = {
            # Ocean biomes (high continentalness = more inland)
            "water": {
                "temperature": (-1.0, 1.0),
                "humidity": (-1.0, 1.0),
                "continentalness": (-1.0, -0.2),  # Ocean areas
                "erosion": (-1.0, 1.0),
                "weirdness": (-1.0, 1.0),
                "depth": (0.0, 0.1)
            },
            
            # Beach transition zones
            "plains": {
                "temperature": (-0.15, 0.55),
                "humidity": (-0.35, 0.3),
                "continentalness": (-0.2, 0.1),  # Coastal areas
                "erosion": (0.2, 1.0),  # Flat areas
                "weirdness": (-1.0, 0.0),
                "depth": (0.0, 0.1)
            },
            
            # Cold biomes
            "tundra": {
                "temperature": (-1.0, -0.45),  # Very cold
                "humidity": (-1.0, 0.1),
                "continentalness": (0.0, 1.0),  # Inland
                "erosion": (-1.0, 1.0),
                "weirdness": (-1.0, 1.0),
                "depth": (0.0, 0.1)
            },
            
            # Hot dry biomes
            "desert": {
                "temperature": (0.2, 1.0),     # Hot
                "humidity": (-1.0, -0.1),      # Dry
                "continentalness": (0.1, 1.0), # Inland
                "erosion": (0.0, 1.0),         # Flat to slightly hilly
                "weirdness": (-1.0, 1.0),
                "depth": (0.0, 0.1)
            },
            
            # Temperate humid biomes
            "forest": {
                "temperature": (-0.15, 0.55),  # Temperate
                "humidity": (0.1, 1.0),        # Humid
                "continentalness": (0.1, 1.0), # Inland
                "erosion": (-1.0, 0.2),        # Hilly to flat
                "weirdness": (-1.0, 0.0),
                "depth": (0.0, 0.1)
            },
            
            # Mountainous areas
            "mountains": {
                "temperature": (-0.45, 0.2),   # Cool
                "humidity": (-0.35, 0.3),
                "continentalness": (0.2, 1.0), # Deep inland
                "erosion": (-1.0, -0.2),       # Very hilly/mountainous
                "weirdness": (-1.0, 1.0),
                "depth": (0.0, 0.1)
            },
            
            # Swampy areas
            "swamp": {
                "temperature": (-0.15, 0.55),  # Temperate
                "humidity": (0.3, 1.0),        # Very humid
                "continentalness": (-0.1, 0.3), # Near coast but not ocean
                "erosion": (0.3, 1.0),         # Flat
                "weirdness": (-1.0, 1.0),
                "depth": (0.0, 0.1)
            },
            
            # Rolling hills
            "hills": {
                "temperature": (-0.15, 0.55),  # Temperate
                "humidity": (-0.1, 0.3),
                "continentalness": (0.1, 1.0), # Inland
                "erosion": (-0.2, 0.3),        # Moderately hilly
                "weirdness": (-1.0, 0.0),
                "depth": (0.0, 0.1)
            }
        }
    
    def _generate_continents(self, main_radius: int, num_continents: int, spacing_pattern: int) -> List[Continent]:
        """Generate multiple continents based on seed parameters"""
        continents = []
        
        # Main continent always at center
        continents.append(Continent(
            center_q=0, center_r=0, center_s=0,
            radius=main_radius,
            coastal_zone=max(8, main_radius // 6),
            continent_id="main"
        ))
        
        # Generate additional continents in a ring pattern
        continent_names = ["north", "northeast", "southeast", "south", "southwest", "northwest"]
        
        # Base spacing - distance between continent centers
        base_spacing = main_radius * 2.5 + (spacing_pattern % 50) * 10  # 2.5x main radius + variation
        
        import math
        for i in range(num_continents - 1):  # -1 because we already have main
            if i >= len(continent_names):
                break
                
            # Position continents in a ring around main
            angle = (2 * math.pi * i) / max(1, num_continents - 1)
            
            # Calculate hex coordinates (convert from polar to hex)
            offset_q = int(base_spacing * math.cos(angle))
            offset_r = int(base_spacing * math.sin(angle))
            offset_s = -offset_q - offset_r
            
            # Vary continent sizes (20% to 80% of main continent)
            size_factor = 0.2 + (0.6 * ((spacing_pattern + i * 17) % 100) / 100)
            continent_radius = max(20, int(main_radius * size_factor))
            
            continents.append(Continent(
                center_q=offset_q, center_r=offset_r, center_s=offset_s,
                radius=continent_radius,
                coastal_zone=max(8, continent_radius // 6),
                continent_id=continent_names[i]
            ))
        
        return continents
    
    def get_biome_parameters(self, q: int, r: int, s: int) -> BiomeParameters:
        """Generate 6D biome parameters for hex coordinates"""
        try:
            # Improved coordinate conversion to eliminate vertical lines
            # Mix all three hex coordinates and add rotation for natural distribution
            
            # Simplified coordinate conversion to avoid segfaults
            x = q * 1.7 + r * 0.4  # Simple mixing to break vertical lines
            z = r * 1.8 + q * 0.3  # Different ratios to avoid patterns
            
            # Conservative base scale
            base_scale = 0.05
            
            # Use simple mathematical functions instead of noise library to avoid segfaults
            import math
            
            # Simple pseudo-random functions based on coordinates and seed
            def simple_noise(x, z, seed_offset):
                # Simple deterministic "noise" using sine waves
                val = math.sin(x * 0.1 + seed_offset) * math.cos(z * 0.1 + seed_offset)
                val += math.sin(x * 0.05 + seed_offset * 1.1) * math.cos(z * 0.05 + seed_offset * 1.1) * 0.5
                return self._clamp(val, -1.0, 1.0)
            
            return BiomeParameters(
                temperature=simple_noise(x * 0.6, z * 0.6, self.seed),
                humidity=simple_noise(x * 0.8, z * 0.8, self.seed + 1000),
                continentalness=simple_noise(x * 0.2, z * 0.2, self.seed + 2000),
                erosion=simple_noise(x * 1.1, z * 1.1, self.seed + 3000),
                weirdness=simple_noise(x * 0.9, z * 0.9, self.seed + 4000),
                depth=0.0
            )
        except Exception as e:
            print(f"Error generating biome parameters for hex ({q},{r},{s}): {e}")
            # Return default parameters on error
            return BiomeParameters(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    def hex_distance_from_center(self, q: int, r: int, s: int) -> int:
        """Calculate hex distance from world center (0,0,0)"""
        return max(abs(q), abs(r), abs(s))
    
    def hex_distance_between_points(self, q1: int, r1: int, s1: int, q2: int, r2: int, s2: int) -> int:
        """Calculate hex distance between two points"""
        return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))
    
    def select_biome(self, q: int, r: int, s: int) -> str:
        """Select biome using 6D parameter matching with multi-continent system"""
        try:
            # Check which continent this hex belongs to (if any)
            closest_continent = None
            min_distance_to_continent = float('inf')
            
            for continent in self.continents:
                distance = self.hex_distance_between_points(
                    q, r, s, 
                    continent.center_q, continent.center_r, continent.center_s
                )
                
                # If within this continent's boundary
                if distance <= continent.radius:
                    if distance < min_distance_to_continent:
                        min_distance_to_continent = distance
                        closest_continent = continent
            
            # If not in any continent, return water (ocean)
            if closest_continent is None:
                return "water"
            
            # Generate biome for this continent
            distance_from_continent_center = min_distance_to_continent
            
            # Get biome parameters
            params = self.get_biome_parameters(q, r, s)
            
            # Coastal zone: Modify parameters for realistic coastlines
            if distance_from_continent_center >= (closest_continent.radius - closest_continent.coastal_zone):
                # Increase continentalness decrease toward ocean
                coast_factor = (closest_continent.radius - distance_from_continent_center) / closest_continent.coastal_zone
                params.continentalness = params.continentalness * coast_factor - 0.3
                
                # Make coastal areas more humid and flatter
                params.humidity = min(1.0, params.humidity + 0.2)
                params.erosion = min(1.0, params.erosion + 0.3)
            
            # Find best biome match, with coastal bias
            best_biome = None
            best_distance = float('inf')
            
            # In coastal zones, bias toward water
            if distance_from_continent_center >= (closest_continent.radius - closest_continent.coastal_zone):
                if params.continentalness < -0.1:  # Very low continentalness = water
                    return "water"
            
            # Find closest biome in 6D space
            for biome, intervals in self.biome_intervals.items():
                distance_to_biome = self._calculate_distance(params, intervals)
                
                if distance_to_biome < best_distance:
                    best_distance = distance_to_biome
                    best_biome = biome
            
            return best_biome or "plains"  # Fallback
        except Exception as e:
            print(f"Error selecting biome for hex ({q},{r},{s}): {e}")
            return "plains"  # Safe fallback
    
    def _calculate_distance(self, params: BiomeParameters, intervals: Dict) -> float:
        """Calculate 6D distance from parameters to biome intervals"""
        total_distance = 0.0
        
        # For each parameter, calculate distance to interval
        param_dict = {
            'temperature': params.temperature,
            'humidity': params.humidity,
            'continentalness': params.continentalness,
            'erosion': params.erosion,
            'weirdness': params.weirdness,
            'depth': params.depth
        }
        
        for param_name, value in param_dict.items():
            min_val, max_val = intervals[param_name]
            
            if value < min_val:
                distance = min_val - value
            elif value > max_val:
                distance = value - max_val
            else:
                distance = 0.0  # Inside interval
            
            total_distance += distance * distance
        
        return math.sqrt(total_distance)
    
    @staticmethod
    def _clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range"""
        return max(min_val, min(max_val, value))