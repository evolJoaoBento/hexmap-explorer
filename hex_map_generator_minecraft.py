"""
Hex Map Generator with Minecraft Biome System
Properly integrated 6D biome generation
"""
import pygame
import math
import random
import json
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Minecraft biome generator
try:
    from generation.minecraft_biomes import MinecraftBiomeGenerator
    from config.constants import TERRAIN_TYPES
    BIOME_SYSTEM_AVAILABLE = True
    print("Successfully loaded Minecraft biome generation system!")
except ImportError as e:
    print(f"Warning: Could not load Minecraft biome system: {e}")
    print("Using fallback terrain generation")
    BIOME_SYSTEM_AVAILABLE = False
    TERRAIN_TYPES = {}

class MinecraftHexGenerator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Screen settings
        self.SCREEN_WIDTH = 1300
        self.SCREEN_HEIGHT = 850
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Minecraft-Style Hex Map Generator")
        
        # Colors
        self.COLORS = {
            'background': (20, 25, 30),
            'ui_bg': (35, 40, 45),
            'ui_border': (80, 90, 100),
            'text': (255, 255, 255),
            'button': (50, 60, 70),
            'button_hover': (70, 80, 90),
            'button_active': (90, 110, 130),
            # Minecraft-inspired terrain colors
            'water': (64, 164, 223),        # Ocean blue
            'forest': (34, 139, 34),        # Forest green
            'plains': (144, 238, 144),      # Light green
            'mountains': (139, 137, 137),   # Stone gray
            'desert': (238, 203, 173),      # Sand color
            'hills': (160, 82, 45),         # Brown
            'swamp': (47, 79, 79),          # Dark teal
            'tundra': (176, 224, 230)       # Ice blue
        }
        
        # Fonts
        self.font_tiny = pygame.font.Font(None, 18)
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)
        
        # Map settings
        self.width = 30
        self.height = 30
        self.seed = random.randint(1, 1000000)
        self.hex_data = {}
        self.biome_counts = {}
        
        # Biome generator
        self.biome_generator = None
        if BIOME_SYSTEM_AVAILABLE:
            try:
                self.biome_generator = MinecraftBiomeGenerator(self.seed)
                print(f"Initialized Minecraft biome generator with seed {self.seed}")
            except Exception as e:
                print(f"Failed to initialize biome generator: {e}")
        
        # View settings
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.2
        self.max_zoom = 4.0
        self.hex_size = 20
        
        # Navigation
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        self.keys_pressed = set()
        
        # UI elements
        self.ui_panel_width = 350
        self.map_area = pygame.Rect(self.ui_panel_width, 0, 
                                  self.SCREEN_WIDTH - self.ui_panel_width, 
                                  self.SCREEN_HEIGHT)
        
        # Create buttons
        self.buttons = {}
        self.create_ui_elements()
        
        # Performance
        self.show_coordinates = True
        self.show_biome_params = False
        
        # Clock
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Tooltip
        self.tooltip_hex = None
        self.tooltip_pos = (0, 0)
    
    def create_ui_elements(self):
        """Create UI buttons"""
        button_width = 140
        button_height = 30
        margin = 10
        y_pos = 60
        
        # Generation controls
        self.buttons['generate'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['clear'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # Size controls
        self.buttons['size_small'] = pygame.Rect(margin, y_pos, 40, button_height)
        self.buttons['size_medium'] = pygame.Rect(margin + 50, y_pos, 40, button_height)
        self.buttons['size_large'] = pygame.Rect(margin + 100, y_pos, 40, button_height)
        self.buttons['size_xlarge'] = pygame.Rect(margin + 150, y_pos, 40, button_height)
        y_pos += button_height + margin
        
        # Seed controls
        self.buttons['random_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['set_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # View controls
        self.buttons['reset_view'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['toggle_coords'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['toggle_params'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # Export
        self.buttons['save_json'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['copy_game'] = pygame.Rect(margin, y_pos, button_width, button_height)
    
    def generate_map_minecraft(self):
        """Generate map using Minecraft biome system"""
        print(f"Generating {self.width}x{self.height} map with Minecraft biomes...")
        print(f"Seed: {self.seed}")
        
        self.hex_data.clear()
        self.biome_counts.clear()
        
        # Reinitialize generator with current seed
        self.biome_generator = MinecraftBiomeGenerator(self.seed)
        
        generated = 0
        errors = 0
        
        for col in range(self.width):
            for row in range(self.height):
                try:
                    # Convert to cube coordinates
                    q = col - (row - (row & 1)) // 2
                    r = row
                    s = -q - r
                    
                    # Generate biome
                    terrain = self.biome_generator.select_biome(q, r, s)
                    
                    # Get biome parameters for debug
                    params = self.biome_generator.get_biome_parameters(q, r, s)
                    
                    # Store hex data
                    self.hex_data[(col, row)] = {
                        'q': q, 'r': r, 's': s,
                        'col': col, 'row': row,
                        'terrain': terrain,
                        'temperature': params.temperature,
                        'humidity': params.humidity,
                        'continentalness': params.continentalness,
                        'erosion': params.erosion,
                        'weirdness': params.weirdness,
                        'depth': params.depth
                    }
                    
                    # Count biomes
                    self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
                    generated += 1
                    
                except Exception as e:
                    print(f"Error generating hex at ({col}, {row}): {e}")
                    errors += 1
                    # Use fallback terrain
                    self.hex_data[(col, row)] = {
                        'q': q, 'r': r, 's': s,
                        'col': col, 'row': row,
                        'terrain': 'plains',
                        'temperature': 0,
                        'humidity': 0,
                        'continentalness': 0,
                        'erosion': 0,
                        'weirdness': 0,
                        'depth': 0
                    }
        
        print(f"Generated {generated} hexes successfully, {errors} errors")
        print(f"Biome distribution: {dict(self.biome_counts)}")
    
    def generate_map_simple(self):
        """Simple fallback map generation"""
        print(f"Generating {self.width}x{self.height} map with simple generation...")
        
        self.hex_data.clear()
        self.biome_counts.clear()
        
        random.seed(self.seed)
        terrains = ['water', 'forest', 'plains', 'mountains', 'desert', 'hills', 'swamp', 'tundra']
        
        for col in range(self.width):
            for row in range(self.height):
                # Convert to cube coordinates
                q = col - (row - (row & 1)) // 2
                r = row
                s = -q - r
                
                # Simple terrain generation
                terrain = random.choice(terrains)
                
                # Store hex data
                self.hex_data[(col, row)] = {
                    'q': q, 'r': r, 's': s,
                    'col': col, 'row': row,
                    'terrain': terrain,
                    'temperature': 0,
                    'humidity': 0,
                    'continentalness': 0,
                    'erosion': 0,
                    'weirdness': 0,
                    'depth': 0
                }
                
                self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
        
        print(f"Generated {len(self.hex_data)} hexes with simple generation")
    
    def generate_map(self):
        """Generate map using available method"""
        if BIOME_SYSTEM_AVAILABLE and self.biome_generator:
            try:
                self.generate_map_minecraft()
            except Exception as e:
                print(f"Minecraft generation failed: {e}")
                print("Falling back to simple generation")
                self.generate_map_simple()
        else:
            self.generate_map_simple()
        
        # Reset view after generation
        self.reset_view()
    
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
                elif event.button in [2, 3]:  # Middle or right click
                    self.dragging = True
                    self.last_mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in [2, 3]:
                    self.dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx / self.zoom
                    self.camera_y += dy / self.zoom
                    self.last_mouse_pos = event.pos
                else:
                    self.update_tooltip(event.pos)
            
            elif event.type == pygame.MOUSEWHEEL:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if self.map_area.collidepoint(mouse_x, mouse_y):
                    old_zoom = self.zoom
                    if event.y > 0:
                        self.zoom = min(self.max_zoom, self.zoom * 1.2)
                    else:
                        self.zoom = max(self.min_zoom, self.zoom * 0.8)
                    
                    # Zoom at mouse position
                    zoom_factor = self.zoom / old_zoom
                    map_mouse_x = mouse_x - self.map_area.x
                    map_mouse_y = mouse_y - self.map_area.y
                    
                    self.camera_x = map_mouse_x - (map_mouse_x - self.camera_x) * zoom_factor
                    self.camera_y = map_mouse_y - (map_mouse_y - self.camera_y) * zoom_factor
    
    def handle_left_click(self, pos):
        """Handle left mouse button clicks"""
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(pos):
                self.handle_button_click(button_name)
                return
        
        # Check if clicked on map
        if self.map_area.collidepoint(pos):
            hex_coords = self.get_hex_at_screen_pos(pos[0] - self.map_area.x, pos[1] - self.map_area.y)
            if hex_coords and hex_coords in self.hex_data:
                hex_info = self.hex_data[hex_coords]
                print(f"\nClicked Hex Info:")
                print(f"  Position: ({hex_coords[0]}, {hex_coords[1]})")
                print(f"  Cube: q={hex_info['q']}, r={hex_info['r']}, s={hex_info['s']}")
                print(f"  Terrain: {hex_info['terrain']}")
                if self.show_biome_params:
                    print(f"  Temperature: {hex_info['temperature']:.2f}")
                    print(f"  Humidity: {hex_info['humidity']:.2f}")
                    print(f"  Continentalness: {hex_info['continentalness']:.2f}")
                    print(f"  Erosion: {hex_info['erosion']:.2f}")
    
    def handle_button_click(self, button_name):
        """Handle button clicks"""
        if button_name == 'generate':
            self.generate_map()
        elif button_name == 'clear':
            self.hex_data.clear()
            self.biome_counts.clear()
        elif button_name == 'size_small':
            self.width = self.height = 15
        elif button_name == 'size_medium':
            self.width = self.height = 30
        elif button_name == 'size_large':
            self.width = self.height = 50
        elif button_name == 'size_xlarge':
            self.width = self.height = 100
        elif button_name == 'random_seed':
            self.seed = random.randint(1, 1000000)
            if self.biome_generator:
                self.biome_generator = MinecraftBiomeGenerator(self.seed)
        elif button_name == 'set_seed':
            try:
                print(f"Current seed: {self.seed}")
                new_seed = input("Enter new seed (number): ").strip()
                if new_seed:
                    self.seed = int(new_seed)
                    if self.biome_generator:
                        self.biome_generator = MinecraftBiomeGenerator(self.seed)
                    print(f"Seed set to: {self.seed}")
            except:
                print("Invalid seed")
        elif button_name == 'reset_view':
            self.reset_view()
        elif button_name == 'toggle_coords':
            self.show_coordinates = not self.show_coordinates
        elif button_name == 'toggle_params':
            self.show_biome_params = not self.show_biome_params
        elif button_name == 'save_json':
            self.save_json()
        elif button_name == 'copy_game':
            self.copy_to_game()
    
    def update_keyboard_navigation(self):
        """Handle keyboard input"""
        move_speed = 300 / self.zoom
        
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
    
    def draw_hex(self, surface, x, y, size, color, border_color=None):
        """Draw a hexagon"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.append((px, py))
        
        pygame.draw.polygon(surface, color, points)
        if border_color:
            pygame.draw.polygon(surface, border_color, points, 1)
    
    def get_hex_screen_pos(self, col, row):
        """Get screen position for hex"""
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        x = col * hex_width * self.zoom + self.camera_x + self.map_area.x
        y = (row * hex_height + (col % 2) * hex_height * 0.5) * self.zoom + self.camera_y + self.map_area.y
        
        return x, y
    
    def get_hex_at_screen_pos(self, screen_x, screen_y):
        """Get hex at screen position"""
        if not self.hex_data:
            return None
        
        # Convert to world coordinates
        world_x = (screen_x - self.camera_x) / self.zoom
        world_y = (screen_y - self.camera_y) / self.zoom
        
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        # Rough estimate
        rough_col = int(world_x / hex_width)
        rough_row = int((world_y - (rough_col % 2) * hex_height * 0.5) / hex_height)
        
        # Check nearby hexes
        for check_col in range(max(0, rough_col - 1), min(self.width, rough_col + 2)):
            for check_row in range(max(0, rough_row - 1), min(self.height, rough_row + 2)):
                if (check_col, check_row) in self.hex_data:
                    hex_x, hex_y = self.get_hex_screen_pos(check_col, check_row)
                    dist = math.sqrt((screen_x + self.map_area.x - hex_x)**2 + 
                                   (screen_y + self.map_area.y - hex_y)**2)
                    if dist < self.hex_size * self.zoom:
                        return (check_col, check_row)
        
        return None
    
    def update_tooltip(self, pos):
        """Update tooltip"""
        if self.map_area.collidepoint(pos):
            hex_coords = self.get_hex_at_screen_pos(pos[0] - self.map_area.x, pos[1] - self.map_area.y)
            self.tooltip_hex = hex_coords
            self.tooltip_pos = pos
        else:
            self.tooltip_hex = None
    
    def draw_map(self):
        """Draw the hex map"""
        if not self.hex_data:
            return
        
        # Clear map area
        pygame.draw.rect(self.screen, self.COLORS['background'], self.map_area)
        
        # Draw hexes
        for (col, row), hex_data in self.hex_data.items():
            x, y = self.get_hex_screen_pos(col, row)
            
            # Only draw if visible
            if (x + self.hex_size * self.zoom >= self.map_area.x and 
                x - self.hex_size * self.zoom <= self.map_area.x + self.map_area.width and
                y + self.hex_size * self.zoom >= self.map_area.y and 
                y - self.hex_size * self.zoom <= self.map_area.y + self.map_area.height):
                
                terrain = hex_data['terrain']
                color = self.COLORS.get(terrain, (128, 128, 128))
                size = self.hex_size * self.zoom
                
                # Draw hex with border
                border_color = (0, 0, 0) if self.zoom > 0.5 else None
                self.draw_hex(self.screen, x, y, size, color, border_color)
                
                # Draw coordinates if enabled and zoomed in enough
                if self.show_coordinates and self.zoom > 1.5:
                    coord_text = f"{col},{row}"
                    text_surface = self.font_tiny.render(coord_text, True, (0, 0, 0))
                    text_rect = text_surface.get_rect(center=(x, y))
                    self.screen.blit(text_surface, text_rect)
    
    def draw_ui(self):
        """Draw UI panel"""
        # Background
        ui_rect = pygame.Rect(0, 0, self.ui_panel_width, self.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, self.COLORS['ui_bg'], ui_rect)
        pygame.draw.line(self.screen, self.COLORS['ui_border'], 
                        (self.ui_panel_width, 0), (self.ui_panel_width, self.SCREEN_HEIGHT), 2)
        
        # Title
        title = self.font_large.render("Minecraft Hex Generator", True, self.COLORS['text'])
        self.screen.blit(title, (10, 10))
        
        # Biome system status
        status_color = (100, 255, 100) if BIOME_SYSTEM_AVAILABLE else (255, 100, 100)
        status_text = "6D Biome System: " + ("ACTIVE" if BIOME_SYSTEM_AVAILABLE else "FALLBACK")
        status_surface = self.font_small.render(status_text, True, status_color)
        self.screen.blit(status_surface, (10, 45))
        
        # Settings
        y_pos = 80
        settings = [
            f"Size: {self.width} x {self.height}",
            f"Seed: {self.seed}",
            f"Zoom: {self.zoom:.2f}x",
            f"Hexes: {len(self.hex_data)}"
        ]
        
        for text in settings:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, y_pos))
            y_pos += 20
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        
        button_labels = {
            'generate': 'Generate Map',
            'clear': 'Clear Map',
            'size_small': '15',
            'size_medium': '30',
            'size_large': '50',
            'size_xlarge': '100',
            'random_seed': 'Random Seed',
            'set_seed': 'Set Seed',
            'reset_view': 'Reset View',
            'toggle_coords': f"Coords: {'ON' if self.show_coordinates else 'OFF'}",
            'toggle_params': f"Debug: {'ON' if self.show_biome_params else 'OFF'}",
            'save_json': 'Save JSON',
            'copy_game': 'Copy to Game'
        }
        
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(mouse_pos):
                color = self.COLORS['button_hover']
            else:
                color = self.COLORS['button']
            
            pygame.draw.rect(self.screen, color, button_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
            
            label = button_labels.get(button_name, button_name)
            text_surface = self.font_small.render(label, True, self.COLORS['text'])
            text_rect = text_surface.get_rect(center=button_rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Size label
        size_label = self.font_small.render("Map Size:", True, self.COLORS['text'])
        self.screen.blit(size_label, (10, 170))
        
        # Biome distribution
        if self.biome_counts:
            y_pos = 420
            dist_title = self.font_medium.render("Biome Distribution:", True, self.COLORS['text'])
            self.screen.blit(dist_title, (10, y_pos))
            y_pos += 25
            
            total = len(self.hex_data)
            for terrain, count in sorted(self.biome_counts.items(), key=lambda x: x[1], reverse=True):
                if y_pos > self.SCREEN_HEIGHT - 100:
                    break
                
                percent = (count / total) * 100 if total > 0 else 0
                
                # Color square
                color = self.COLORS.get(terrain, (128, 128, 128))
                pygame.draw.rect(self.screen, color, (10, y_pos, 15, 15))
                pygame.draw.rect(self.screen, self.COLORS['ui_border'], (10, y_pos, 15, 15), 1)
                
                # Text
                text = f"{terrain.title()}: {count} ({percent:.1f}%)"
                surface = self.font_small.render(text, True, self.COLORS['text'])
                self.screen.blit(surface, (30, y_pos))
                y_pos += 18
        
        # Controls help
        help_y = self.SCREEN_HEIGHT - 90
        help_text = [
            "Right/Middle Drag: Pan",
            "Mouse Wheel: Zoom",
            "WASD/Arrows: Navigate",
            "R: Reset View"
        ]
        
        for text in help_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, help_y))
            help_y += 18
    
    def draw_tooltip(self):
        """Draw tooltip"""
        if self.tooltip_hex and self.tooltip_hex in self.hex_data:
            hex_data = self.hex_data[self.tooltip_hex]
            
            tooltip_lines = [
                f"Position: ({self.tooltip_hex[0]}, {self.tooltip_hex[1]})",
                f"Terrain: {hex_data['terrain'].title()}"
            ]
            
            if self.show_biome_params:
                tooltip_lines.extend([
                    f"Temp: {hex_data['temperature']:.2f}",
                    f"Humid: {hex_data['humidity']:.2f}",
                    f"Cont: {hex_data['continentalness']:.2f}"
                ])
            
            # Draw tooltip
            y = self.tooltip_pos[1] - 20 * len(tooltip_lines) - 10
            max_width = 0
            
            for line in tooltip_lines:
                text_surface = self.font_small.render(line, True, self.COLORS['text'])
                max_width = max(max_width, text_surface.get_width())
            
            # Background
            bg_rect = pygame.Rect(self.tooltip_pos[0] + 10, y, max_width + 10, 20 * len(tooltip_lines) + 5)
            pygame.draw.rect(self.screen, self.COLORS['ui_bg'], bg_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], bg_rect, 1)
            
            # Text
            for line in tooltip_lines:
                text_surface = self.font_small.render(line, True, self.COLORS['text'])
                self.screen.blit(text_surface, (self.tooltip_pos[0] + 15, y + 2))
                y += 20
    
    def reset_view(self):
        """Reset camera view"""
        if self.hex_data:
            # Center on map
            self.camera_x = self.map_area.width // 2 - (self.width * self.hex_size * 1.5) // 2
            self.camera_y = self.map_area.height // 2 - (self.height * self.hex_size * math.sqrt(3)) // 2
            self.zoom = min(
                self.map_area.width / (self.width * self.hex_size * 1.5),
                self.map_area.height / (self.height * self.hex_size * math.sqrt(3))
            ) * 0.9
    
    def save_json(self):
        """Save map to JSON"""
        if not self.hex_data:
            print("No map to save!")
            return
        
        filename = f"maps/minecraft_style_{self.seed}.json"
        self.export_map_data(filename)
        print(f"Saved: {filename}")
    
    def copy_to_game(self):
        """Copy to game folder"""
        if not self.hex_data:
            return
        
        os.makedirs("maps", exist_ok=True)
        filename = f"maps/minecraft_style_{self.seed}.json"
        self.export_map_data(filename)
        print(f"Copied to game: {filename}")
    
    def export_map_data(self, filename):
        """Export map data"""
        export_data = {
            "seed": self.seed,
            "dimensions": {"width": self.width, "height": self.height},
            "generation": "minecraft_6d" if BIOME_SYSTEM_AVAILABLE else "simple",
            "hexes": {}
        }
        
        for (col, row), hex_data in self.hex_data.items():
            key = f"{hex_data['q']},{hex_data['r']},{hex_data['s']}"
            export_data["hexes"][key] = {
                "q": hex_data['q'],
                "r": hex_data['r'],
                "s": hex_data['s'],
                "terrain": hex_data['terrain'],
                "description": f"A {hex_data['terrain']} hex",
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
            self.clock.tick(60)
        
        pygame.quit()

def main():
    """Main function"""
    print("=" * 60)
    print("MINECRAFT-STYLE HEX MAP GENERATOR")
    print("=" * 60)
    print("Using authentic Minecraft 6D biome generation system!")
    print("Temperature, Humidity, Continentalness, Erosion, Weirdness, Depth")
    print("=" * 60)
    
    try:
        app = MinecraftHexGenerator()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()