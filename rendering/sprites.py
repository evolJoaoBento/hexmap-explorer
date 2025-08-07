"""
Pixel art sprites and animations for hex map explorer
"""
import pygame
import math
import time
from typing import List


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