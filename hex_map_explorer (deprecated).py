import pygame
import json
import math
import random
import requests
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Set
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
from enum import Enum

# Hex terrain types with movement costs
TERRAIN_TYPES = {
    "forest": {"color": (34, 139, 34), "description": "Dense woodland", "movement_cost": 2},
    "plains": {"color": (144, 238, 144), "description": "Open grasslands", "movement_cost": 1},
    "mountains": {"color": (139, 137, 137), "description": "Rocky peaks", "movement_cost": 3},
    "water": {"color": (65, 105, 225), "description": "Deep waters", "movement_cost": 4},
    "desert": {"color": (238, 203, 173), "description": "Sandy dunes", "movement_cost": 2},
    "swamp": {"color": (47, 79, 79), "description": "Murky wetlands", "movement_cost": 3},
    "tundra": {"color": (176, 224, 230), "description": "Frozen wasteland", "movement_cost": 2},
    "hills": {"color": (160, 82, 45), "description": "Rolling hills", "movement_cost": 1.5}
}

# Travel pace settings (3-mile hexes)
TRAVEL_PACE = {
    "slow": {"hexes_per_8h": 6, "name": "Slow", "exhaustion_free_hours": 8},
    "normal": {"hexes_per_8h": 8, "name": "Normal", "exhaustion_free_hours": 8},
    "fast": {"hexes_per_8h": 10, "name": "Fast", "exhaustion_free_hours": 8}
}

# Transportation modes with their properties
TRANSPORTATION_MODES = {
    "on_foot": {
        "name": "On Foot",
        "icon": "👟",
        "base_hexes_per_8h": {"slow": 6, "normal": 8, "fast": 10},
        "terrain_modifiers": {
            "forest": 1.0, "plains": 1.0, "mountains": 1.0, "water": 999,
            "desert": 1.0, "swamp": 1.0, "tundra": 1.0, "hills": 1.0
        },
        "exhaustion_resistant": False,
        "requires_rest": True,
        "description": "Standard travel by foot"
    },
    "horse": {
        "name": "Horse",
        "icon": "🐴",
        "base_hexes_per_8h": {"slow": 9, "normal": 12, "fast": 15},
        "terrain_modifiers": {
            "forest": 1.2, "plains": 0.8, "mountains": 1.5, "water": 999,
            "desert": 1.1, "swamp": 2.0, "tundra": 1.2, "hills": 0.9
        },
        "exhaustion_resistant": True,
        "requires_rest": True,
        "description": "Mounted on horseback - faster on open terrain"
    },
    "boat": {
        "name": "Boat/Ship",
        "icon": "⛵",
        "base_hexes_per_8h": {"slow": 8, "normal": 12, "fast": 16},
        "terrain_modifiers": {
            "forest": 999, "plains": 999, "mountains": 999, "water": 0.5,
            "desert": 999, "swamp": 2.0, "tundra": 999, "hills": 999
        },
        "exhaustion_resistant": True,
        "requires_rest": False,
        "description": "Water travel - can only traverse water and swamps"
    },
    "airship": {
        "name": "Airship",
        "icon": "🎈",
        "base_hexes_per_8h": {"slow": 12, "normal": 20, "fast": 28},
        "terrain_modifiers": {
            "forest": 0.8, "plains": 0.8, "mountains": 1.0, "water": 0.8,
            "desert": 0.9, "swamp": 0.8, "tundra": 1.1, "hills": 0.85
        },
        "exhaustion_resistant": True,
        "requires_rest": False,
        "description": "Magical flight - ignores most terrain obstacles"
    }
}

@dataclass
class Hex:
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
        data = asdict(self)
        data.pop('generating', None)
        data.pop('distance_from_current', None)
        return data
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data, generating=False, distance_from_current=999)

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
            if random.random() < 0.3:
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

