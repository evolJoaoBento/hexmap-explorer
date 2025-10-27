"""
Pygame-based Hex Map Generator
High-performance visual hex map generator with smooth navigation
"""
import pygame
import math
import random
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def safe_import():
    """Safely import biome system"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        from config.constants import TERRAIN_TYPES
        return MinecraftBiomeGenerator, TERRAIN_TYPES
    except ImportError:
        return None, None

class PygameHexGenerator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Screen settings
        self.SCREEN_WIDTH = 1200
        self.SCREEN_HEIGHT = 800
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Hex Map Generator - Pygame Edition")
        
        # Colors
        self.COLORS = {
            'background': (20, 25, 30),
            'ui_bg': (40, 45, 50),
            'ui_border': (100, 110, 120),
            'text': (255, 255, 255),
            'button': (60, 70, 80),
            'button_hover': (80, 90, 100),
            'button_active': (100, 120, 140),
            # Terrain colors
            'water': (64, 164, 223),
            'forest': (34, 139, 34),
            'plains': (144, 238, 144),
            'mountains': (139, 137, 137),
            'desert': (238, 203, 173),
            'hills': (160, 82, 45),
            'swamp': (47, 79, 79),
            'tundra': (176, 224, 230)
        }
        
        # Fonts
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        # Map settings - paint brush system
        self.brush_size = 4  # Larger brush for painting massive continents
        self.mouse_x = 0
        self.mouse_y = 0
        self.brush_preview_hexes = set()  # Hexes that would be painted
        self.seed = 12345
        self.hex_data = {}
        self.biome_counts = {}
        
        # View settings
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.hex_size = 25
        
        # Navigation
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.keys_pressed = set()
        
        # UI elements
        self.ui_panel_width = 300
        self.map_area = pygame.Rect(self.ui_panel_width, 0, 
                                  self.SCREEN_WIDTH - self.ui_panel_width, 
                                  self.SCREEN_HEIGHT)
        
        # Buttons
        self.buttons = {}
        self.create_ui_elements()
        
        # Initialize biome generator
        try:
            self.MinecraftBiomeGenerator, self.TERRAIN_TYPES = safe_import()
            print("Biome generator imported successfully")
        except Exception as e:
            print(f"Error importing biome generator: {e}")
            self.MinecraftBiomeGenerator, self.TERRAIN_TYPES = None, None
        
        # Clock for smooth animation
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Tooltip
        self.tooltip_hex = None
        self.tooltip_pos = (0, 0)
    
    def create_ui_elements(self):
        """Create UI buttons and input areas - match draw_ui positions exactly"""
        button_width = 120
        button_height = 30
        margin = 10
        
        # Match draw_ui exactly: y_pos = 15 + 45 + 30 = 90
        y_pos = 90  # After title (15+45) and GENERATION header (+30)
        
        # Generation buttons (4 buttons)
        self.buttons['generate'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['load_continents'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['set_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['random_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        # After 4 generation buttons: y_pos = 90 + 4*(30+10) = 90 + 160 = 250
        # Remove view controls section, go directly to export
        # Add 170px space + 10px after header for EXPORT CONTROLS buttons
        export_start = 250 + 170 + 10  # Generation end + space + header space
        
        self.buttons['save_json'] = pygame.Rect(margin, export_start, button_width, button_height)
        self.buttons['copy_game'] = pygame.Rect(margin, export_start + 40, button_width, button_height)
        self.buttons['screenshot'] = pygame.Rect(margin, export_start + 80, button_width, button_height)
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed.add(event.key)
            
            elif event.type == pygame.KEYUP:
                self.keys_pressed.discard(event.key)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.handle_left_click(event.pos)
                elif event.button == 2:  # Middle click
                    self.dragging = True
                    self.last_mouse_pos = event.pos
                elif event.button == 3:  # Right click
                    self.dragging = True
                    self.last_mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in [2, 3]:  # Middle or right click
                    self.dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx / self.zoom
                    self.camera_y += dy / self.zoom
                    self.last_mouse_pos = event.pos
                else:
                    # Update tooltip
                    self.update_tooltip(event.pos)
                    
                    # Update brush preview when mouse is over map area
                    if self.map_area.collidepoint(event.pos):
                        self.update_brush_preview(event.pos[0], event.pos[1])
            
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                self.SCREEN_WIDTH = event.w
                self.SCREEN_HEIGHT = event.h
                self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT), pygame.RESIZABLE)
                
                # Update map area
                self.map_area = pygame.Rect(self.ui_panel_width, 0, 
                                          self.SCREEN_WIDTH - self.ui_panel_width, 
                                          self.SCREEN_HEIGHT)
                
                # Recreate UI elements with new positions
                self.create_ui_elements()
            
            elif event.type == pygame.MOUSEWHEEL:
                # Zoom with mouse wheel
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if self.map_area.collidepoint(mouse_x, mouse_y):
                    old_zoom = self.zoom
                    if event.y > 0:  # Zoom in
                        self.zoom = min(self.max_zoom, self.zoom * 1.2)
                    else:  # Zoom out
                        self.zoom = max(self.min_zoom, self.zoom * 0.8)
                    
                    # Adjust camera to zoom at mouse position
                    zoom_factor = self.zoom / old_zoom
                    map_mouse_x = mouse_x - self.map_area.x
                    map_mouse_y = mouse_y - self.map_area.y
                    
                    self.camera_x = map_mouse_x - (map_mouse_x - self.camera_x) * zoom_factor
                    self.camera_y = map_mouse_y - (map_mouse_y - self.camera_y) * zoom_factor
    
    def handle_left_click(self, pos):
        """Handle left mouse clicks"""
        # Check UI buttons first
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(pos):
                self.handle_button_click(button_name)
                return
        
        # Check map click for hex details or generation
        if self.map_area.collidepoint(pos):
            map_x = pos[0] - self.map_area.x
            map_y = pos[1] - self.map_area.y
            hex_coords = self.get_hex_at_screen_pos(map_x, map_y)
            
            if hex_coords and hex_coords in self.hex_data:
                # Existing hex - show details
                self.show_hex_details(hex_coords)
            else:
                # Empty area - paint hexes with brush
                self.paint_hexes()
    
    def handle_button_click(self, button_name):
        """Handle button clicks"""
        if button_name == 'generate':
            self.generate_map()
        elif button_name == 'load_continents':
            self.load_all_continents()
        elif button_name == 'set_seed':
            self.set_seed()
        elif button_name == 'random_seed':
            self.seed = random.randint(1, 1000000)
        elif button_name == 'save_json':
            self.save_json()
        elif button_name == 'copy_game':
            self.copy_to_game()
        elif button_name == 'screenshot':
            self.take_screenshot()
    
    def update_keyboard_navigation(self):
        """Handle keyboard navigation"""
        move_speed = 300 / self.zoom  # Adjust speed based on zoom
        
        if pygame.K_w in self.keys_pressed or pygame.K_UP in self.keys_pressed:
            self.camera_y += move_speed * (1/60)  # Assuming 60 FPS
        if pygame.K_s in self.keys_pressed or pygame.K_DOWN in self.keys_pressed:
            self.camera_y -= move_speed * (1/60)
        if pygame.K_a in self.keys_pressed or pygame.K_LEFT in self.keys_pressed:
            self.camera_x += move_speed * (1/60)
        if pygame.K_d in self.keys_pressed or pygame.K_RIGHT in self.keys_pressed:
            self.camera_x -= move_speed * (1/60)
        
        if pygame.K_r in self.keys_pressed:
            self.reset_view()
            self.keys_pressed.discard(pygame.K_r)  # Prevent rapid reset
        
        if pygame.K_F12 in self.keys_pressed:
            self.take_screenshot()
            self.keys_pressed.discard(pygame.K_F12)  # Prevent rapid screenshots
        
        if pygame.K_EQUALS in self.keys_pressed or pygame.K_PLUS in self.keys_pressed:
            self.zoom = min(self.max_zoom, self.zoom * 1.02)
        if pygame.K_MINUS in self.keys_pressed:
            self.zoom = max(self.min_zoom, self.zoom * 0.98)
            
        # Brush size controls
        if pygame.K_LEFTBRACKET in self.keys_pressed:
            self.brush_size = max(1, self.brush_size - 1)
            print(f"Brush size: {self.brush_size}")
            self.keys_pressed.discard(pygame.K_LEFTBRACKET)
            
        if pygame.K_RIGHTBRACKET in self.keys_pressed:
            self.brush_size = min(100, self.brush_size + 1)  # Massive brush for continent painting!
            print(f"Brush size: {self.brush_size}")
            self.keys_pressed.discard(pygame.K_RIGHTBRACKET)
            
        # Fast brush size controls
        if pygame.K_1 in self.keys_pressed:
            self.brush_size = 10
            print(f"Brush size: {self.brush_size}")
            self.keys_pressed.discard(pygame.K_1)
        elif pygame.K_2 in self.keys_pressed:
            self.brush_size = 25
            print(f"Brush size: {self.brush_size}")
            self.keys_pressed.discard(pygame.K_2)
        elif pygame.K_3 in self.keys_pressed:
            self.brush_size = 50
            print(f"Brush size: {self.brush_size}")
            self.keys_pressed.discard(pygame.K_3)
        elif pygame.K_4 in self.keys_pressed:
            self.brush_size = 100
            print(f"Brush size: {self.brush_size} - MAXIMUM!")
            self.keys_pressed.discard(pygame.K_4)
    
    def generate_map(self):
        """Generate initial center hex"""
        try:
            if not self.MinecraftBiomeGenerator:
                print("Error: MinecraftBiomeGenerator not available")
                return
            
            print(f"Generating center hex (seed {self.seed})...")
            
            # Reset all data
            self.hex_data = {}
            self.biome_counts = {}
            
            # Generate just the center hex
            generator = self.MinecraftBiomeGenerator(self.seed)
            terrain = generator.select_biome(0, 0, 0)
            
            self.hex_data[(0, 0, 0)] = {
                'q': 0, 'r': 0, 's': 0,
                'terrain': terrain,
                'is_center': True
            }
            self.biome_counts[terrain] = 1
            
            # Reset view to show the new map
            self.reset_view()
            print(f"Generated center hex with terrain: {terrain}")
            
        except Exception as e:
            print(f"Error in generate_map: {e}")
            import traceback
            traceback.print_exc()
    
    def load_all_continents(self):
        """Load all continents at once based on seed configuration"""
        try:
            if not self.MinecraftBiomeGenerator:
                print("Error: MinecraftBiomeGenerator not available")
                return
            
            print(f"Loading all continents for seed {self.seed}...")
            
            # Reset all data
            self.hex_data = {}
            self.biome_counts = {}
            
            # Create generator to get continent data
            generator = self.MinecraftBiomeGenerator(self.seed)
            
            total_hexes = 0
            # Generate hexes for each continent
            for continent in generator.continents:
                print(f"Loading {continent.continent_id} continent (radius {continent.radius})...")
                
                # Generate all hexes within the continent radius
                for ring in range(continent.radius + 1):
                    # Get all hexes at this distance from the continent center
                    if ring == 0:
                        # Center hex
                        q, r, s = continent.center_q, continent.center_r, continent.center_s
                        if (q, r, s) not in self.hex_data:
                            terrain = generator.select_biome(q, r, s)
                            self.hex_data[(q, r, s)] = {
                                'q': q, 'r': r, 's': s,
                                'terrain': terrain,
                                'is_center': (q == 0 and r == 0 and s == 0)
                            }
                            self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
                            total_hexes += 1
                    else:
                        # Generate ring of hexes at this distance
                        for angle_idx in range(6):
                            # Direction vectors for hex grid
                            directions = [(1, 0, -1), (1, -1, 0), (0, -1, 1), 
                                        (-1, 0, 1), (-1, 1, 0), (0, 1, -1)]
                            
                            # Starting hex for this edge of the ring
                            start_q = continent.center_q + directions[angle_idx][0] * ring
                            start_r = continent.center_r + directions[angle_idx][1] * ring
                            start_s = continent.center_s + directions[angle_idx][2] * ring
                            
                            # Move along the edge
                            next_dir_idx = (angle_idx + 2) % 6
                            for step in range(ring):
                                q = start_q + directions[next_dir_idx][0] * step
                                r = start_r + directions[next_dir_idx][1] * step
                                s = start_s + directions[next_dir_idx][2] * step
                                
                                if (q, r, s) not in self.hex_data:
                                    terrain = generator.select_biome(q, r, s)
                                    self.hex_data[(q, r, s)] = {
                                        'q': q, 'r': r, 's': s,
                                        'terrain': terrain,
                                        'is_center': (q == 0 and r == 0 and s == 0)
                                    }
                                    self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
                                    total_hexes += 1
            
            print(f"Loaded {total_hexes} hexes across {len(generator.continents)} continents")
            
            # Fit view to show all loaded continents
            self.fit_map_to_view()
            
        except Exception as e:
            print(f"Error in load_all_continents: {e}")
            import traceback
            traceback.print_exc()
    
    def update_brush_preview(self, mouse_x, mouse_y):
        """Update which hexes would be painted by the brush"""
        self.mouse_x = mouse_x
        self.mouse_y = mouse_y
        self.brush_preview_hexes.clear()
        
        # Convert mouse position to hex coordinates
        world_x = (mouse_x - self.camera_x - self.map_area.x) / self.zoom
        world_y = (mouse_y - self.camera_y - self.map_area.y) / self.zoom
        
        # Convert pixel to cube coordinates
        hex_size = self.hex_size
        q = (2.0/3.0 * world_x) / hex_size
        r = (-1.0/3.0 * world_x + math.sqrt(3)/3.0 * world_y) / hex_size
        s = -q - r
        
        # Round to nearest hex coordinates
        q_center = round(q)
        r_center = round(r)
        s_center = round(s)
        
        # Handle rounding errors
        q_diff = abs(q - q_center)
        r_diff = abs(r - r_center) 
        s_diff = abs(s - s_center)
        
        if q_diff > r_diff and q_diff > s_diff:
            q_center = -r_center - s_center
        elif r_diff > s_diff:
            r_center = -q_center - s_center
        else:
            s_center = -q_center - r_center
        
        # Generate brush area around the center hex
        for ring_radius in range(0, self.brush_size + 1):
            if ring_radius == 0:
                # Center hex
                self.brush_preview_hexes.add((q_center, r_center, s_center))
            else:
                # Ring of hexes
                for q in range(q_center - ring_radius, q_center + ring_radius + 1):
                    for r in range(max(r_center - ring_radius, -q - s_center - ring_radius), 
                                  min(r_center + ring_radius, -q - s_center + ring_radius) + 1):
                        s = -q - r
                        
                        # Only include hexes that are exactly at this ring distance
                        if max(abs(q - q_center), abs(r - r_center), abs(s - s_center)) == ring_radius:
                            self.brush_preview_hexes.add((q, r, s))
    
    def paint_hexes(self):
        """Paint hexes at the current brush location"""
        if not self.MinecraftBiomeGenerator or not self.brush_preview_hexes:
            return
        
        generator = self.MinecraftBiomeGenerator(self.seed)
        generated_count = 0
        
        # Generate only the hexes under the brush that don't already exist
        for q, r, s in self.brush_preview_hexes:
            if (q, r, s) not in self.hex_data:
                terrain = generator.select_biome(q, r, s)
                
                self.hex_data[(q, r, s)] = {
                    'q': q, 'r': r, 's': s,
                    'terrain': terrain,
                    'is_center': (q == 0 and r == 0 and s == 0)
                }
                
                self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
                generated_count += 1
        
        if generated_count > 0:
            print(f"Painted {generated_count} hexes")
            
            # Redraw to show the new hexes immediately
            self.draw_map()
            self.draw_ui()
            pygame.display.flip()
    
    def draw_brush_preview(self):
        """Draw a preview of where the brush will paint"""
        if not self.brush_preview_hexes:
            return
            
        # Draw preview hexes with a translucent outline
        for q, r, s in self.brush_preview_hexes:
            # Don't show preview for hexes that already exist
            if (q, r, s) not in self.hex_data:
                x, y = self.get_hex_screen_pos(q, r)
                
                # Only draw if hex is visible on screen
                if (self.map_area.left <= x <= self.map_area.right and 
                    self.map_area.top <= y <= self.map_area.bottom):
                    
                    hex_size = self.hex_size * self.zoom
                    
                    # Draw a faint outline showing where hex will be painted
                    points = []
                    for i in range(6):
                        angle = math.pi / 3 * i
                        px = x + hex_size * math.cos(angle)
                        py = y + hex_size * math.sin(angle)
                        points.append((px, py))
                    
                    # Draw solid preview outline (avoid alpha issues)
                    pygame.draw.polygon(self.screen, (200, 200, 200), points, 2)
    
    def draw_continent_outlines(self):
        """Draw outlines showing continent boundaries"""
        if not hasattr(self, 'MinecraftBiomeGenerator') or not self.MinecraftBiomeGenerator:
            return
            
        # Get a generator instance to access continent data
        try:
            generator = self.MinecraftBiomeGenerator(self.seed)
            
            # Different colors for different continents
            continent_colors = [
                (100, 150, 255),  # Light blue - main
                (150, 255, 150),  # Light green - north
                (255, 150, 150),  # Light red - northeast
                (255, 255, 150),  # Light yellow - southeast
                (255, 150, 255),  # Light magenta - south
                (150, 255, 255),  # Light cyan - southwest
            ]
            
            for i, continent in enumerate(generator.continents):
                color = continent_colors[i % len(continent_colors)]
                
                # Draw continent boundary circle (approximate)
                center_x, center_y = self.get_hex_screen_pos(continent.center_q, continent.center_r)
                
                # Only draw if continent center is reasonably close to view
                if (self.map_area.left - 500 <= center_x <= self.map_area.right + 500 and 
                    self.map_area.top - 500 <= center_y <= self.map_area.bottom + 500):
                    
                    # Calculate screen radius
                    radius_in_pixels = continent.radius * self.hex_size * self.zoom * 2
                    
                    # Draw circle outline
                    if radius_in_pixels > 5:  # Only draw if big enough to see
                        pygame.draw.circle(self.screen, color, (int(center_x), int(center_y)), int(radius_in_pixels), 2)
                        
                        # Draw continent label
                        label_text = self.font_small.render(continent.continent_id.title(), True, color)
                        label_rect = label_text.get_rect(center=(center_x, center_y - radius_in_pixels - 20))
                        self.screen.blit(label_text, label_rect)
                        
        except Exception as e:
            pass  # Silently fail if continents can't be drawn
    
    def draw_hex(self, surface, x, y, size, color, border_color=None):
        """Draw a hexagon at the given position"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.append((px, py))
        
        pygame.draw.polygon(surface, color, points)
        if border_color:
            pygame.draw.polygon(surface, border_color, points, 1)
    
    def get_hex_screen_pos(self, q, r):
        """Get screen position for hex at cube coordinates"""
        # Convert cube to pixel coordinates
        hex_size = self.hex_size * self.zoom
        
        # Standard hex-to-pixel conversion
        x = hex_size * (3.0/2.0 * q) + self.camera_x + self.map_area.x
        y = hex_size * (math.sqrt(3)/2.0 * q + math.sqrt(3) * r) + self.camera_y + self.map_area.y
        
        return x, y
    
    def get_hex_at_screen_pos(self, screen_x, screen_y):
        """Get hex coordinates from screen position"""
        if not self.hex_data:
            return None
        
        # Convert screen to world coordinates
        world_x = (screen_x - self.camera_x) / self.zoom
        world_y = (screen_y - self.camera_y) / self.zoom
        
        # Convert pixel to cube coordinates (approximate)
        hex_size = self.hex_size
        
        q = (2.0/3.0 * world_x) / hex_size
        r = (-1.0/3.0 * world_x + math.sqrt(3)/3.0 * world_y) / hex_size
        
        # Round to nearest hex
        q_round = round(q)
        r_round = round(r)
        s_round = round(-q - r)
        
        # Check if this hex exists in our data
        hex_coords = (q_round, r_round, s_round)
        if hex_coords in self.hex_data:
            return hex_coords
        
        # Check nearby hexes if exact match not found
        min_distance = float('inf')
        closest_hex = None
        
        for (q_check, r_check, s_check) in self.hex_data.keys():
            hex_x, hex_y = self.get_hex_screen_pos(q_check, r_check)
            screen_hex_x = hex_x - self.map_area.x
            screen_hex_y = hex_y - self.map_area.y
            
            distance = math.sqrt((screen_x - screen_hex_x)**2 + (screen_y - screen_hex_y)**2)
            if distance < self.hex_size * self.zoom and distance < min_distance:
                min_distance = distance
                closest_hex = (q_check, r_check, s_check)
        
        return closest_hex
    
    def update_tooltip(self, pos):
        """Update tooltip for hex under mouse"""
        if self.map_area.collidepoint(pos):
            map_x = pos[0] - self.map_area.x
            map_y = pos[1] - self.map_area.y
            hex_info = self.get_hex_at_screen_pos(map_x, map_y)
            self.tooltip_hex = hex_info
            self.tooltip_pos = pos
        else:
            self.tooltip_hex = None
    
    def draw_map(self):
        """Draw the hex map"""
        if not self.hex_data:
            return
        
        # Clear map area
        pygame.draw.rect(self.screen, self.COLORS['background'], self.map_area)
        
        # Draw continent outlines first (behind everything)
        self.draw_continent_outlines()
        
        # Draw brush preview (behind hexes)
        self.draw_brush_preview()
        
        # Draw hexes
        for (q, r, s), hex_data in self.hex_data.items():
            x, y = self.get_hex_screen_pos(q, r)
            
            # Only draw if hex is visible on screen
            if (x + self.hex_size * self.zoom >= self.map_area.x and 
                x - self.hex_size * self.zoom <= self.map_area.x + self.map_area.width and
                y + self.hex_size * self.zoom >= self.map_area.y and 
                y - self.hex_size * self.zoom <= self.map_area.y + self.map_area.height):
                
                terrain = hex_data['terrain']
                color = self.COLORS.get(terrain, (128, 128, 128))
                size = self.hex_size * self.zoom
                
                # Draw hex with border for better visibility
                if hex_data.get('is_center', False):
                    # Special red border for center hex
                    border_color = (255, 0, 0) if self.zoom > 0.3 else (255, 100, 100)
                    # Draw thicker border for center
                    self.draw_hex(self.screen, x, y, size, color, border_color)
                    if self.zoom > 0.8:
                        # Draw inner border too
                        self.draw_hex(self.screen, x, y, size * 0.9, color, border_color)
                else:
                    border_color = (0, 0, 0) if self.zoom > 0.5 else None
                    self.draw_hex(self.screen, x, y, size, color, border_color)
    
    def draw_ui(self):
        """Draw the UI panel - structured with buttons first, then info"""
        # Draw UI background
        ui_rect = pygame.Rect(0, 0, self.ui_panel_width, self.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, self.COLORS['ui_bg'], ui_rect)
        pygame.draw.line(self.screen, self.COLORS['ui_border'], 
                        (self.ui_panel_width, 0), (self.ui_panel_width, self.SCREEN_HEIGHT), 2)
        
        y_pos = 15
        mouse_pos = pygame.mouse.get_pos()
        
        # Title
        title = self.font_large.render("Hex Generator", True, self.COLORS['text'])
        self.screen.blit(title, (10, y_pos))
        y_pos += 45
        
        # === BUTTONS FIRST ===
        
        # Generation section
        gen_header = self.font_medium.render("GENERATION", True, (200, 200, 255))
        self.screen.blit(gen_header, (10, y_pos))
        y_pos += 30
        
        # Draw generation buttons
        generation_buttons = [
            ('generate', 'Generate Map', (60, 120, 60)),
            ('load_continents', 'Load Continents', (80, 80, 120)),  
            ('set_seed', 'Set Seed', (80, 80, 120)),
            ('random_seed', 'Random Seed', (80, 80, 120))
        ]
        
        for button_name, label, base_color in generation_buttons:
            if button_name in self.buttons:
                button_rect = self.buttons[button_name]
                
                # Button color
                if button_rect.collidepoint(mouse_pos):
                    color = tuple(min(255, c + 30) for c in base_color)
                else:
                    color = base_color
                
                # Draw button
                pygame.draw.rect(self.screen, color, button_rect)
                pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
                
                # Draw text
                text_surface = self.font_small.render(label, True, self.COLORS['text'])
                text_rect = text_surface.get_rect(center=button_rect.center)
                self.screen.blit(text_surface, text_rect)
        
        # Export Controls section (removed view controls)
        y_pos += 170  # Keep title position away from generation buttons
        export_header = self.font_medium.render("EXPORT CONTROLS", True, (100, 255, 100))
        self.screen.blit(export_header, (10, y_pos))
        y_pos += 10   # Minimal space after header - bring buttons closer to title
        
        export_buttons = [
            ('save_json', 'Save JSON', (60, 100, 60)),
            ('copy_game', 'Copy to Game', (60, 100, 60)),
            ('screenshot', 'Screenshot (F12)', (100, 60, 100))
        ]
        
        for button_name, label, base_color in export_buttons:
            if button_name in self.buttons:
                button_rect = self.buttons[button_name]
                
                if button_rect.collidepoint(mouse_pos):
                    color = tuple(min(255, c + 30) for c in base_color)
                else:
                    color = base_color
                
                pygame.draw.rect(self.screen, color, button_rect)
                pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
                
                text_surface = self.font_small.render(label, True, self.COLORS['text'])
                text_rect = text_surface.get_rect(center=button_rect.center)
                self.screen.blit(text_surface, text_rect)
        
        # === INFO AT BOTTOM ===
        
        # Calculate positions from bottom up
        controls_height = 115  # Height for controls section
        info_height = 100      # Height for map info section
        terrain_height = min(120, len(self.biome_counts) * 16 + 35) if self.biome_counts else 0
        
        # Controls section at very bottom
        controls_y = self.SCREEN_HEIGHT - controls_height
        controls_header = self.font_medium.render("CONTROLS", True, (180, 255, 180))
        self.screen.blit(controls_header, (10, controls_y))
        controls_y += 25
        
        controls_rect = pygame.Rect(10, controls_y, 260, 90)
        pygame.draw.rect(self.screen, (30, 35, 40), controls_rect)
        pygame.draw.rect(self.screen, self.COLORS['ui_border'], controls_rect, 1)
        
        controls_y += 10
        controls_text = [
            "Wheel: Zoom | Drag: Pan",
            "WASD/Arrows: Navigate",
            "R: Reset | F12: Screenshot",
            "Click hex: Details"
        ]
        
        for text in controls_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (15, controls_y))
            controls_y += 18
        
        # Terrain Distribution section above controls
        if self.biome_counts:
            terrain_start_y = self.SCREEN_HEIGHT - controls_height - terrain_height - 10
            terrain_header = self.font_medium.render("TERRAIN", True, (255, 180, 180))
            self.screen.blit(terrain_header, (10, terrain_start_y))
            terrain_y = terrain_start_y + 25
            
            # Terrain box
            terrain_box_height = min(120, len(self.biome_counts) * 16 + 10)
            terrain_rect = pygame.Rect(10, terrain_y, 260, terrain_box_height)
            pygame.draw.rect(self.screen, (30, 35, 40), terrain_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], terrain_rect, 1)
            
            terrain_y += 8
            total = len(self.hex_data)
            for terrain, count in sorted(self.biome_counts.items(), key=lambda x: x[1], reverse=True):
                if terrain_y > self.SCREEN_HEIGHT - controls_height - 20:  # Dynamic overflow check
                    break
                    
                percent = (count / total) * 100 if total > 0 else 0
                
                # Color indicator
                color = self.COLORS.get(terrain, (128, 128, 128))
                pygame.draw.rect(self.screen, color, (15, terrain_y, 12, 12))
                pygame.draw.rect(self.screen, (255, 255, 255), (15, terrain_y, 12, 12), 1)
                
                # Text
                text = f"{terrain.title()}: {percent:.1f}%"
                surface = self.font_small.render(text, True, self.COLORS['text'])
                self.screen.blit(surface, (32, terrain_y))
                terrain_y += 16
        
        # Map info section above terrain/controls (moved 10px up)
        info_start_y = self.SCREEN_HEIGHT - controls_height - terrain_height - info_height - 30
        settings_header = self.font_medium.render("MAP INFO", True, (255, 200, 255))
        self.screen.blit(settings_header, (10, info_start_y))
        info_y = info_start_y + 25
        
        # Settings box
        settings_rect = pygame.Rect(10, info_y, 260, 100)
        pygame.draw.rect(self.screen, (30, 35, 40), settings_rect)
        pygame.draw.rect(self.screen, self.COLORS['ui_border'], settings_rect, 1)
        
        info_y += 10
        expected_hexes = len(self.hex_data)
        settings_info = [
            f"Shape: Hexagonal",
            f"Brush Size: {self.brush_size}",  
            f"Seed: {self.seed}",
            f"Hexes: {len(self.hex_data)}/{expected_hexes}",
            f"Center: Red border at (0,0,0)"
        ]
        
        for info in settings_info:
            surface = self.font_small.render(info, True, self.COLORS['text'])
            self.screen.blit(surface, (15, info_y))
            info_y += 18
    
    def draw_tooltip(self):
        """Draw tooltip for hex under mouse"""
        if self.tooltip_hex and self.tooltip_hex in self.hex_data:
            hex_data = self.hex_data[self.tooltip_hex]
            q, r, s = self.tooltip_hex
            
            tooltip_text = [
                f"Cube: q={q}, r={r}, s={s}",
                f"Terrain: {hex_data['terrain'].title()}",
                f"Distance: {max(abs(q), abs(r), abs(s))}"
            ]
            
            # Calculate tooltip size
            max_width = 0
            total_height = 0
            text_surfaces = []
            
            for text in tooltip_text:
                surface = self.font_small.render(text, True, self.COLORS['text'])
                text_surfaces.append(surface)
                max_width = max(max_width, surface.get_width())
                total_height += surface.get_height()
            
            # Position tooltip
            tooltip_width = max_width + 10
            tooltip_height = total_height + 10
            x = self.tooltip_pos[0] + 15
            y = self.tooltip_pos[1] - tooltip_height - 5
            
            # Keep tooltip on screen
            if x + tooltip_width > self.SCREEN_WIDTH:
                x = self.tooltip_pos[0] - tooltip_width - 15
            if y < 0:
                y = self.tooltip_pos[1] + 15
            
            # Draw tooltip background
            tooltip_rect = pygame.Rect(x, y, tooltip_width, tooltip_height)
            pygame.draw.rect(self.screen, self.COLORS['ui_bg'], tooltip_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], tooltip_rect, 1)
            
            # Draw tooltip text
            text_y = y + 5
            for surface in text_surfaces:
                self.screen.blit(surface, (x + 5, text_y))
                text_y += surface.get_height()
    
    def reset_view(self):
        """Reset camera to center on hexagonal map"""
        if self.hex_data:
            # Center the camera on the hexagonal map
            map_diameter = self.brush_size * 4 * self.hex_size
            self.camera_x = self.map_area.width // 2 - map_diameter // 2
            self.camera_y = self.map_area.height // 2 - map_diameter // 2
            
            # Set zoom to fit the hexagonal map in the view
            self.zoom = min(
                self.map_area.width / (map_diameter * 1.5),
                self.map_area.height / (map_diameter * 1.5)
            )
            self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * 0.8))
    
    def fit_map_to_view(self):
        """Fit map to view with optimal zoom"""
        self.reset_view()
    
    # UI Dialog methods (using tkinter for simplicity)
    # Size is now fixed to chunk-based system - no longer needed
    
    def set_seed(self):
        """Set seed value"""
        try:
            # Temporarily hide pygame window
            pygame.display.iconify()
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            root.lift()
            root.focus_force()
            
            seed = simpledialog.askinteger("Seed", "Enter seed:", 
                                         initialvalue=self.seed, parent=root)
            if seed is not None:
                self.seed = seed
                
            root.destroy()
            
            # Restore pygame window
            pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            
        except Exception as e:
            print(f"Seed setting error: {e}")
            # Fallback to console input
            try:
                print(f"Current seed: {self.seed}")
                seed_input = input("Enter new seed: ").strip()
                if seed_input:
                    self.seed = int(seed_input)
            except:
                pass
    
    def show_hex_details(self, hex_coords):
        """Show detailed hex information"""
        if hex_coords not in self.hex_data:
            return
        
        hex_data = self.hex_data[hex_coords]
        q, r, s = hex_coords
        
        try:
            pygame.display.iconify()
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            root.lift()
            root.focus_force()
            
            messagebox.showinfo("Hex Details", 
                f"Cube Coordinates: q={q}, r={r}, s={s}\n"
                f"Terrain: {hex_data['terrain'].title()}\n"
                f"Distance from center: {max(abs(q), abs(r), abs(s))}",
                parent=root)
                
            root.destroy()
            pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
            
        except Exception as e:
            print(f"Hex details error: {e}")
            # Print to console as fallback
            print(f"Hex Details - Cube: q={q}, r={r}, s={s}, "
                  f"Terrain: {hex_data['terrain'].title()}, "
                  f"Distance: {max(abs(q), abs(r), abs(s))}")
    
    def save_json(self):
        """Save map as JSON"""
        if not self.hex_data:
            return
        
        root = tk.Tk()
        root.withdraw()
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            
            if filename:
                self.export_map_data(filename)
                messagebox.showinfo("Success", f"Saved: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
        finally:
            root.destroy()
    
    def copy_to_game(self):
        """Copy to game maps folder"""
        if not self.hex_data:
            return
        
        try:
            os.makedirs("maps", exist_ok=True)
            filename = f"maps/generated_pygame_{self.seed}.json"
            self.export_map_data(filename)
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Success", f"Copied to: {filename}\nLoad in game with 'Load Map'")
            root.destroy()
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Copy failed: {e}")
            root.destroy()
    
    def export_map_data(self, filename):
        """Export map data to JSON file with multi-continent support"""
        export_data = {
            "seed": self.seed,
            "world_type": "multi-continent",
            "dimensions": {"shape": "paint-brush", "brush_size": self.brush_size},
            "continents": [],
            "hexes": {}
        }
        
        # Add continent information
        if hasattr(self, 'MinecraftBiomeGenerator') and self.MinecraftBiomeGenerator:
            try:
                generator = self.MinecraftBiomeGenerator(self.seed)
                for continent in generator.continents:
                    export_data["continents"].append({
                        "continent_id": continent.continent_id,
                        "center": [continent.center_q, continent.center_r, continent.center_s],
                        "radius": continent.radius,
                        "coastal_zone": continent.coastal_zone
                    })
            except Exception as e:
                print(f"Error exporting continent data: {e}")
        
        for (q, r, s), hex_data in self.hex_data.items():
            key = f"{q},{r},{s}"
            export_data["hexes"][key] = {
                "q": q,
                "r": r,
                "s": s,
                "terrain": hex_data['terrain'],
                "description": f"A generated {hex_data['terrain']}",
                "explored": False,
                "visible": False
            }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    def take_screenshot(self):
        """Take a screenshot of the current screen"""
        try:
            # Create screenshots directory
            os.makedirs("screenshots", exist_ok=True)
            
            # Generate timestamp filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshots/hex_generator_{timestamp}.png"
            
            # Save screenshot
            pygame.image.save(self.screen, filename)
            
            print(f"📸 Screenshot saved: {filename}")
            
            # Show visual feedback - briefly flash the screen border
            original_bg = self.COLORS['ui_bg']
            self.COLORS['ui_bg'] = (100, 255, 100)  # Green flash
            
            # Redraw just the UI border for feedback
            ui_rect = pygame.Rect(0, 0, self.ui_panel_width, self.SCREEN_HEIGHT)
            pygame.draw.rect(self.screen, self.COLORS['ui_bg'], ui_rect, 3)
            pygame.display.flip()
            
            # Wait briefly then restore
            pygame.time.wait(150)
            self.COLORS['ui_bg'] = original_bg
            
            return filename
            
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            return None
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.handle_events()
            self.update_keyboard_navigation()
            
            # Clear screen
            self.screen.fill(self.COLORS['background'])
            
            # Draw everything
            self.draw_map()
            self.draw_ui()
            self.draw_tooltip()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()

def main():
    """Main function"""
    print("Starting Pygame Hex Map Generator...")
    
    try:
        app = PygameHexGenerator()
        app.run()
    except Exception as e:
        print(f"Failed to start: {e}")

if __name__ == "__main__":
    main()