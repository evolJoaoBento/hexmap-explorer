"""
Hexagonal Chunk-based Map Generator
Generates world in hexagonal chunks with directional expansion
"""
import pygame
import math
import random
import json
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from collections import defaultdict

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

class HexChunk:
    """Represents a hexagonal chunk of hexes"""
    def __init__(self, chunk_q, chunk_r, chunk_s, size=510):
        self.chunk_q = chunk_q
        self.chunk_r = chunk_r
        self.chunk_s = chunk_s
        self.size = size  # Number of hexes from center to edge
        self.hexes = {}  # Local hex storage
        self.generated = False

class HexChunkGenerator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Screen settings
        self.SCREEN_WIDTH = 1400
        self.SCREEN_HEIGHT = 900
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Hexagonal Chunk World Generator")
        
        # Colors
        self.COLORS = {
            'background': (15, 20, 25),
            'ui_bg': (30, 35, 40),
            'ui_border': (80, 90, 100),
            'text': (255, 255, 255),
            'button': (50, 60, 70),
            'button_hover': (70, 80, 90),
            'button_active': (90, 110, 130),
            'expand_button': (40, 100, 60),
            'expand_button_hover': (50, 130, 80),
            'chunk_border': (255, 255, 100),
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
        self.font_tiny = pygame.font.Font(None, 16)
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        # Chunk settings - reduced size to prevent crashes
        self.hexes_per_chunk = 30  # Hexes from center to edge of chunk (much more reasonable)
        self.chunk_actual_size = self.hexes_per_chunk * 2 + 1  # Full diameter (61 hexes)
        self.chunks = {}  # Dictionary of generated chunks
        self.seed = random.randint(1, 1000000)
        
        # All hex data across all chunks
        self.all_hexes = {}  # Global hex storage
        self.biome_counts = defaultdict(int)
        
        # View settings
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 0.5  # Start zoomed out to see chunks
        self.min_zoom = 0.01  # Very zoomed out to see massive world
        self.max_zoom = 5.0
        self.hex_size = 3  # Smaller hex size for massive maps
        
        # Navigation
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.keys_pressed = set()
        
        # UI elements
        self.ui_panel_width = 350
        self.map_area = pygame.Rect(self.ui_panel_width, 0, 
                                  self.SCREEN_WIDTH - self.ui_panel_width, 
                                  self.SCREEN_HEIGHT)
        
        # Buttons
        self.buttons = {}
        self.expand_buttons = {}  # Directional expansion buttons
        self.create_ui_elements()
        
        # Initialize biome generator
        self.MinecraftBiomeGenerator, self.TERRAIN_TYPES = safe_import()
        
        # Clock for smooth animation
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Tooltip
        self.tooltip_hex = None
        self.tooltip_pos = (0, 0)
        
        # Performance settings
        self.max_visible_hexes = 10000  # Limit rendering for performance
        self.show_chunk_borders = True
        
        # Don't generate initial chunk automatically - wait for user action
        # self.generate_chunk(0, 0, 0)
    
    def create_ui_elements(self):
        """Create UI buttons and input areas"""
        button_width = 120
        button_height = 30
        margin = 10
        y_pos = 20
        
        # Title and info area
        y_pos += 40
        
        # Generate center chunk button
        self.buttons['generate_center'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        # Clear world button
        self.buttons['clear_world'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # Expansion controls title
        y_pos += 20
        
        # Hexagonal arrangement of expansion buttons
        expand_button_size = 40
        center_x = self.ui_panel_width // 2
        center_y = y_pos + 60
        
        # Create 6 directional buttons in hex pattern
        directions = [
            ('NE', 1, -1, 0),   # Northeast
            ('E', 1, 0, -1),    # East
            ('SE', 0, 1, -1),   # Southeast
            ('SW', -1, 1, 0),   # Southwest
            ('W', -1, 0, 1),    # West
            ('NW', 0, -1, 1),   # Northwest
        ]
        
        for i, (name, q, r, s) in enumerate(directions):
            angle = math.pi / 3 * i - math.pi / 6  # Start from NE
            x = center_x + math.cos(angle) * 50 - expand_button_size // 2
            y = center_y + math.sin(angle) * 50 - expand_button_size // 2
            self.expand_buttons[name] = {
                'rect': pygame.Rect(x, y, expand_button_size, expand_button_size),
                'direction': (q, r, s)
            }
        
        y_pos = center_y + 80
        
        # Settings
        y_pos += margin * 2
        self.buttons['set_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['random_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['toggle_borders'] = pygame.Rect(margin, y_pos, button_width + 30, button_height)
        y_pos += button_height + margin * 2
        
        # Navigation controls
        self.buttons['reset_view'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['fit_map'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # Export buttons
        self.buttons['save_json'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['copy_game'] = pygame.Rect(margin, y_pos, button_width, button_height)
    
    def get_chunk_coordinates(self, hex_q, hex_r, hex_s):
        """Get which chunk a hex belongs to"""
        # Simple chunk division based on distance from origin
        chunk_size = self.hexes_per_chunk * 2
        chunk_q = hex_q // chunk_size
        chunk_r = hex_r // chunk_size
        chunk_s = -chunk_q - chunk_r
        return chunk_q, chunk_r, chunk_s
    
    def generate_chunk(self, chunk_q, chunk_r, chunk_s):
        """Generate a hexagonal chunk of hexes"""
        try:
            if (chunk_q, chunk_r, chunk_s) in self.chunks:
                return  # Already generated
            
            if not self.MinecraftBiomeGenerator:
                print("Warning: Biome generator not available, using fallback")
                self.generate_chunk_simple(chunk_q, chunk_r, chunk_s)
                return
            
            print(f"Generating chunk ({chunk_q}, {chunk_r}, {chunk_s})...")
            
            # Create chunk
            chunk = HexChunk(chunk_q, chunk_r, chunk_s, self.hexes_per_chunk)
            generator = self.MinecraftBiomeGenerator(self.seed + chunk_q * 1000 + chunk_r * 100 + chunk_s * 10)
            
            # Calculate chunk center in world coordinates
            # Space chunks apart properly
            chunk_spacing = self.hexes_per_chunk * 2 + 5  # Add small gap between chunks
            chunk_center_q = chunk_q * chunk_spacing
            chunk_center_r = chunk_r * chunk_spacing  
            chunk_center_s = -chunk_center_q - chunk_center_r
            
            # Generate hexes in hexagonal pattern within chunk
            generated_count = 0
            
            # Generate center hex
            terrain = generator.select_biome(chunk_center_q, chunk_center_r, chunk_center_s)
            hex_data = {
                'q': chunk_center_q, 'r': chunk_center_r, 's': chunk_center_s,
                'terrain': terrain,
                'chunk': (chunk_q, chunk_r, chunk_s)
            }
            chunk.hexes[(chunk_center_q, chunk_center_r, chunk_center_s)] = hex_data
            self.all_hexes[(chunk_center_q, chunk_center_r, chunk_center_s)] = hex_data
            self.biome_counts[terrain] += 1
            generated_count += 1
            
            # Generate rings of hexes
            for radius in range(1, self.hexes_per_chunk + 1):
                # Start position for this ring
                ring_q = chunk_center_q + radius
                ring_r = chunk_center_r - radius
                ring_s = chunk_center_s
                
                # Direction vectors for hex neighbors
                directions = [
                    (-1, 1, 0),  # Northwest
                    (-1, 0, 1),  # West
                    (0, -1, 1),  # Southwest
                    (1, -1, 0),  # Southeast
                    (1, 0, -1),  # East
                    (0, 1, -1),  # Northeast
                ]
                
                # Walk around the ring
                for direction_idx in range(6):
                    dq, dr, ds = directions[direction_idx]
                    
                    for step in range(radius):
                        # Generate this hex
                        terrain = generator.select_biome(ring_q, ring_r, ring_s)
                        hex_data = {
                            'q': ring_q, 'r': ring_r, 's': ring_s,
                            'terrain': terrain,
                            'chunk': (chunk_q, chunk_r, chunk_s)
                        }
                        
                        chunk.hexes[(ring_q, ring_r, ring_s)] = hex_data
                        self.all_hexes[(ring_q, ring_r, ring_s)] = hex_data
                        self.biome_counts[terrain] += 1
                        generated_count += 1
                        
                        # Move to next hex in this direction
                        ring_q += dq
                        ring_r += dr
                        ring_s += ds
        
            chunk.generated = True
            self.chunks[(chunk_q, chunk_r, chunk_s)] = chunk
            
            # Calculate expected hex count
            expected_count = 1 + 3 * self.hexes_per_chunk * (self.hexes_per_chunk + 1)
            
            print(f"Generated {generated_count} hexes in chunk ({chunk_q}, {chunk_r}, {chunk_s})")
            print(f"Total world size: {len(self.all_hexes)} hexes across {len(self.chunks)} chunks")
            
        except Exception as e:
            print(f"Error generating chunk ({chunk_q}, {chunk_r}, {chunk_s}): {e}")
            import traceback
            traceback.print_exc()
    
    def generate_chunk_simple(self, chunk_q, chunk_r, chunk_s):
        """Simple fallback chunk generator"""
        if (chunk_q, chunk_r, chunk_s) in self.chunks:
            return
        
        print(f"Generating chunk ({chunk_q}, {chunk_r}, {chunk_s}) with simple generator...")
        
        chunk = HexChunk(chunk_q, chunk_r, chunk_s, self.hexes_per_chunk)
        random.seed(self.seed + chunk_q * 1000 + chunk_r * 100 + chunk_s * 10)
        
        terrains = ['water', 'forest', 'plains', 'mountains', 'desert', 'hills', 'swamp', 'tundra']
        
        # Calculate chunk center
        chunk_spacing = self.hexes_per_chunk * 2 + 5
        chunk_center_q = chunk_q * chunk_spacing
        chunk_center_r = chunk_r * chunk_spacing
        chunk_center_s = -chunk_center_q - chunk_center_r
        
        generated_count = 0
        
        # Generate center hex
        terrain = random.choice(terrains)
        hex_data = {
            'q': chunk_center_q, 'r': chunk_center_r, 's': chunk_center_s,
            'terrain': terrain,
            'chunk': (chunk_q, chunk_r, chunk_s)
        }
        self.all_hexes[(chunk_center_q, chunk_center_r, chunk_center_s)] = hex_data
        self.biome_counts[terrain] += 1
        generated_count += 1
        
        # Generate rings
        for radius in range(1, min(self.hexes_per_chunk + 1, 10)):  # Limit for testing
            ring_q = chunk_center_q + radius
            ring_r = chunk_center_r - radius
            ring_s = chunk_center_s
            
            directions = [(-1, 1, 0), (-1, 0, 1), (0, -1, 1), (1, -1, 0), (1, 0, -1), (0, 1, -1)]
            
            for direction_idx in range(6):
                dq, dr, ds = directions[direction_idx]
                
                for step in range(radius):
                    terrain = random.choice(terrains)
                    hex_data = {
                        'q': ring_q, 'r': ring_r, 's': ring_s,
                        'terrain': terrain,
                        'chunk': (chunk_q, chunk_r, chunk_s)
                    }
                    self.all_hexes[(ring_q, ring_r, ring_s)] = hex_data
                    self.biome_counts[terrain] += 1
                    generated_count += 1
                    
                    ring_q += dq
                    ring_r += dr
                    ring_s += ds
        
        chunk.generated = True
        self.chunks[(chunk_q, chunk_r, chunk_s)] = chunk
        
        print(f"Generated {generated_count} hexes in chunk ({chunk_q}, {chunk_r}, {chunk_s})")
        print(f"Total world size: {len(self.all_hexes)} hexes across {len(self.chunks)} chunks")
    
    def expand_world(self, direction_q, direction_r, direction_s):
        """Expand world by generating chunks in given direction"""
        # Find all existing chunk edges in that direction
        new_chunks = []
        
        for (chunk_q, chunk_r, chunk_s) in list(self.chunks.keys()):
            # Calculate adjacent chunk position
            new_chunk_q = chunk_q + direction_q
            new_chunk_r = chunk_r + direction_r
            new_chunk_s = chunk_s + direction_s
            
            # Check if this chunk already exists
            if (new_chunk_q, new_chunk_r, new_chunk_s) not in self.chunks:
                new_chunks.append((new_chunk_q, new_chunk_r, new_chunk_s))
        
        # Generate new chunks
        for chunk_coords in new_chunks:
            self.generate_chunk(*chunk_coords)
        
        print(f"Expanded world in direction ({direction_q}, {direction_r}, {direction_s})")
        print(f"Added {len(new_chunks)} new chunks")
    
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
                if event.button in [2, 3]:
                    self.dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx
                    self.camera_y += dy
                    self.last_mouse_pos = event.pos
                else:
                    self.update_tooltip(event.pos)
            
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
                    
                    # Adjust camera position
                    self.camera_x = map_mouse_x - (map_mouse_x - self.camera_x) * zoom_factor
                    self.camera_y = map_mouse_y - (map_mouse_y - self.camera_y) * zoom_factor
    
    def handle_left_click(self, pos):
        """Handle left mouse clicks"""
        # Check expansion buttons first
        for button_name, button_data in self.expand_buttons.items():
            if button_data['rect'].collidepoint(pos):
                self.expand_world(*button_data['direction'])
                return
        
        # Check UI buttons
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(pos):
                self.handle_button_click(button_name)
                return
        
        # Check map click for hex details
        if self.map_area.collidepoint(pos):
            map_x = pos[0] - self.map_area.x
            map_y = pos[1] - self.map_area.y
            hex_coords = self.get_hex_at_screen_pos(map_x, map_y)
            if hex_coords:
                self.show_hex_details(hex_coords)
    
    def handle_button_click(self, button_name):
        """Handle button clicks"""
        if button_name == 'generate_center':
            self.generate_chunk(0, 0, 0)
            self.reset_view()
        elif button_name == 'clear_world':
            self.chunks.clear()
            self.all_hexes.clear()
            self.biome_counts.clear()
        elif button_name == 'set_seed':
            self.set_seed()
        elif button_name == 'random_seed':
            self.seed = random.randint(1, 1000000)
        elif button_name == 'toggle_borders':
            self.show_chunk_borders = not self.show_chunk_borders
        elif button_name == 'reset_view':
            self.reset_view()
        elif button_name == 'fit_map':
            self.fit_map_to_view()
        elif button_name == 'save_json':
            self.save_json()
        elif button_name == 'copy_game':
            self.copy_to_game()
    
    def update_keyboard_navigation(self):
        """Handle keyboard navigation"""
        move_speed = 500 / max(0.1, self.zoom)
        
        if pygame.K_w in self.keys_pressed or pygame.K_UP in self.keys_pressed:
            self.camera_y += move_speed * (1/60)
        if pygame.K_s in self.keys_pressed or pygame.K_DOWN in self.keys_pressed:
            self.camera_y -= move_speed * (1/60)
        if pygame.K_a in self.keys_pressed or pygame.K_LEFT in self.keys_pressed:
            self.camera_x += move_speed * (1/60)
        if pygame.K_d in self.keys_pressed or pygame.K_RIGHT in self.keys_pressed:
            self.camera_x -= move_speed * (1/60)
        
        if pygame.K_r in self.keys_pressed:
            self.reset_view()
            self.keys_pressed.discard(pygame.K_r)
        
        if pygame.K_EQUALS in self.keys_pressed or pygame.K_PLUS in self.keys_pressed:
            self.zoom = min(self.max_zoom, self.zoom * 1.02)
        if pygame.K_MINUS in self.keys_pressed:
            self.zoom = max(self.min_zoom, self.zoom * 0.98)
    
    def get_hex_screen_pos(self, hex_q, hex_r):
        """Get screen position for hex at cube coordinates"""
        # Convert cube to offset coordinates for display
        col = hex_q + (hex_r - (hex_r & 1)) // 2
        row = hex_r
        
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        x = col * hex_width * self.zoom + self.camera_x + self.map_area.x
        y = row * hex_height * self.zoom + self.camera_y + self.map_area.y
        
        return x, y
    
    def get_hex_at_screen_pos(self, screen_x, screen_y):
        """Get hex coordinates from screen position"""
        if not self.all_hexes:
            return None
        
        # Convert screen to world coordinates
        world_x = (screen_x - self.camera_x) / self.zoom
        world_y = (screen_y - self.camera_y) / self.zoom
        
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        # Estimate grid position
        rough_col = int(world_x / hex_width)
        rough_row = int(world_y / hex_height)
        
        # Convert to cube coordinates
        rough_q = rough_col - (rough_row - (rough_row & 1)) // 2
        rough_r = rough_row
        rough_s = -rough_q - rough_r
        
        # Find closest hex
        min_distance = float('inf')
        closest_hex = None
        
        # Check nearby positions
        for dq in range(-2, 3):
            for dr in range(-2, 3):
                check_q = rough_q + dq
                check_r = rough_r + dr
                check_s = -check_q - check_r
                
                if (check_q, check_r, check_s) in self.all_hexes:
                    hex_x, hex_y = self.get_hex_screen_pos(check_q, check_r)
                    screen_hex_x = hex_x - self.map_area.x
                    screen_hex_y = hex_y - self.map_area.y
                    
                    distance = math.sqrt((screen_x - screen_hex_x)**2 + (screen_y - screen_hex_y)**2)
                    if distance < self.hex_size * self.zoom and distance < min_distance:
                        min_distance = distance
                        closest_hex = (check_q, check_r, check_s)
        
        return closest_hex
    
    def update_tooltip(self, pos):
        """Update tooltip for hex under mouse"""
        if self.map_area.collidepoint(pos):
            map_x = pos[0] - self.map_area.x
            map_y = pos[1] - self.map_area.y
            hex_coords = self.get_hex_at_screen_pos(map_x, map_y)
            self.tooltip_hex = hex_coords
            self.tooltip_pos = pos
        else:
            self.tooltip_hex = None
    
    def draw_hex(self, surface, x, y, size, color, border_color=None):
        """Draw a hexagon at the given position"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.append((px, py))
        
        pygame.draw.polygon(surface, color, points)
        if border_color and self.zoom > 0.3:  # Only show borders when zoomed in enough
            pygame.draw.polygon(surface, border_color, points, 1)
    
    def draw_map(self):
        """Draw the hex map"""
        if not self.all_hexes:
            return
        
        # Clear map area
        pygame.draw.rect(self.screen, self.COLORS['background'], self.map_area)
        
        # Count visible hexes for performance
        visible_count = 0
        
        # Draw chunk borders if enabled
        if self.show_chunk_borders and self.zoom > 0.05:
            for (chunk_q, chunk_r, chunk_s) in self.chunks.keys():
                # Get center of chunk
                chunk_center_q = chunk_q * (self.hexes_per_chunk * 3)
                chunk_center_r = chunk_r * (self.hexes_per_chunk * 3)
                
                x, y = self.get_hex_screen_pos(chunk_center_q, chunk_center_r)
                
                # Draw chunk border (simplified - just a large hex outline)
                if self.map_area.collidepoint(x, y):
                    chunk_size = self.hexes_per_chunk * self.hex_size * self.zoom
                    self.draw_hex(self.screen, x, y, chunk_size, None, self.COLORS['chunk_border'])
        
        # Draw hexes (limit for performance)
        for (hex_q, hex_r, hex_s), hex_data in self.all_hexes.items():
            if visible_count > self.max_visible_hexes:
                break
            
            x, y = self.get_hex_screen_pos(hex_q, hex_r)
            
            # Only draw if hex is visible on screen
            margin = self.hex_size * self.zoom * 2
            if (x >= self.map_area.x - margin and 
                x <= self.map_area.x + self.map_area.width + margin and
                y >= self.map_area.y - margin and 
                y <= self.map_area.y + self.map_area.height + margin):
                
                terrain = hex_data['terrain']
                color = self.COLORS.get(terrain, (128, 128, 128))
                size = self.hex_size * self.zoom
                
                # Only draw if hex is large enough to see
                if size > 0.5:
                    border_color = (0, 0, 0) if size > 2 else None
                    self.draw_hex(self.screen, x, y, size, color, border_color)
                    visible_count += 1
        
        # Draw visible hex count
        if visible_count >= self.max_visible_hexes:
            warning_text = self.font_medium.render(f"Rendering limited to {self.max_visible_hexes} hexes (zoom in for detail)", 
                                                  True, (255, 255, 100))
            self.screen.blit(warning_text, (self.map_area.x + 10, self.map_area.y + 10))
    
    def draw_ui(self):
        """Draw the UI panel"""
        # Draw UI background
        ui_rect = pygame.Rect(0, 0, self.ui_panel_width, self.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, self.COLORS['ui_bg'], ui_rect)
        pygame.draw.line(self.screen, self.COLORS['ui_border'], 
                        (self.ui_panel_width, 0), (self.ui_panel_width, self.SCREEN_HEIGHT), 2)
        
        # Draw title
        title = self.font_large.render("Hex Chunk Generator", True, self.COLORS['text'])
        self.screen.blit(title, (10, 10))
        
        # Draw current settings
        y_pos = 50
        settings_text = [
            f"Seed: {self.seed}",
            f"Zoom: {self.zoom:.3f}x",
            f"Chunks: {len(self.chunks)}",
            f"Total Hexes: {len(self.all_hexes):,}",
            f"Hexes/Chunk: ~{1 + 3 * self.hexes_per_chunk * (self.hexes_per_chunk + 1):,}"
        ]
        
        for text in settings_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, y_pos))
            y_pos += 20
        
        # Draw expansion controls title
        y_pos = 180
        expand_title = self.font_medium.render("Expand World:", True, self.COLORS['text'])
        self.screen.blit(expand_title, (10, y_pos))
        
        # Draw expansion buttons
        mouse_pos = pygame.mouse.get_pos()
        
        for button_name, button_data in self.expand_buttons.items():
            # Determine button color
            if button_data['rect'].collidepoint(mouse_pos):
                color = self.COLORS['expand_button_hover']
            else:
                color = self.COLORS['expand_button']
            
            # Draw hexagonal button
            center_x = button_data['rect'].centerx
            center_y = button_data['rect'].centery
            size = button_data['rect'].width // 2
            self.draw_hex(self.screen, center_x, center_y, size, color, self.COLORS['ui_border'])
            
            # Draw direction text
            text_surface = self.font_small.render(button_name, True, self.COLORS['text'])
            text_rect = text_surface.get_rect(center=(center_x, center_y))
            self.screen.blit(text_surface, text_rect)
        
        # Draw regular buttons
        button_labels = {
            'generate_center': 'Generate Center',
            'clear_world': 'Clear World',
            'set_seed': 'Set Seed',
            'random_seed': 'Random Seed',
            'toggle_borders': f"Borders: {'ON' if self.show_chunk_borders else 'OFF'}",
            'reset_view': 'Reset View',
            'fit_map': 'Fit Map',
            'save_json': 'Save JSON',
            'copy_game': 'Copy to Game'
        }
        
        for button_name, button_rect in self.buttons.items():
            # Determine button color
            if button_rect.collidepoint(mouse_pos):
                color = self.COLORS['button_hover']
            else:
                color = self.COLORS['button']
            
            # Draw button
            pygame.draw.rect(self.screen, color, button_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
            
            # Draw button text
            label = button_labels.get(button_name, button_name)
            text_surface = self.font_small.render(label, True, self.COLORS['text'])
            text_rect = text_surface.get_rect(center=button_rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Draw terrain distribution
        if self.biome_counts:
            dist_y = 550
            dist_title = self.font_medium.render("Terrain Distribution:", True, self.COLORS['text'])
            self.screen.blit(dist_title, (10, dist_y))
            dist_y += 25
            
            total = len(self.all_hexes)
            for terrain, count in sorted(self.biome_counts.items()):
                if dist_y > self.SCREEN_HEIGHT - 100:
                    break
                    
                percent = (count / total) * 100 if total > 0 else 0
                
                # Draw color square
                color = self.COLORS.get(terrain, (128, 128, 128))
                pygame.draw.rect(self.screen, color, (10, dist_y, 12, 12))
                pygame.draw.rect(self.screen, self.COLORS['ui_border'], (10, dist_y, 12, 12), 1)
                
                # Draw text
                text = f"{terrain[:8]}: {percent:.1f}%"
                surface = self.font_tiny.render(text, True, self.COLORS['text'])
                self.screen.blit(surface, (25, dist_y))
                dist_y += 15
        
        # Draw controls help
        help_y = self.SCREEN_HEIGHT - 130
        help_text = [
            "Controls:",
            "Wheel: Zoom | Drag: Pan",
            "WASD/Arrows: Navigate",
            "R: Reset | +/-: Zoom",
            "",
            "Click hex for details",
            "Click direction to expand"
        ]
        
        for text in help_text:
            surface = self.font_tiny.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, help_y))
            help_y += 15
    
    def draw_tooltip(self):
        """Draw tooltip for hex under mouse"""
        if self.tooltip_hex and self.tooltip_hex in self.all_hexes:
            hex_data = self.all_hexes[self.tooltip_hex]
            hex_q, hex_r, hex_s = self.tooltip_hex
            
            tooltip_text = [
                f"Cube: ({hex_q}, {hex_r}, {hex_s})",
                f"Terrain: {hex_data['terrain'].title()}",
                f"Chunk: {hex_data['chunk']}"
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
        """Reset camera to center on map"""
        self.camera_x = self.map_area.width // 2
        self.camera_y = self.map_area.height // 2
        self.zoom = 0.5
    
    def fit_map_to_view(self):
        """Fit map to view"""
        if not self.all_hexes:
            return
        
        # Find bounds of all hexes
        min_q = min_r = float('inf')
        max_q = max_r = float('-inf')
        
        for (hex_q, hex_r, hex_s) in self.all_hexes.keys():
            min_q = min(min_q, hex_q)
            max_q = max(max_q, hex_q)
            min_r = min(min_r, hex_r)
            max_r = max(max_r, hex_r)
        
        # Calculate size needed
        width_hexes = max_q - min_q
        height_hexes = max_r - min_r
        
        if width_hexes > 0 and height_hexes > 0:
            # Calculate zoom to fit
            zoom_x = self.map_area.width / (width_hexes * self.hex_size * 1.5)
            zoom_y = self.map_area.height / (height_hexes * self.hex_size * math.sqrt(3))
            
            self.zoom = min(self.max_zoom, max(self.min_zoom, min(zoom_x, zoom_y) * 0.8))
            
            # Center on map
            center_q = (min_q + max_q) / 2
            center_r = (min_r + max_r) / 2
            
            center_x, center_y = self.get_hex_screen_pos(center_q, center_r)
            self.camera_x = self.map_area.width // 2 - (center_x - self.map_area.x - self.camera_x)
            self.camera_y = self.map_area.height // 2 - (center_y - self.map_area.y - self.camera_y)
    
    def set_seed(self):
        """Set seed value"""
        try:
            print(f"Current seed: {self.seed}")
            seed_input = input("Enter new seed: ").strip()
            if seed_input:
                self.seed = int(seed_input)
                print(f"Seed set to: {self.seed}")
        except:
            pass
    
    def show_hex_details(self, hex_coords):
        """Show detailed hex information"""
        if hex_coords not in self.all_hexes:
            return
        
        hex_data = self.all_hexes[hex_coords]
        hex_q, hex_r, hex_s = hex_coords
        
        print(f"Hex Details - Cube: ({hex_q}, {hex_r}, {hex_s}), "
              f"Terrain: {hex_data['terrain'].title()}, "
              f"Chunk: {hex_data['chunk']}")
    
    def save_json(self):
        """Save map as JSON"""
        if not self.all_hexes:
            return
        
        try:
            filename = f"maps/generated_chunks_{self.seed}_{len(self.chunks)}chunks.json"
            self.export_map_data(filename)
            print(f"Saved: {filename}")
        except Exception as e:
            print(f"Save failed: {e}")
    
    def copy_to_game(self):
        """Copy to game maps folder"""
        if not self.all_hexes:
            return
        
        try:
            os.makedirs("maps", exist_ok=True)
            filename = f"maps/generated_chunks_{self.seed}.json"
            self.export_map_data(filename)
            print(f"Copied to: {filename}")
        except Exception as e:
            print(f"Copy failed: {e}")
    
    def export_map_data(self, filename):
        """Export map data to JSON file"""
        # Convert cube coordinates to offset for compatibility
        export_data = {
            "seed": self.seed,
            "chunks": len(self.chunks),
            "total_hexes": len(self.all_hexes),
            "hexes": {}
        }
        
        for (hex_q, hex_r, hex_s), hex_data in self.all_hexes.items():
            key = f"{hex_q},{hex_r},{hex_s}"
            export_data["hexes"][key] = {
                "q": hex_q,
                "r": hex_r,
                "s": hex_s,
                "terrain": hex_data['terrain'],
                "description": f"A generated {hex_data['terrain']}",
                "explored": False,
                "visible": False
            }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
    
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
    print("Starting Hexagonal Chunk World Generator...")
    print("Each chunk contains 30 hexes per side (approx 2,800 hexes per chunk)")
    print("Click directional buttons to expand the world!")
    
    try:
        app = HexChunkGenerator()
        app.run()
    except Exception as e:
        print(f"Failed to start: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()