class PixelArtSprites:
    """Manages pixel art sprites for campfire, scouting, and adventurer"""
    
    def __init__(self):
        self.adventurer_frame = 0
        self.adventurer_timer = 0
        self.scout_frame = 0
        self.scout_timer = 0
        self.campfire_stages = self.create_campfire_stages()
        self.adventurer_sprites = self.create_adventurer_sprites()
        self.campfire_scenes = self.create_campfire_scenes()
        self.scout_scenes = self.create_scout_scenes()
    
    def create_campfire_stages(self) -> List[pygame.Surface]:
        """Create 6 stages of campfire from bright to dim"""
        stages = []
        size = 32
        
        for stage in range(6):
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            brightness = 1.0 - (stage * 0.15)
            
            log_color = (101, 67, 33)
            pygame.draw.rect(surface, log_color, (10, 20, 12, 3))
            pygame.draw.rect(surface, log_color, (8, 23, 16, 3))
            
            if stage < 5:
                flame_height = int(16 * brightness)
                flame_width = int(12 * brightness)
                
                if brightness > 0.3:
                    outer_color = (255, int(100 * brightness), 0)
                    for i in range(flame_height):
                        width = flame_width - (i * flame_width // flame_height)
                        if width > 0:
                            y_pos = 20 - i
                            x_pos = 16 - width // 2
                            pygame.draw.rect(surface, outer_color, (x_pos, y_pos, width, 1))
                
                if brightness > 0.5:
                    inner_height = int(flame_height * 0.6)
                    inner_color = (255, 255, int(200 * brightness))
                    for i in range(inner_height):
                        width = (flame_width // 2) - (i * (flame_width // 2) // inner_height)
                        if width > 0:
                            y_pos = 20 - i
                            x_pos = 16 - width // 2
                            pygame.draw.rect(surface, inner_color, (x_pos, y_pos, width, 1))
            
            stages.append(surface)
        return stages
    
    def create_scout_scenes(self) -> List[pygame.Surface]:
        """Create scouting animation frames"""
        scenes = []
        scene_width = 80
        scene_height = 40
        
        for frame in range(4):
            surface = pygame.Surface((scene_width, scene_height), pygame.SRCALPHA)
            
            warrior_x = 40
            warrior_y = 15
            
            armor_color = (160, 160, 170)
            armor_dark = (120, 120, 130)
            armor_shine = (200, 200, 210)
            
            leg_spread = 2 if frame % 2 == 0 else 3
            pygame.draw.rect(surface, armor_color, (warrior_x - leg_spread, warrior_y + 15, 3, 8))
            pygame.draw.rect(surface, armor_color, (warrior_x + leg_spread - 1, warrior_y + 15, 3, 8))
            
            body_sway = 1 if frame in [1, 2] else 0
            pygame.draw.rect(surface, armor_color, (warrior_x - 2 + body_sway, warrior_y + 7, 6, 9))
            pygame.draw.rect(surface, armor_shine, (warrior_x - 1 + body_sway, warrior_y + 8, 4, 3))
            
            if frame < 3:
                pygame.draw.rect(surface, armor_color, (warrior_x + 3 + body_sway, warrior_y + 7, 2, 4))
                pygame.draw.rect(surface, armor_color, (warrior_x + 4 + body_sway, warrior_y + 3, 2, 5))
                pygame.draw.rect(surface, armor_dark, (warrior_x + 3 + body_sway, warrior_y + 2, 3, 2))
            else:
                pygame.draw.rect(surface, armor_color, (warrior_x + 3 + body_sway, warrior_y + 7, 2, 5))
                pygame.draw.rect(surface, armor_color, (warrior_x + 5 + body_sway, warrior_y + 9, 4, 2))
                surface.set_at((warrior_x + 9 + body_sway, warrior_y + 10), armor_dark)
            
            pygame.draw.rect(surface, armor_color, (warrior_x - 4 + body_sway, warrior_y + 7, 2, 6))
            pygame.draw.rect(surface, armor_shine, (warrior_x - 1 + body_sway, warrior_y, 4, 5))
            pygame.draw.rect(surface, (10, 10, 10), (warrior_x - 1 + body_sway, warrior_y + 2, 4, 1))
            
            grass_color = (50, 100, 50)
            for i in range(0, 80, 3):
                height = 2 + (i + frame) % 3
                pygame.draw.rect(surface, grass_color, (i, 35 - height, 1, height))
            
            if frame % 2 == 0:
                surface.set_at((10 + frame * 5, 5), (0, 0, 0))
                surface.set_at((60 - frame * 3, 8), (0, 0, 0))
            
            for i in range(3):
                pygame.draw.circle(surface, (100, 100, 100), 
                                 (warrior_x - 10 - i * 8, warrior_y + 22), 1)
            
            scenes.append(surface)
        return scenes
    
    def create_campfire_scenes(self) -> List[pygame.Surface]:
        """Create resting campfire scenes with warrior"""
        scenes = []
        scene_width = 80
        scene_height = 40
        
        for stage in range(6):
            surface = pygame.Surface((scene_width, scene_height), pygame.SRCALPHA)
            brightness = 1.0 - (stage * 0.15)
            
            log_color = (101, 67, 33)
            pygame.draw.rect(surface, log_color, (25, 28, 12, 3))
            pygame.draw.rect(surface, log_color, (23, 31, 16, 3))
            
            rock_color = (80, 80, 80)
            pygame.draw.circle(surface, rock_color, (22, 30), 2)
            pygame.draw.circle(surface, rock_color, (40, 31), 2)
            
            if stage < 5:
                flame_height = int(14 * brightness)
                flame_width = int(10 * brightness)
                
                if brightness > 0.3:
                    outer_color = (255, int(100 * brightness), 0)
                    for i in range(flame_height):
                        width = flame_width - (i * flame_width // flame_height)
                        if width > 0:
                            y_pos = 28 - i
                            x_pos = 31 - width // 2
                            pygame.draw.rect(surface, outer_color, (x_pos, y_pos, width, 1))
            
            warrior_x = 48
            warrior_y = 25
            
            bedroll_color = (100, 60, 40)
            pygame.draw.rect(surface, bedroll_color, (warrior_x, warrior_y, 15, 6))
            
            armor_color = (140, 140, 150)
            pygame.draw.rect(surface, armor_color, (warrior_x + 2, warrior_y + 1, 10, 4))
            pygame.draw.rect(surface, (170, 170, 180), (warrior_x, warrior_y + 2, 3, 3))
            
            if stage % 2 == 0:
                z_color = (200, 200, 200)
                surface.set_at((warrior_x - 2, warrior_y - 2 - stage), z_color)
                surface.set_at((warrior_x - 1, warrior_y - 3 - stage), z_color)
                surface.set_at((warrior_x, warrior_y - 2 - stage), z_color)
            
            pygame.draw.rect(surface, (140, 140, 150), (warrior_x + 13, warrior_y - 2, 4, 6))
            for i in range(8):
                surface.set_at((warrior_x + 15, warrior_y - 4 + i), (192, 192, 192))
            
            moon_color = (240, 240, 200)
            pygame.draw.circle(surface, moon_color, (65, 8), 4)
            for star_pos in [(10, 5), (30, 3), (50, 6), (70, 4)]:
                surface.set_at(star_pos, (255, 255, 255))
            
            scenes.append(surface)
        return scenes
    
    def create_adventurer_sprites(self) -> List[pygame.Surface]:
        """Create idle animation frames for armored warrior"""
        sprites = []
        size = 24
        
        for frame in range(4):
            surface = pygame.Surface((size, size), pygame.SRCALPHA)
            
            body_offset = 1 if frame in [1, 2] else 0
            armor_color = (140, 140, 150)
            armor_dark = (100, 100, 110)
            
            pygame.draw.rect(surface, armor_color, (9, 10 + body_offset, 6, 8))
            pygame.draw.rect(surface, (160, 160, 170), (10, 11 + body_offset, 4, 3))
            pygame.draw.rect(surface, armor_dark, (9, 14 + body_offset, 6, 1))
            
            pygame.draw.rect(surface, armor_color, (8, 10 + body_offset, 2, 3))
            pygame.draw.rect(surface, armor_color, (14, 10 + body_offset, 2, 3))
            
            pygame.draw.rect(surface, (150, 150, 160), (10, 6 + body_offset, 4, 5))
            pygame.draw.rect(surface, (20, 20, 20), (10, 8 + body_offset, 4, 1))
            pygame.draw.rect(surface, (200, 50, 50), (11, 5 + body_offset, 2, 2))
            
            arm_offset = 1 if frame % 2 == 0 else 0
            pygame.draw.rect(surface, armor_color, (8, 12 + body_offset + arm_offset, 2, 4))
            pygame.draw.rect(surface, armor_color, (14, 12 + body_offset - arm_offset, 2, 4))
            
            pygame.draw.rect(surface, armor_color, (10, 18, 2, 4))
            pygame.draw.rect(surface, armor_color, (12, 18, 2, 4))
            
            for i in range(10):
                surface.set_at((15 + i // 4, 7 + i), (192, 192, 192))
            
            sprites.append(surface)
        
        return sprites
    
    def get_campfire_scene(self, progress: float, total_hexes: int) -> pygame.Surface:
        """Get appropriate campfire scene for resting"""
        if total_hexes <= 0:
            return self.campfire_scenes[-1]
        
        stage_index = int(progress * 5)
        stage_index = max(0, min(5, stage_index))
        
        if total_hexes < 6:
            initial_stage = 6 - total_hexes
            stage_index = min(5, stage_index + initial_stage)
        
        return self.campfire_scenes[stage_index]
    
    def get_scout_scene(self, progress: float) -> pygame.Surface:
        """Get scouting animation frame"""
        frame_index = int((progress * 10) % 4)
        return self.scout_scenes[frame_index]
    
    def update_adventurer(self, dt: float):
        """Update adventurer animation"""
        self.adventurer_timer += dt
        if self.adventurer_timer >= 0.3:
            self.adventurer_timer = 0
            self.adventurer_frame = (self.adventurer_frame + 1) % 4
    
    def update_scout(self, dt: float):
        """Update scout animation"""
        self.scout_timer += dt
        if self.scout_timer >= 0.25:
            self.scout_timer = 0
            self.scout_frame = (self.scout_frame + 1) % 4
    
    def get_adventurer_sprite(self) -> pygame.Surface:
        """Get current adventurer sprite"""
        return self.adventurer_sprites[self.adventurer_frame]

class OllamaClient:
    """Client for Ollama API with synchronous generation"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:3b"
        self.description_cache = {}
        self.session = requests.Session()
        self.ollama_available = self.check_ollama()
    
    def check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except:
            print("Ollama not detected - using fallback descriptions")
            return False
    
    def generate(self, terrain: str, coords: Tuple[int, int]) -> str:
        """Generate description synchronously"""
        cache_key = f"{terrain}_{coords[0]}_{coords[1]}"
        
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]
        
        if not self.ollama_available:
            return self.get_fallback_description(terrain)
        
        prompt = f"""Generate a brief, evocative description (2-3 sentences) for a hex tile in a fantasy map. 
        The terrain is: {terrain} ({TERRAIN_TYPES[terrain]['description']}).
        Location: hex coordinates ({coords[0]}, {coords[1]}).
        Make it atmospheric and hint at potential discoveries or dangers.
        Description:"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 50,
                        "temperature": 0.7,
                        "top_k": 30,
                        "top_p": 0.85
                    }
                },
                timeout=10
            )
            if response.status_code == 200:
                description = response.json().get("response", "").strip()
                if description:
                    self.description_cache[cache_key] = description
                    return description
        except Exception as e:
            print(f"Generation error: {e}")
            self.ollama_available = False
        
        return self.get_fallback_description(terrain)
    
    def get_fallback_description(self, terrain: str) -> str:
        """Fallback descriptions by terrain type"""
        fallbacks = {
            "forest": [
                "Ancient trees tower overhead, their branches creating a verdant canopy. The air is thick with the scent of moss and decay.",
                "The forest whispers with unseen life and hidden paths. Shadows dance between the massive trunks."
            ],
            "plains": [
                "Endless grasslands ripple in the wind like a golden sea. The horizon seems infinitely distant.",
                "The open plains stretch to the horizon under vast skies. Wild flowers dot the landscape."
            ],
            "mountains": [
                "Jagged peaks pierce the clouds, eternal and imposing. The air grows thin and cold.",
                "Rocky cliffs and steep paths challenge any traveler. Eagles circle overhead."
            ],
            "water": [
                "Deep waters reflect the sky, hiding depths unknown. Gentle waves lap at unseen shores.",
                "The water's surface conceals aquatic mysteries. Strange ripples disturb the calm."
            ],
            "desert": [
                "Sand dunes shift endlessly under the scorching sun. Mirages dance on the horizon.",
                "The desert's harsh beauty masks hidden oases. Wind-carved rocks create natural sculptures."
            ],
            "swamp": [
                "Murky waters and twisted trees create an eerie landscape. Strange bubbles rise from the depths.",
                "The swamp bubbles with mysterious life and decay. Fog drifts between gnarled roots."
            ],
            "tundra": [
                "Frozen wastes stretch endlessly, beautiful and desolate. The wind cuts like ice.",
                "Ice and snow dominate this harsh, unforgiving land. Aurora lights dance overhead."
            ],
            "hills": [
                "Rolling hills create a patchwork of light and shadow. Ancient paths wind between them.",
                "Gentle slopes hide valleys and ancient secrets. Wildflowers carpet the hillsides."
            ]
        }
        return random.choice(fallbacks.get(terrain, ["An unexplored region awaits discovery."]))
    
    def cleanup(self):
        """Cleanup session"""
        self.session.close()

class GenerationManager:
    """Manages description generation with progress tracking"""
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.generating = False
        self.progress = 0.0
        self.total_hexes = 0
        self.completed_hexes = 0
        self.current_hex_name = ""
        self.generation_thread = None
        self.hexes_to_generate = []
        self.cancel_generation = False
        self.generation_type = "scouting"
    
    def start_generation(self, hexes: List[Tuple[Hex, Tuple[int, int]]], gen_type: str = "scouting"):
        """Start generating descriptions for a list of hexes"""
        if self.generating:
            return
        
        self.hexes_to_generate = hexes
        self.total_hexes = len(hexes)
        self.completed_hexes = 0
        self.progress = 0.0
        self.generating = True
        self.cancel_generation = False
        self.generation_type = gen_type
        
        self.generation_thread = threading.Thread(target=self._generate_worker, daemon=True)
        self.generation_thread.start()
    
    def _generate_worker(self):
        """Worker thread for generation"""
        for hex_obj, coords in self.hexes_to_generate:
            if self.cancel_generation:
                break
            
            self.current_hex_name = f"{hex_obj.terrain} at ({hex_obj.q}, {hex_obj.r})"
            hex_obj.generating = True
            
            description = self.ollama.generate(hex_obj.terrain, coords)
            hex_obj.description = description
            hex_obj.generating = False
            
            self.completed_hexes += 1
            self.progress = self.completed_hexes / self.total_hexes
            
            if self.ollama.ollama_available:
                time.sleep(0.1)
        
        self.generating = False
        self.progress = 1.0
    
    def cancel(self):
        """Cancel current generation"""
        self.cancel_generation = True
        if self.generation_thread:
            self.generation_thread.join(timeout=1)
        self.generating = False

class HexMap:
    """Hex map with travel system"""
    
    def __init__(self, ollama_client: OllamaClient, generation_manager: GenerationManager):
        self.hexes: Dict[Tuple[int, int, int], Hex] = {}
        self.ollama = ollama_client
        self.gen_manager = generation_manager
        self.current_position = (0, 0, 0)
        self.travel_system = TravelSystem()
    
    def get_neighbors(self, q: int, r: int, s: int) -> List[Tuple[int, int, int]]:
        """Get all 6 neighbors of a hex"""
        directions = [
            (1, 0, -1), (1, -1, 0), (0, -1, 1),
            (-1, 0, 1), (-1, 1, 0), (0, 1, -1)
        ]
        return [(q + dq, r + dr, s + ds) for dq, dr, ds in directions]
    
    def get_hexes_within_radius(self, q: int, r: int, s: int, radius: int) -> List[Tuple[int, int, int]]:
        """Get all hexes within a given radius"""
        hexes = []
        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                ds = -dq - dr
                hexes.append((q + dq, r + dr, s + ds))
        return hexes
    
    def get_adjacent_explored(self, q: int, r: int, s: int) -> List[Tuple[int, int, int]]:
        """Get adjacent hexes that are explored"""
        neighbors = self.get_neighbors(q, r, s)
        explored = []
        for nq, nr, ns in neighbors:
            if (nq, nr, ns) in self.hexes and self.hexes[(nq, nr, ns)].explored:
                explored.append((nq, nr, ns))
        return explored
    
    def calculate_distances(self):
        """Calculate distance from current position to all hexes"""
        curr_q, curr_r, curr_s = self.current_position
        for (q, r, s), hex_obj in self.hexes.items():
            hex_obj.distance_from_current = (abs(q - curr_q) + abs(r - curr_r) + abs(s - curr_s)) // 2
    
    def create_hex(self, q: int, r: int, s: int) -> Hex:
        """Create a hex with placeholder description"""
        neighbors = self.get_neighbors(q, r, s)
        neighbor_terrains = []
        
        for nq, nr, ns in neighbors:
            if (nq, nr, ns) in self.hexes:
                neighbor_terrains.append(self.hexes[(nq, nr, ns)].terrain)
        
        if neighbor_terrains and random.random() < 0.6:
            terrain = random.choice(neighbor_terrains)
        else:
            terrain = random.choice(list(TERRAIN_TYPES.keys()))
        
        return Hex(q, r, s, terrain, "Awaiting description...", generating=True)
    
    def initialize_map(self):
        """Initialize starting area with generation"""
        start_hex = self.create_hex(0, 0, 0)
        start_hex.explored = True
        start_hex.visible = True
        self.hexes[(0, 0, 0)] = start_hex
        
        hexes_to_generate = [(start_hex, (0, 0))]
        
        for q, r, s in self.get_neighbors(0, 0, 0):
            hex_obj = self.create_hex(q, r, s)
            hex_obj.visible = True
            self.hexes[(q, r, s)] = hex_obj
            hexes_to_generate.append((hex_obj, (q, r)))
        
        self.gen_manager.start_generation(hexes_to_generate, "scouting")
    
    def rest_and_scout(self):
        """Rest and reveal hexes within 2-hex radius"""
        self.travel_system.rest()
        
        curr_q, curr_r, curr_s = self.current_position
        hexes_to_generate = []
        
        for q, r, s in self.get_hexes_within_radius(curr_q, curr_r, curr_s, 2):
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
            
            for nq, nr, ns in self.get_neighbors(q, r, s):
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
        
        self.travel_system.move_to_hex(hex_obj.terrain)
        hex_obj.explored = True
        self.current_position = (q, r, s)
        
        hexes_to_generate = []
        for nq, nr, ns in self.get_neighbors(q, r, s):
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
            "travel_data": {
                "days": self.travel_system.days_traveled,
                "hours": self.travel_system.hours_traveled,
                "movement": self.travel_system.movement_points,
                "pace": self.travel_system.current_pace,
                "exhaustion": self.travel_system.exhaustion_level,
                "transport": self.travel_system.current_transport,
                "supplies": self.travel_system.supplies,
                "mount_exhaustion": self.travel_system.mount_exhaustion,
                "has_ranger": self.travel_system.has_ranger,
                "has_navigator": self.travel_system.has_navigator,
                "has_outlander": self.travel_system.has_outlander,
                "favored_terrain": self.travel_system.favored_terrain
            }
        }
        with open(filename, 'w') as f:
            json.dump(map_data, f, indent=2)
    
    def load_from_json(self, filename: str):
        """Load map from JSON file"""
        with open(filename, 'r') as f:
            map_data = json.load(f)
        
        self.hexes.clear()
        self.current_position = tuple(map_data["current_position"])
        
        for hex_data in map_data["hexes"]:
            hex_obj = Hex.from_dict(hex_data)
            self.hexes[(hex_obj.q, hex_obj.r, hex_obj.s)] = hex_obj
        
        if "travel_data" in map_data:
            td = map_data["travel_data"]
            self.travel_system.days_traveled = td.get("days", 0)
            self.travel_system.hours_traveled = td.get("hours", 0)
            self.travel_system.movement_points = td.get("movement", 8)
            self.travel_system.current_pace = td.get("pace", "normal")
            self.travel_system.exhaustion_level = td.get("exhaustion", 0)
            self.travel_system.current_transport = td.get("transport", "on_foot")
            self.travel_system.supplies = td.get("supplies", 10)
            self.travel_system.mount_exhaustion = td.get("mount_exhaustion", 0)
            self.travel_system.has_ranger = td.get("has_ranger", False)
            self.travel_system.has_navigator = td.get("has_navigator", False)
            self.travel_system.has_outlander = td.get("has_outlander", False)
            self.travel_system.favored_terrain = td.get("favored_terrain", None)
            self.travel_system._update_movement_points()

class HexMapRenderer:
    """Renderer with travel UI"""
    
    def __init__(self, screen: pygame.Surface, hex_map: HexMap, gen_manager: GenerationManager):
        self.screen = screen
        self.hex_map = hex_map
        self.gen_manager = gen_manager
        
        screen_size = min(screen.get_width(), screen.get_height())
        self.hex_size = max(20, min(40, int(screen_size * 0.04)))
        
        self.font = pygame.font.Font(None, max(20, min(32, int(screen_size * 0.03))))
        self.small_font = pygame.font.Font(None, max(14, min(20, int(screen_size * 0.02))))
        
        self.selected_hex = None
        self.show_popup = False
        self.sprites = PixelArtSprites()
        self.message = ""
        self.message_timer = 0
        
        # Menu flags
        self.show_transport_menu = False
        self.show_party_menu = False
        
        # Initialize button storage
        self.transport_buttons = {}
        self.transport_menu_buttons = {}
        self.party_menu_buttons = {}
        self.terrain_buttons = []
        
        self.update_hex_vertices()
    
    def update_hex_vertices(self):
        """Update cached hex vertex offsets"""
        self.hex_vertex_offsets = []
        for i in range(6):
            angle = math.pi / 3 * i
            x = self.hex_size * math.cos(angle)
            y = self.hex_size * math.sin(angle)
            self.hex_vertex_offsets.append((x, y))
    
    def hex_to_pixel(self, q: int, r: int) -> Tuple[float, float]:
        """Convert hex to pixel coordinates (relative to current position)"""
        curr_q, curr_r, curr_s = self.hex_map.current_position
        
        rel_q = q - curr_q
        rel_r = r - curr_r
        
        x = self.hex_size * (3/2 * rel_q)
        y = self.hex_size * (math.sqrt(3)/2 * rel_q + math.sqrt(3) * rel_r)
        
        return (x + self.screen.get_width() // 2, y + self.screen.get_height() // 2)
    
    def pixel_to_hex(self, x: float, y: float) -> Tuple[int, int, int]:
        """Convert pixel to hex coordinates"""
        curr_q, curr_r, curr_s = self.hex_map.current_position
        
        x = (x - self.screen.get_width() // 2) / self.hex_size
        y = (y - self.screen.get_height() // 2) / self.hex_size
        
        q = (2/3) * x
        r = (-1/3) * x + (math.sqrt(3)/3) * y
        
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
        
        return (rq + curr_q, rr + curr_r, -rq - rr + curr_s)
    
    def draw_hex(self, q: int, r: int, hex_obj: Hex):
        """Draw a single hexagon"""
        center_x, center_y = self.hex_to_pixel(q, r)
        
        if abs(center_x - self.screen.get_width() // 2) > self.screen.get_width() // 2 + self.hex_size:
            return
        if abs(center_y - self.screen.get_height() // 2) > self.screen.get_height() // 2 + self.hex_size:
            return
        
        points = [(center_x + ox, center_y + oy) for ox, oy in self.hex_vertex_offsets]
        
        color = TERRAIN_TYPES[hex_obj.terrain]["color"]
        if not hex_obj.explored:
            color = tuple(c // 2 for c in color)
        
        if hex_obj.generating:
            pulse = (math.sin(time.time() * 3) + 1) / 2
            color = tuple(int(c * (0.5 + 0.5 * pulse)) for c in color)
        
        pygame.draw.polygon(self.screen, color, points)
        
        if hex_obj.generating:
            border_color = (255, 255, 0)
        elif hex_obj.explored:
            border_color = (255, 255, 255)
        else:
            border_color = (100, 100, 100)
        
        pygame.draw.polygon(self.screen, border_color, points, 2)
        
        if hex_obj.visible and not hex_obj.explored:
            cost = TERRAIN_TYPES[hex_obj.terrain]["movement_cost"]
            cost_text = self.small_font.render(str(int(cost)), True, (255, 255, 255))
            cost_rect = cost_text.get_rect(center=(int(center_x), int(center_y)))
            self.screen.blit(cost_text, cost_rect)
        
        if (q, r, -q-r) == self.hex_map.current_position:
            adventurer = self.sprites.get_adventurer_sprite()
            adventurer_scaled = pygame.transform.scale2x(adventurer)
            adventurer_rect = adventurer_scaled.get_rect(center=(int(center_x), int(center_y)))
            self.screen.blit(adventurer_scaled, adventurer_rect)
    
    def draw_map(self):
        """Draw all visible hexes"""
        for (q, r, s), hex_obj in self.hex_map.hexes.items():
            if hex_obj.visible:
                self.draw_hex(q, r, hex_obj)
    
    def draw_loading_animation(self):
        """Draw loading animation (scouting or resting)"""
        if not self.gen_manager.generating:
            return
        
        bar_width = 450
        bar_height = 120
        bar_x = (self.screen.get_width() - bar_width) // 2
        bar_y = self.screen.get_height() - 140
        
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), bg_rect, 2)
        
        if self.gen_manager.generation_type == "resting":
            title_text = self.font.render("Resting at camp...", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, bar_y + 20))
            self.screen.blit(title_text, title_rect)
            
            scene = self.sprites.get_campfire_scene(self.gen_manager.progress, self.gen_manager.total_hexes)
            scene_scaled = pygame.transform.scale2x(scene)
            scene_rect = scene_scaled.get_rect(center=(self.screen.get_width() // 2, bar_y + 65))
            self.screen.blit(scene_scaled, scene_rect)
        else:
            title_text = self.font.render("Scouting ahead...", True, (255, 255, 255))
            title_rect = title_text.get_rect(center=(self.screen.get_width() // 2, bar_y + 20))
            self.screen.blit(title_text, title_rect)
            
            scene = self.sprites.get_scout_scene(self.gen_manager.progress)
            scene_scaled = pygame.transform.scale2x(scene)
            scene_rect = scene_scaled.get_rect(center=(self.screen.get_width() // 2, bar_y + 65))
            self.screen.blit(scene_scaled, scene_rect)
        
        progress_text = f"{self.gen_manager.completed_hexes}/{self.gen_manager.total_hexes} areas discovered"
        text_surface = self.small_font.render(progress_text, True, (200, 200, 200))
        text_rect = text_surface.get_rect(center=(self.screen.get_width() // 2, bar_y + 105))
        self.screen.blit(text_surface, text_rect)
    
    def draw_travel_ui(self):
        """Draw enhanced travel system UI with transport options"""
        travel = self.hex_map.travel_system
        
        panel_width = 260
        panel_height = 200
        panel_rect = pygame.Rect(10, 50, panel_width, panel_height)
        pygame.draw.rect(self.screen, (40, 40, 40), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 1)
        
        title_text = self.small_font.render("Travel Status", True, (255, 255, 255))
        self.screen.blit(title_text, (15, 55))
        
        transport = TRANSPORTATION_MODES[travel.current_transport]
        transport_text = self.small_font.render(f"Transport: {transport['name']}", True, (200, 200, 255))
        self.screen.blit(transport_text, (15, 75))
        
        hours = int(travel.hours_traveled)
        minutes = int((travel.hours_traveled - hours) * 60)
        time_text = self.small_font.render(f"Day {travel.days_traveled + 1}, Hour {hours}:{minutes:02d}", True, (200, 200, 200))
        self.screen.blit(time_text, (15, 95))
        
        cost_preview = ""
        if self.selected_hex and self.selected_hex in self.hex_map.hexes:
            hex_obj = self.hex_map.hexes[self.selected_hex]
            cost = travel.get_movement_cost(hex_obj.terrain)
            if cost >= 999:
                cost_preview = " (Impassable!)"
            else:
                cost_preview = f" (Next: {cost:.1f})"
        
        mp_color = (0, 255, 0) if travel.movement_points > 2 else (255, 255, 0) if travel.movement_points > 0 else (255, 0, 0)
        mp_text = self.small_font.render(f"Movement: {travel.movement_points:.1f}/{travel.max_movement}{cost_preview}", True, mp_color)
        self.screen.blit(mp_text, (15, 115))
        
        pace_text = self.small_font.render(f"Pace: {travel.current_pace.title()}", True, (200, 200, 200))
        self.screen.blit(pace_text, (15, 135))
        
        supply_color = (0, 255, 0) if travel.supplies > 5 else (255, 255, 0) if travel.supplies > 2 else (255, 0, 0)
        supply_text = self.small_font.render(f"Supplies: {travel.supplies:.1f} days", True, supply_color)
        self.screen.blit(supply_text, (15, 155))
        
        effective_exhaustion = travel.get_effective_exhaustion()
        if effective_exhaustion > 0:
            ex_label = "Mount Exhaustion" if transport["exhaustion_resistant"] else "Exhaustion"
            ex_color = (255, 100, 100)
            ex_text = self.small_font.render(f"{ex_label}: {effective_exhaustion}", True, ex_color)
            self.screen.blit(ex_text, (15, 175))
        
        bonuses_y = 195
        if travel.has_ranger:
            ranger_text = self.small_font.render("✓ Ranger (terrain bonus)", True, (100, 255, 100))
            self.screen.blit(ranger_text, (15, bonuses_y))
            bonuses_y += 18
        if travel.has_navigator:
            nav_text = self.small_font.render("✓ Navigator (+10% speed)", True, (100, 255, 100))
            self.screen.blit(nav_text, (15, bonuses_y))
            bonuses_y += 18
        if travel.has_outlander:
            outlander_text = self.small_font.render("✓ Outlander (never lost)", True, (100, 255, 100))
            self.screen.blit(outlander_text, (15, bonuses_y))
            bonuses_y += 18
        
        # Favored terrain active badge
        current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
        if travel.has_ranger and current_hex and travel.favored_terrain == current_hex.terrain:
            bonus_surf = self.small_font.render("Favored terrain bonus!", True, (100, 255, 100))
            self.screen.blit(bonus_surf, (15, bonuses_y))
            bonuses_y += 18

        # Transport controls panel
        transport_panel_y = 260
        transport_panel_rect = pygame.Rect(10, transport_panel_y, panel_width, 140)
        pygame.draw.rect(self.screen, (40, 40, 40), transport_panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), transport_panel_rect, 1)
        
        transport_title = self.small_font.render("Transportation", True, (255, 255, 255))
        self.screen.blit(transport_title, (15, transport_panel_y + 5))
        
        # Quick transport buttons
        quick_transports = ["on_foot", "horse", "boat", "airship"]
        button_width = 60
        button_height = 25
        for i, trans_key in enumerate(quick_transports):
            if trans_key not in TRANSPORTATION_MODES:
                continue
            trans = TRANSPORTATION_MODES[trans_key]
            x = 15 + (i % 4) * (button_width + 5)
            y = transport_panel_y + 30 + (i // 4) * 30
            
            is_current = travel.current_transport == trans_key
            button_color = (80, 80, 120) if is_current else (60, 60, 80)
            button_rect = pygame.Rect(x, y, button_width, button_height)
            
            can_use = True
            if self.hex_map.current_position in self.hex_map.hexes:
                current_hex = self.hex_map.hexes[self.hex_map.current_position]
                if trans["terrain_modifiers"][current_hex.terrain] >= 999:
                    can_use = False
                    button_color = (80, 40, 40)
            
            pygame.draw.rect(self.screen, button_color, button_rect)
            pygame.draw.rect(self.screen, (150, 150, 150), button_rect, 1)
            
            name = trans_key.replace("_", " ").title()[:7]
            name_text = self.small_font.render(name, True, (255, 255, 255) if can_use else (150, 150, 150))
            text_rect = name_text.get_rect(center=button_rect.center)
            self.screen.blit(name_text, text_rect)
            
            self.transport_buttons[trans_key] = button_rect
        
        more_button_rect = pygame.Rect(15, transport_panel_y + 60, 240, 25)
        pygame.draw.rect(self.screen, (70, 70, 100), more_button_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), more_button_rect, 1)
        more_text = self.small_font.render("More Transport Options (T)", True, (255, 255, 255))
        more_text_rect = more_text.get_rect(center=more_button_rect.center)
        self.screen.blit(more_text, more_text_rect)
        self.more_transport_button = more_button_rect
        
        party_button_rect = pygame.Rect(15, transport_panel_y + 90, 240, 25)
        pygame.draw.rect(self.screen, (70, 100, 70), party_button_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), party_button_rect, 1)
        party_text = self.small_font.render("Party Composition (Y)", True, (255, 255, 255))
        party_text_rect = party_text.get_rect(center=party_button_rect.center)
        self.screen.blit(party_text, party_text_rect)
        self.party_button = party_button_rect
        
        controls = [
            "R: Rest | P: Pace | F: Force",
            "T: Transport | Y: Party",
            "S: Resupply (in town)"
        ]
        y_pos = transport_panel_y + 120
        for control in controls:
            text = self.small_font.render(control, True, (150, 150, 150))
            self.screen.blit(text, (15, y_pos))
            y_pos += 18
        
        # Menu button (bottom right corner)
        menu_button_width = 100
        menu_button_height = 30
        menu_x = self.screen.get_width() - menu_button_width - 10
        menu_y = self.screen.get_height() - menu_button_height - 10
        
        self.menu_button_rect = pygame.Rect(menu_x, menu_y, menu_button_width, menu_button_height)
        
        mouse_pos = pygame.mouse.get_pos()
        if self.menu_button_rect.collidepoint(mouse_pos):
            button_color = (100, 100, 120)
            text_color = (255, 255, 255)
        else:
            button_color = (60, 60, 80)
            text_color = (200, 200, 200)
        
        pygame.draw.rect(self.screen, button_color, self.menu_button_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), self.menu_button_rect, 2)
        
        menu_text = self.font.render("MENU", True, text_color)
        menu_text_rect = menu_text.get_rect(center=(menu_x + menu_button_width // 2, menu_y + menu_button_height // 2))
        self.screen.blit(menu_text, menu_text_rect)
    
    def draw_transport_menu(self):
        """Draw full transportation selection menu"""
        if not self.show_transport_menu:
            return
        
        menu_width = 600
        menu_height = 500
        menu_x = (self.screen.get_width() - menu_width) // 2
        menu_y = (self.screen.get_height() - menu_height) // 2
        
        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(self.screen, (30, 30, 40), menu_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), menu_rect, 3)
        
        title_text = self.font.render("Transportation Options", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(menu_x + menu_width // 2, menu_y + 30))
        self.screen.blit(title_text, title_rect)
        
        current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
        if current_hex:
            terrain_text = self.small_font.render(f"Current Terrain: {current_hex.terrain.title()}", True, (200, 200, 200))
            self.screen.blit(terrain_text, (menu_x + 20, menu_y + 60))
        
        col_width = 190
        row_height = 100
        cols = 3
        
        y_offset = menu_y + 90
        for i, (trans_key, trans_data) in enumerate(TRANSPORTATION_MODES.items()):
            col = i % cols
            row = i // cols
            
            x = menu_x + 10 + col * col_width
            y = y_offset + row * row_height
            
            can_use = True
            speed_text = ""
            if current_hex:
                modifier = trans_data["terrain_modifiers"][current_hex.terrain]
                if modifier >= 999:
                    can_use = False
                    speed_text = "Cannot use here!"
                else:
                    base_speed = trans_data["base_hexes_per_8h"][self.hex_map.travel_system.current_pace]
                    effective_speed = base_speed / modifier
                    speed_text = f"Speed: {effective_speed:.1f} hex/8h"
            
            box_rect = pygame.Rect(x, y, col_width - 10, row_height - 10)
            
            is_current = self.hex_map.travel_system.current_transport == trans_key
            
            if is_current:
                box_color = (60, 60, 100)
                border_color = (255, 255, 100)
            elif not can_use:
                box_color = (60, 30, 30)
                border_color = (150, 50, 50)
            else:
                box_color = (40, 40, 60)
                border_color = (100, 100, 150)
            
            pygame.draw.rect(self.screen, box_color, box_rect)
            pygame.draw.rect(self.screen, border_color, box_rect, 2)
            
            name_text = self.small_font.render(trans_data["name"], True, (255, 255, 255))
            self.screen.blit(name_text, (x + 5, y + 5))
            
            speed_color = (150, 150, 150) if can_use else (200, 100, 100)
            speed_surface = self.small_font.render(speed_text, True, speed_color)
            self.screen.blit(speed_surface, (x + 5, y + 25))
            
            desc_words = trans_data["description"].split()
            desc_lines = []
            current_line = []
            for word in desc_words:
                test_line = ' '.join(current_line + [word])
                if self.small_font.size(test_line)[0] < col_width - 20:
                    current_line.append(word)
                else:
                    if current_line:
                        desc_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                desc_lines.append(' '.join(current_line))
            
            for j, line in enumerate(desc_lines[:2]):
                line_surface = self.small_font.render(line, True, (180, 180, 180))
                self.screen.blit(line_surface, (x + 5, y + 45 + j * 15))
            
            self.transport_menu_buttons[trans_key] = box_rect
        
        close_button = pygame.Rect(menu_x + menu_width - 110, menu_y + menu_height - 40, 100, 30)
        pygame.draw.rect(self.screen, (150, 50, 50), close_button)
        pygame.draw.rect(self.screen, (200, 100, 100), close_button, 2)
        close_text = self.font.render("Close (ESC)", True, (255, 255, 255))
        close_rect = close_text.get_rect(center=close_button.center)
        self.screen.blit(close_text, close_rect)
        self.transport_close_button = close_button

    def draw_party_menu(self):
        """Draw the party composition and bonuses menu"""
        if not self.show_party_menu:
            return

        menu_width, menu_height = 500, 400
        menu_x = (self.screen.get_width() - menu_width) // 2
        menu_y = (self.screen.get_height() - menu_height) // 2

        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(self.screen, (30, 30, 30), menu_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), menu_rect, 3)

        # Title
        title = self.font.render("Party Composition", True, (255, 255, 255))
        title_rect = title.get_rect(center=(menu_x + menu_width // 2, menu_y + 30))
        self.screen.blit(title, title_rect)

        party = self.hex_map.travel_system

        # Toggles for Ranger, Navigator, Outlander
        opts = [
            ("ranger", "Ranger", "Reduces movement cost on favored terrain"),
            ("navigator", "Navigator", "Improves travel speed by 10%"),
            ("outlander", "Outlander", "Prevents getting lost in wilderness")
        ]
        
        y = menu_y + 70
        for attr, label, desc in opts:
            # Checkbox
            btn = pygame.Rect(menu_x + 20, y, 20, 20)
            pygame.draw.rect(self.screen, (50, 50, 50), btn)
            pygame.draw.rect(self.screen, (200, 200, 200), btn, 1)
            
            # Checkmark if enabled
            if getattr(party, f"has_{attr}"):
                pygame.draw.line(self.screen, (100, 255, 100),
                                 (btn.left + 4, btn.centery),
                                 (btn.centerx, btn.bottom - 4), 2)
                pygame.draw.line(self.screen, (100, 255, 100),
                                 (btn.centerx, btn.bottom - 4),
                                 (btn.right - 4, btn.top + 4), 2)
            
            # Label
            txt = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(txt, (btn.right + 10, y - 2))
            
            # Description
            desc_txt = self.small_font.render(desc, True, (180, 180, 180))
            self.screen.blit(desc_txt, (menu_x + 20, y + 25))
            
            self.party_menu_buttons[attr] = btn
            y += 60

        # Favored terrain row (only if Ranger is enabled)
        if party.has_ranger:
            fav_label = self.font.render("Ranger's Favored Terrain:", True, (200, 200, 255))
            self.screen.blit(fav_label, (menu_x + 20, y))
            y += 30
            
            # Terrain selection buttons
            self.terrain_buttons = []
            terrains = ["forest", "plains", "mountains", "desert", "swamp", "hills"]
            cols = 3
            button_width = 120
            button_height = 30
            
            for i, terrain in enumerate(terrains):
                col = i % cols
                row = i // cols
                x = menu_x + 20 + col * (button_width + 10)
                terrain_y = y + row * (button_height + 10)
                
                tbtn = pygame.Rect(x, terrain_y, button_width, button_height)
                selected = (party.favored_terrain == terrain)
                color = (80, 80, 120) if selected else (60, 60, 80)
                
                pygame.draw.rect(self.screen, color, tbtn)
                pygame.draw.rect(self.screen, (200, 200, 200), tbtn, 1)
                
                ttxt = self.small_font.render(terrain.title(), True, (255, 255, 255))
                text_rect = ttxt.get_rect(center=tbtn.center)
                self.screen.blit(ttxt, text_rect)
                
                self.terrain_buttons.append((terrain, tbtn))
            
            y += 80

        # Close button
        close_btn = pygame.Rect(menu_x + menu_width - 110, menu_y + menu_height - 40, 100, 30)
        pygame.draw.rect(self.screen, (150, 50, 50), close_btn)
        pygame.draw.rect(self.screen, (200, 100, 100), close_btn, 2)
        close_txt = self.font.render("Close (ESC)", True, (255, 255, 255))
        close_rect = close_txt.get_rect(center=close_btn.center)
        self.screen.blit(close_txt, close_rect)
        self.party_close_button = close_btn

    
    def draw_message(self):
        """Draw temporary message"""
        if self.message and self.message_timer > 0:
            msg_surface = self.font.render(self.message, True, (255, 255, 0))
            msg_rect = msg_surface.get_rect(center=(self.screen.get_width() // 2, 100))
            
            # Background
            padding = 10
            bg_rect = msg_rect.inflate(padding * 2, padding)
            pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
            pygame.draw.rect(self.screen, (255, 255, 0), bg_rect, 2)
            
            self.screen.blit(msg_surface, msg_rect)
    
    def draw_popup(self):
        """Draw hex description popup"""
        if not self.show_popup or not self.selected_hex:
            return
        
        hex_obj = self.hex_map.hexes.get(self.selected_hex)
        if not hex_obj:
            return
        
        popup_width = 400
        popup_height = 240
        popup_x = (self.screen.get_width() - popup_width) // 2
        popup_y = (self.screen.get_height() - popup_height) // 2
        
        popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
        pygame.draw.rect(self.screen, (50, 50, 50), popup_rect)
        pygame.draw.rect(self.screen, (200, 200, 200), popup_rect, 2)
        
        # Terrain and movement cost
        terrain_text = self.font.render(f"{hex_obj.terrain.title()}", True, (255, 255, 255))
        self.screen.blit(terrain_text, (popup_x + 10, popup_y + 10))
        
        cost_text = self.small_font.render(f"Movement cost: {TERRAIN_TYPES[hex_obj.terrain]['movement_cost']}", True, (150, 200, 150))
        self.screen.blit(cost_text, (popup_x + 10, popup_y + 35))
        
        coord_text = self.small_font.render(f"Location: ({hex_obj.q}, {hex_obj.r})", True, (150, 150, 150))
        self.screen.blit(coord_text, (popup_x + 10, popup_y + 55))
        
        # Description
        if hex_obj.generating:
            gen_text = self.font.render("Generating description...", True, (255, 255, 0))
            gen_rect = gen_text.get_rect(center=(popup_x + popup_width // 2, popup_y + 120))
            self.screen.blit(gen_text, gen_rect)
        else:
            words = hex_obj.description.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                if self.small_font.size(test_line)[0] < popup_width - 20:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            y_offset = 75
            for line in lines[:4]:
                desc_text = self.small_font.render(line, True, (200, 200, 200))
                self.screen.blit(desc_text, (popup_x + 10, popup_y + y_offset))
                y_offset += 20
        
        # Buttons
        button_y = popup_y + 190
        
        if not hex_obj.generating:
            travel = self.hex_map.travel_system
            can_move = travel.can_move_to(hex_obj.terrain)
            
            curr_q, curr_r, curr_s = self.hex_map.current_position
            adjacent_explored = self.hex_map.get_adjacent_explored(curr_q, curr_r, curr_s)
            is_adjacent_explored = self.selected_hex in adjacent_explored
            
            if not hex_obj.explored:
                # Explore button
                explore_color = (0, 150, 0) if can_move else (100, 100, 100)
                explore_rect = pygame.Rect(popup_x + 50, button_y, 100, 30)
                pygame.draw.rect(self.screen, explore_color, explore_rect)
                explore_text = self.font.render("Explore", True, (255, 255, 255))
                self.screen.blit(explore_text, (explore_rect.x + 20, explore_rect.y + 5))
                
                if not can_move:
                    no_mp_text = self.small_font.render(f"Need {TERRAIN_TYPES[hex_obj.terrain]['movement_cost']} MP", True, (255, 100, 100))
                    self.screen.blit(no_mp_text, (popup_x + 50, button_y + 35))
            elif is_adjacent_explored:
                # Navigate button
                nav_color = (0, 100, 150) if can_move else (100, 100, 100)
                navigate_rect = pygame.Rect(popup_x + 50, button_y, 100, 30)
                pygame.draw.rect(self.screen, nav_color, navigate_rect)
                navigate_text = self.font.render("Navigate", True, (255, 255, 255))
                self.screen.blit(navigate_text, (navigate_rect.x + 15, navigate_rect.y + 5))
            
            # Close button
            close_rect = pygame.Rect(popup_x + 250, button_y, 100, 30)
            pygame.draw.rect(self.screen, (150, 0, 0), close_rect)
            close_text = self.font.render("Close", True, (255, 255, 255))
            self.screen.blit(close_text, (close_rect.x + 30, close_rect.y + 5))
    
    def handle_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle mouse clicks"""
        if self.gen_manager.generating:
            return None
        
        # Check if menu button was clicked
        if hasattr(self, 'menu_button_rect') and self.menu_button_rect.collidepoint(pos):
            return "menu"
        
        if self.show_popup and self.selected_hex:
            popup_width = 400
            popup_height = 240
            popup_x = (self.screen.get_width() - popup_width) // 2
            popup_y = (self.screen.get_height() - popup_height) // 2
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
            button_y = popup_y + 190
            
            hex_obj = self.hex_map.hexes.get(self.selected_hex)
            if hex_obj and not hex_obj.generating:
                travel = self.hex_map.travel_system
                can_move = travel.can_move_to(hex_obj.terrain)
                
                curr_q, curr_r, curr_s = self.hex_map.current_position
                adjacent_explored = self.hex_map.get_adjacent_explored(curr_q, curr_r, curr_s)
                is_adjacent_explored = self.selected_hex in adjacent_explored
                
                if not hex_obj.explored and can_move:
                    explore_rect = pygame.Rect(popup_x + 50, button_y, 100, 30)
                    if explore_rect.collidepoint(pos):
                        return "explore"
                elif is_adjacent_explored and can_move:
                    navigate_rect = pygame.Rect(popup_x + 50, button_y, 100, 30)
                    if navigate_rect.collidepoint(pos):
                        return "navigate"
                
                close_rect = pygame.Rect(popup_x + 250, button_y, 100, 30)
                if close_rect.collidepoint(pos):
                    return "close"
            
            if not popup_rect.collidepoint(pos):
                self.show_popup = False
                self.selected_hex = None
        else:
            hex_coords = self.pixel_to_hex(*pos)
            if hex_coords in self.hex_map.hexes and self.hex_map.hexes[hex_coords].visible:
                self.selected_hex = hex_coords
                self.show_popup = True
        
        return None
    
    def set_message(self, msg: str, duration: float = 2.0):
        """Set a temporary message"""
        self.message = msg
        self.message_timer = duration
    
    def update(self, dt: float):
        """Update animations and timers"""
        self.sprites.update_adventurer(dt)
        self.sprites.update_scout(dt)
        if self.message_timer > 0:
            self.message_timer -= dt

class HexMapExplorer:
    """Main application"""
    
    # Enhanced event handling for HexMapExplorer
    # Add these to the HexMapExplorer class

    def __init__(self):
        """Enhanced initialization with transport menus"""
        pygame.init()
        
        # Get display info for responsive sizing
        info = pygame.display.Info()
        display_width = info.current_w
        display_height = info.current_h
        
        # Set window size (90% of screen or minimum size)
        self.width = max(1024, min(int(display_width * 0.9), 1920))
        self.height = max(768, min(int(display_height * 0.9), 1080))
        
        # Create resizable window
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Hex Map Explorer - Enhanced Travel System")
        self.clock = pygame.time.Clock()
        
        self.ollama = OllamaClient()
        self.gen_manager = GenerationManager(self.ollama)
        self.hex_map = HexMap(self.ollama, self.gen_manager)
        self.renderer = HexMapRenderer(self.screen, self.hex_map, self.gen_manager)
        
        # Add menu state flags
        self.renderer.show_transport_menu = False
        self.renderer.show_party_menu = False
        
        self.running = True
        self.last_time = time.time()
        
        print("Initializing map with enhanced travel system...")
        self.hex_map.initialize_map()

    def handle_transport_click(self, pos: Tuple[int,int]) -> bool:
        """Handle clicks on transport UI elements"""
        ts = self.hex_map.travel_system
        rnd = self.renderer

        # --- FULL MENU BUTTONS (only if it's open) ---
        if rnd.show_transport_menu:
            # Change transport via full-menu buttons
            for key, rect in rnd.transport_menu_buttons.items():
                if rect.collidepoint(pos):
                    current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
                    if current_hex:
                        modifier = TRANSPORTATION_MODES[key]["terrain_modifiers"][current_hex.terrain]
                        if modifier < 999:
                            ts.change_transport(key)
                            rnd.set_message(f"Changed to {TRANSPORTATION_MODES[key]['name']}")
                        else:
                            rnd.set_message(f"Cannot use {TRANSPORTATION_MODES[key]['name']} here!")
                    return True
            
            # Close full menu
            if hasattr(rnd, 'transport_close_button') and rnd.transport_close_button.collidepoint(pos):
                rnd.show_transport_menu = False
                return True

        # --- QUICK-PANEL BUTTONS (always visible under travel UI) ---
        for key, rect in rnd.transport_buttons.items():
            if rect.collidepoint(pos):
                current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
                if current_hex:
                    modifier = TRANSPORTATION_MODES[key]["terrain_modifiers"][current_hex.terrain]
                    if modifier < 999:
                        ts.change_transport(key)
                        rnd.set_message(f"Changed to {TRANSPORTATION_MODES[key]['name']}")
                    else:
                        rnd.set_message(f"Cannot use {TRANSPORTATION_MODES[key]['name']} here!")
                return True

        # --- "More Transport Options" BUTTON ---
        if hasattr(rnd, 'more_transport_button') and rnd.more_transport_button.collidepoint(pos):
            rnd.show_transport_menu = True
            rnd.show_party_menu = False
            return True

        # --- "Party Composition" BUTTON ---
        if hasattr(rnd, 'party_button') and rnd.party_button.collidepoint(pos):
            rnd.show_party_menu = True
            rnd.show_transport_menu = False
            return True

        return False

    def handle_party_click(self, pos):
        """Handle clicks in party menu"""
        if not self.renderer.show_party_menu:
            return False

        travel = self.hex_map.travel_system

        # Toggle traits
        for attr in ("ranger", "navigator", "outlander"):
            btn = self.renderer.party_menu_buttons.get(attr)
            if btn and btn.collidepoint(pos):
                getattr(travel, f"toggle_{attr}")()
                self.renderer.set_message(
                    f"{attr.title()} " +
                    ("joined" if getattr(travel, f"has_{attr}") else "left")
                )
                return True

        # Select favored terrain
        for terrain, rect in getattr(self.renderer, "terrain_buttons", []):
            if rect.collidepoint(pos):
                travel.set_favored_terrain(terrain)
                self.renderer.set_message(f"Favored terrain: {terrain}")
                return True

        # Close menu
        if hasattr(self.renderer, "party_close_button") and \
           self.renderer.party_close_button.collidepoint(pos):
            self.renderer.show_party_menu = False
            return True

        return False


    def check_resupply(self):
        """Check if current hex is a town/settlement for resupply"""
        # Simple check - you could expand this with actual town hexes
        current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
        if current_hex and "town" in current_hex.description.lower():
            return True
        # Starting position counts as town
        if self.hex_map.current_position == (0, 0, 0):
            return True
        return False

    # Enhanced run method with new event handling
    def run(self):
        """Main game loop with enhanced transport controls"""
        while self.running:
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.gen_manager.cancel()
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and not self.gen_manager.generating:
                        # 1) Give menus first crack at the click
                        if self.handle_transport_click(event.pos):
                            continue
                        if self.handle_party_click(event.pos):
                            continue

                        # 2) Otherwise fall back to map-clicks
                        action = self.renderer.handle_click(event.pos)
                        if action == "menu":
                            if self.confirm_return_to_menu():
                                self.return_to_menu()
                        elif action == "explore":
                            success, msg = self.hex_map.explore_hex(*self.renderer.selected_hex)
                            if not success:
                                self.renderer.set_message(msg)
                            self.renderer.show_popup = False
                            self.renderer.selected_hex = None
                        elif action == "navigate":
                            success, msg = self.hex_map.navigate_to_hex(*self.renderer.selected_hex)
                            if not success:
                                self.renderer.set_message(msg)
                            self.renderer.show_popup = False
                            self.renderer.selected_hex = None
                        elif action == "close":
                            self.renderer.show_popup = False
                            self.renderer.selected_hex = None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                    elif event.key == pygame.K_m and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self.return_to_menu()
                    elif not self.gen_manager.generating:
                        if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            self.save_map()
                        elif event.key == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_CTRL:
                            self.load_map()
                        elif event.key == pygame.K_r:
                            # Rest
                            self.hex_map.rest_and_scout()
                            self.renderer.set_message("Resting... Movement restored!")
                        elif event.key == pygame.K_p:
                            # Change pace
                            travel = self.hex_map.travel_system
                            paces = ["slow", "normal", "fast"]
                            idx = paces.index(travel.current_pace)
                            new_pace = paces[(idx + 1) % 3]
                            travel.change_pace(new_pace)
                            self.renderer.set_message(f"Pace: {new_pace.title()}")
                        elif event.key == pygame.K_f:
                            # Forced march
                            if self.hex_map.travel_system.forced_march():
                                self.renderer.set_message("Forced march! +2 movement")
                            else:
                                self.renderer.set_message("Cannot force march with this transport")
                        elif event.key == pygame.K_t:
                            # toggle full transport menu
                            self.renderer.show_transport_menu = not self.renderer.show_transport_menu
                            # hide party menu if it was open
                            self.renderer.show_party_menu = False
                        elif event.key == pygame.K_y:
                            # Toggle party menu
                            self.renderer.show_party_menu = not self.renderer.show_party_menu
                            self.renderer.show_transport_menu = False
                        elif event.key == pygame.K_s and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                            # Resupply (if in town)
                            if self.check_resupply():
                                self.hex_map.travel_system.resupply(10)
                                self.renderer.set_message("Resupplied! +10 days of supplies")
                            else:
                                self.renderer.set_message("Must be in a town to resupply")
                    if event.key == pygame.K_ESCAPE:
                        if self.gen_manager.generating:
                            self.gen_manager.cancel()
                        elif self.renderer.show_transport_menu:
                            self.renderer.show_transport_menu = False
                        elif self.renderer.show_party_menu:
                            self.renderer.show_party_menu = False
                        elif self.renderer.show_popup:
                            self.renderer.show_popup = False
                            self.renderer.selected_hex = None
                        else:
                            if self.confirm_return_to_menu():
                                self.return_to_menu()
            
            # Update
            self.renderer.update(dt)
            
            # Draw
            self.screen.fill((30, 30, 30))
            self.renderer.draw_map()
            self.renderer.draw_travel_ui()
            self.renderer.draw_transport_menu()
            self.renderer.draw_party_menu()
            self.renderer.draw_popup()
            self.renderer.draw_loading_animation()
            self.renderer.draw_message()
            
            # Status bar with transport info
            transport_name = TRANSPORTATION_MODES[self.hex_map.travel_system.current_transport]["name"]
            if self.gen_manager.generating:
                status = f"ESC: Cancel | Transport: {transport_name}"
            else:
                status = f"ESC: Menu | T:Transport Y:Party | {transport_name}"
            status_text = self.renderer.small_font.render(status, True, (200, 200, 200))
            self.screen.blit(status_text, (10, 10))
            
            # Position and terrain
            curr_q, curr_r, curr_s = self.hex_map.current_position
            current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
            terrain_info = f" - {current_hex.terrain.title()}" if current_hex else ""
            pos_text = self.renderer.small_font.render(f"Position: ({curr_q}, {curr_r}){terrain_info}", True, (150, 200, 150))
            self.screen.blit(pos_text, (10, 30))
            
            pygame.display.flip()
            self.clock.tick(60)
        
        self.ollama.cleanup()
        pygame.quit()

    # Enhanced save/load to include transport data
    def save_map(self):
        """Save map with transport data to JSON"""
        if self.gen_manager.generating:
            return
        
        root = tk.Tk()
        root.withdraw()
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            try:
                # Add transport data to save
                self.hex_map.travel_data_extra = {
                    "transport": self.hex_map.travel_system.current_transport,
                    "supplies": self.hex_map.travel_system.supplies,
                    "mount_exhaustion": self.hex_map.travel_system.mount_exhaustion,
                    "has_ranger": self.hex_map.travel_system.has_ranger,
                    "has_navigator": self.hex_map.travel_system.has_navigator,
                    "has_outlander": self.hex_map.travel_system.has_outlander,
                    "favored_terrain": self.hex_map.travel_system.favored_terrain
                }
                self.hex_map.save_to_json(filename)
                self.renderer.set_message("Map saved!")
            except Exception as e:
                self.renderer.set_message(f"Save failed: {e}")
        root.destroy()

    def load_map(self):
        """Load map with transport data from JSON"""
        if self.gen_manager.generating:
            return
        
        root = tk.Tk()
        root.withdraw()
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            try:
                self.hex_map.load_from_json(filename)
                # Load additional transport data if present
                if hasattr(self.hex_map, 'travel_data_extra'):
                    extra = self.hex_map.travel_data_extra
                    travel = self.hex_map.travel_system
                    travel.current_transport = extra.get("transport", "on_foot")
                    travel.supplies = extra.get("supplies", 10)
                    travel.mount_exhaustion = extra.get("mount_exhaustion", 0)
                    travel.has_ranger = extra.get("has_ranger", False)
                    travel.has_navigator = extra.get("has_navigator", False)
                    travel.has_outlander = extra.get("has_outlander", False)
                    travel.favored_terrain = extra.get("favored_terrain", None)
                    travel._update_movement_points()
                self.renderer.set_message("Map loaded!")
            except Exception as e:
                self.renderer.set_message(f"Load failed: {e}")
        root.destroy()
    def handle_resize(self, event):
        """Handle window resize event"""
        self.width = event.w
        self.height = event.h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.renderer.screen = self.screen
        
        # Update renderer with adaptive sizing
        screen_size = min(self.width, self.height)
        self.renderer.hex_size = max(20, min(40, int(screen_size * 0.04)))
        self.renderer.font = pygame.font.Font(None, max(20, min(32, int(screen_size * 0.03))))
        self.renderer.small_font = pygame.font.Font(None, max(14, min(20, int(screen_size * 0.02))))
        self.renderer.update_hex_vertices()
    
      
       
    def open_map_converter(self):
        """Open the map image converter"""
        try:
            from map_image_converter import MapImageConverter
            converter = MapImageConverter()
            
            # Create a temporary Tk root for the converter dialog
            import tkinter as tk
            temp_root = tk.Tk()
            temp_root.withdraw()  # Hide the root window
            converter.open_converter_window()
            self.renderer.set_message("Converter opened in new window")
        except Exception as e:
            self.renderer.set_message(f"Converter error: {e}")
    
    def import_converted_map(self):
        """Import a converted map with options"""
        try:
            from map_image_converter import MapImportDialog
            import tkinter as tk
            
            # Create temporary Tk root
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            dialog = MapImportDialog(temp_root, self.hex_map)
            temp_root.wait_window(dialog.dialog)
            
            self.renderer.set_message("Map imported!")
        except Exception as e:
            self.renderer.set_message(f"Import error: {e}")
    
    def confirm_return_to_menu(self):
        """Show confirmation dialog for returning to menu"""
        # Quick save prompt
        result = messagebox.askyesnocancel(
            "Return to Menu",
            "Do you want to save your game before returning to the menu?"
        )
        
        if result is True:  # Yes - save and return
            root = tk.Tk()
            root.withdraw()
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=f"quicksave_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            if filename:
                try:
                    self.hex_map.save_to_json(filename)
                    root.destroy()
                    return True
                except Exception as e:
                    messagebox.showerror("Error", f"Save failed: {e}")
            root.destroy()
            return False
        elif result is False:  # No - return without saving
            return True
        else:  # Cancel
            return False
    
    def return_to_menu(self):
        """Return to the main menu"""
        self.running = False
        self.ollama.cleanup()
        
        # Import and run main menu
        from main_menu import MainMenu
        menu = MainMenu()
        menu.run()
    
    def edit_current_hex(self):
        """Edit the current hex description"""
        try:
            from map_image_converter import HexEditor
            import tkinter as tk
            
            curr_pos = self.hex_map.current_position
            if curr_pos not in self.hex_map.hexes:
                self.renderer.set_message("No hex at current position")
                return
            
            hex_obj = self.hex_map.hexes[curr_pos]
            
            # Create temporary Tk root
            temp_root = tk.Tk()
            temp_root.withdraw()
            
            def on_save(updated_hex):
                # Update the hex in the map
                self.hex_map.hexes[curr_pos] = updated_hex
                self.renderer.set_message("Hex updated!")
            
            editor = HexEditor(temp_root, hex_obj, on_save)
            temp_root.wait_window(editor.dialog)
            
        except Exception as e:
            self.renderer.set_message(f"Edit error: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("Hex Map Explorer - D&D 5e Travel System")
    print("=" * 50)
    print("\nTravel Rules:")
    print("- Normal pace: 8 hexes per day (3-mile hexes)")
    print("- Difficult terrain costs more movement")
    print("- Rest to restore movement and scout 2-hex radius")
    print("\nControls:")
    print("- R: Rest (reveals 2-hex radius)")
    print("- P: Change pace (slow/normal/fast)")
    print("- F: Forced march (risk exhaustion)")
    print("-" * 50)
    
    explorer = HexMapExplorer()
    explorer.run()