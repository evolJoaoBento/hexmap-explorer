"""
Stable Hex Map Generator with Chunk Expansion
Simplified version that works reliably
"""
import pygame
import math
import random
import json
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class StableHexGenerator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Screen settings
        self.SCREEN_WIDTH = 1200
        self.SCREEN_HEIGHT = 800
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Stable Hex Map Generator")
        
        # Colors
        self.COLORS = {
            'background': (20, 25, 30),
            'ui_bg': (40, 45, 50),
            'ui_border': (100, 110, 120),
            'text': (255, 255, 255),
            'button': (60, 70, 80),
            'button_hover': (80, 90, 100),
            'expand_button': (40, 100, 60),
            'expand_button_hover': (50, 130, 80),
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
        
        # Map settings - start with empty map
        self.seed = random.randint(1, 1000000)
        self.hex_data = {}
        self.biome_counts = {}
        
        # Chunk settings
        self.chunk_size = 10  # Small chunks for stability
        self.generated_chunks = set()  # Track which chunks are generated
        
        # View settings
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.hex_size = 20
        
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
        self.expand_buttons = {}
        self.create_ui_elements()
        
        # Try to import biome generator
        try:
            from generation.minecraft_biomes import MinecraftBiomeGenerator
            self.MinecraftBiomeGenerator = MinecraftBiomeGenerator
            print("Minecraft biome generator loaded successfully")
        except:
            self.MinecraftBiomeGenerator = None
            print("Using simple terrain generator")
        
        # Clock for smooth animation
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Tooltip
        self.tooltip_hex = None
        self.tooltip_pos = (0, 0)
    
    def create_ui_elements(self):
        """Create UI buttons and input areas"""
        button_width = 120
        button_height = 30
        margin = 10
        y_pos = 60
        
        # Generate center button
        self.buttons['generate_center'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        # Clear world button
        self.buttons['clear_world'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin * 2
        
        # Expansion controls - simple directional buttons
        y_pos += 20
        
        # Create directional buttons in a cross pattern
        center_x = self.ui_panel_width // 2 - 20
        center_y = y_pos + 40
        button_size = 40
        
        # North
        self.expand_buttons['N'] = pygame.Rect(center_x, center_y - 45, button_size, button_size)
        # South  
        self.expand_buttons['S'] = pygame.Rect(center_x, center_y + 45, button_size, button_size)
        # East
        self.expand_buttons['E'] = pygame.Rect(center_x + 45, center_y, button_size, button_size)
        # West
        self.expand_buttons['W'] = pygame.Rect(center_x - 45, center_y, button_size, button_size)
        
        y_pos = center_y + 80
        
        # Settings
        self.buttons['set_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
        y_pos += button_height + margin
        
        self.buttons['random_seed'] = pygame.Rect(margin, y_pos, button_width, button_height)
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
    
    def generate_chunk(self, chunk_x, chunk_y):
        """Generate a chunk of hexes at given chunk coordinates"""
        chunk_key = (chunk_x, chunk_y)
        if chunk_key in self.generated_chunks:
            return
        
        print(f"Generating chunk at ({chunk_x}, {chunk_y})...")
        
        # Use seed based on chunk position
        random.seed(self.seed + chunk_x * 1000 + chunk_y * 100)
        
        terrains = ['water', 'forest', 'plains', 'mountains', 'desert', 'hills', 'swamp', 'tundra']
        terrain_weights = [20, 25, 20, 10, 10, 10, 3, 2]  # Weighted random
        
        generated_count = 0
        
        # Generate hexes in a square chunk (simpler than hexagonal chunks)
        for dx in range(self.chunk_size):
            for dy in range(self.chunk_size):
                # Calculate actual hex position
                hex_x = chunk_x * self.chunk_size + dx
                hex_y = chunk_y * self.chunk_size + dy
                
                # Convert to cube coordinates
                q = hex_x - (hex_y - (hex_y & 1)) // 2
                r = hex_y
                s = -q - r
                
                # Generate terrain
                if self.MinecraftBiomeGenerator:
                    try:
                        generator = self.MinecraftBiomeGenerator(self.seed)
                        terrain = generator.select_biome(q, r, s)
                    except:
                        terrain = random.choices(terrains, weights=terrain_weights)[0]
                else:
                    terrain = random.choices(terrains, weights=terrain_weights)[0]
                
                # Store hex data
                self.hex_data[(hex_x, hex_y)] = {
                    'q': q, 'r': r, 's': s,
                    'terrain': terrain,
                    'x': hex_x, 'y': hex_y,
                    'chunk': chunk_key
                }
                
                self.biome_counts[terrain] = self.biome_counts.get(terrain, 0) + 1
                generated_count += 1
        
        self.generated_chunks.add(chunk_key)
        print(f"Generated {generated_count} hexes in chunk ({chunk_x}, {chunk_y})")
        print(f"Total hexes: {len(self.hex_data)}")
    
    def expand_world(self, direction):
        """Expand world in given direction"""
        new_chunks = []
        
        if not self.generated_chunks:
            # Generate center if nothing exists
            self.generate_chunk(0, 0)
            return
        
        # Find edge chunks in the given direction
        for chunk_x, chunk_y in self.generated_chunks:
            if direction == 'N':
                new_chunk = (chunk_x, chunk_y - 1)
            elif direction == 'S':
                new_chunk = (chunk_x, chunk_y + 1)
            elif direction == 'E':
                new_chunk = (chunk_x + 1, chunk_y)
            elif direction == 'W':
                new_chunk = (chunk_x - 1, chunk_y)
            else:
                continue
            
            if new_chunk not in self.generated_chunks:
                new_chunks.append(new_chunk)
        
        # Generate new chunks
        for chunk_x, chunk_y in new_chunks:
            self.generate_chunk(chunk_x, chunk_y)
        
        print(f"Expanded world {direction}: added {len(new_chunks)} new chunks")
    
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
        # Check expansion buttons
        for button_name, button_rect in self.expand_buttons.items():
            if button_rect.collidepoint(pos):
                self.expand_world(button_name)
                return
        
        # Check UI buttons
        for button_name, button_rect in self.buttons.items():
            if button_rect.collidepoint(pos):
                self.handle_button_click(button_name)
                return
    
    def handle_button_click(self, button_name):
        """Handle button clicks"""
        if button_name == 'generate_center':
            self.generate_chunk(0, 0)
            self.reset_view()
        elif button_name == 'clear_world':
            self.hex_data.clear()
            self.biome_counts.clear()
            self.generated_chunks.clear()
        elif button_name == 'set_seed':
            try:
                print(f"Current seed: {self.seed}")
                seed_input = input("Enter new seed: ").strip()
                if seed_input:
                    self.seed = int(seed_input)
                    print(f"Seed set to: {self.seed}")
            except:
                pass
        elif button_name == 'random_seed':
            self.seed = random.randint(1, 1000000)
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
        
        if pygame.K_EQUALS in self.keys_pressed or pygame.K_PLUS in self.keys_pressed:
            self.zoom = min(self.max_zoom, self.zoom * 1.02)
        if pygame.K_MINUS in self.keys_pressed:
            self.zoom = max(self.min_zoom, self.zoom * 0.98)
    
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
    
    def get_hex_screen_pos(self, hex_x, hex_y):
        """Get screen position for hex at grid coordinates"""
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        x = hex_x * hex_width * self.zoom + self.camera_x + self.map_area.x
        y = (hex_y * hex_height + (hex_x % 2) * hex_height * 0.5) * self.zoom + self.camera_y + self.map_area.y
        
        return x, y
    
    def get_hex_at_screen_pos(self, screen_x, screen_y):
        """Get hex coordinates from screen position"""
        if not self.hex_data:
            return None
        
        # Convert screen to world coordinates
        world_x = (screen_x - self.camera_x) / self.zoom
        world_y = (screen_y - self.camera_y) / self.zoom
        
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        # Rough estimate
        rough_x = int(world_x / hex_width)
        rough_y = int(world_y / hex_height)
        
        # Check nearby hexes
        for check_x in range(rough_x - 2, rough_x + 3):
            for check_y in range(rough_y - 2, rough_y + 3):
                if (check_x, check_y) in self.hex_data:
                    hex_screen_x, hex_screen_y = self.get_hex_screen_pos(check_x, check_y)
                    dist = math.sqrt((screen_x + self.map_area.x - hex_screen_x)**2 + 
                                   (screen_y + self.map_area.y - hex_screen_y)**2)
                    if dist < self.hex_size * self.zoom:
                        return (check_x, check_y)
        
        return None
    
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
    
    def draw_map(self):
        """Draw the hex map"""
        if not self.hex_data:
            return
        
        # Clear map area
        pygame.draw.rect(self.screen, self.COLORS['background'], self.map_area)
        
        # Draw hexes
        visible_count = 0
        max_visible = 5000  # Limit for performance
        
        for (hex_x, hex_y), hex_data in self.hex_data.items():
            if visible_count > max_visible:
                break
                
            x, y = self.get_hex_screen_pos(hex_x, hex_y)
            
            # Only draw if visible
            if (x + self.hex_size * self.zoom >= self.map_area.x and 
                x - self.hex_size * self.zoom <= self.map_area.x + self.map_area.width and
                y + self.hex_size * self.zoom >= self.map_area.y and 
                y - self.hex_size * self.zoom <= self.map_area.y + self.map_area.height):
                
                terrain = hex_data['terrain']
                color = self.COLORS.get(terrain, (128, 128, 128))
                size = self.hex_size * self.zoom
                
                # Draw hex
                border_color = (0, 0, 0) if self.zoom > 0.5 else None
                self.draw_hex(self.screen, x, y, size, color, border_color)
                visible_count += 1
    
    def draw_ui(self):
        """Draw the UI panel"""
        # Draw UI background
        ui_rect = pygame.Rect(0, 0, self.ui_panel_width, self.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, self.COLORS['ui_bg'], ui_rect)
        pygame.draw.line(self.screen, self.COLORS['ui_border'], 
                        (self.ui_panel_width, 0), (self.ui_panel_width, self.SCREEN_HEIGHT), 2)
        
        # Draw title
        title = self.font_large.render("Stable Hex Generator", True, self.COLORS['text'])
        self.screen.blit(title, (10, 10))
        
        # Draw stats
        y_pos = 50
        stats = [
            f"Seed: {self.seed}",
            f"Zoom: {self.zoom:.2f}x",
            f"Chunks: {len(self.generated_chunks)}",
            f"Total Hexes: {len(self.hex_data)}",
            f"Chunk Size: {self.chunk_size}x{self.chunk_size}"
        ]
        
        for text in stats:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, y_pos))
            y_pos += 20
        
        # Draw expand label
        expand_label = self.font_medium.render("Expand:", True, self.COLORS['text'])
        self.screen.blit(expand_label, (10, 180))
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        
        # Expansion buttons
        for button_name, button_rect in self.expand_buttons.items():
            if button_rect.collidepoint(mouse_pos):
                color = self.COLORS['expand_button_hover']
            else:
                color = self.COLORS['expand_button']
            
            pygame.draw.rect(self.screen, color, button_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
            
            text_surface = self.font_medium.render(button_name, True, self.COLORS['text'])
            text_rect = text_surface.get_rect(center=button_rect.center)
            self.screen.blit(text_surface, text_rect)
        
        # Regular buttons
        button_labels = {
            'generate_center': 'Generate Center',
            'clear_world': 'Clear World',
            'set_seed': 'Set Seed',
            'random_seed': 'Random Seed',
            'reset_view': 'Reset View',
            'fit_map': 'Fit Map',
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
        
        # Draw terrain distribution
        if self.biome_counts:
            dist_y = 500
            dist_title = self.font_medium.render("Terrain:", True, self.COLORS['text'])
            self.screen.blit(dist_title, (10, dist_y))
            dist_y += 25
            
            total = len(self.hex_data)
            for terrain, count in sorted(self.biome_counts.items())[:5]:  # Show top 5
                percent = (count / total) * 100 if total > 0 else 0
                
                color = self.COLORS.get(terrain, (128, 128, 128))
                pygame.draw.rect(self.screen, color, (10, dist_y, 12, 12))
                
                text = f"{terrain}: {percent:.1f}%"
                surface = self.font_small.render(text, True, self.COLORS['text'])
                self.screen.blit(surface, (25, dist_y))
                dist_y += 18
        
        # Draw controls
        help_y = self.SCREEN_HEIGHT - 100
        help_text = [
            "Mouse wheel: Zoom",
            "Right drag: Pan",
            "WASD: Navigate",
            "R: Reset view"
        ]
        
        for text in help_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, help_y))
            help_y += 18
    
    def draw_tooltip(self):
        """Draw tooltip for hex under mouse"""
        if self.tooltip_hex and self.tooltip_hex in self.hex_data:
            hex_data = self.hex_data[self.tooltip_hex]
            
            tooltip_text = [
                f"Position: ({hex_data['x']}, {hex_data['y']})",
                f"Terrain: {hex_data['terrain'].title()}"
            ]
            
            # Draw tooltip near mouse
            y = self.tooltip_pos[1] - 40
            for text in tooltip_text:
                surface = self.font_small.render(text, True, self.COLORS['text'])
                bg_rect = surface.get_rect(topleft=(self.tooltip_pos[0] + 10, y))
                bg_rect.inflate_ip(10, 4)
                pygame.draw.rect(self.screen, self.COLORS['ui_bg'], bg_rect)
                pygame.draw.rect(self.screen, self.COLORS['ui_border'], bg_rect, 1)
                self.screen.blit(surface, (self.tooltip_pos[0] + 15, y + 2))
                y += 20
    
    def reset_view(self):
        """Reset camera to center on map"""
        if self.hex_data:
            # Find center of generated world
            min_x = min(x for x, y in self.hex_data.keys())
            max_x = max(x for x, y in self.hex_data.keys())
            min_y = min(y for x, y in self.hex_data.keys())
            max_y = max(y for x, y in self.hex_data.keys())
            
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            
            # Center camera on world center
            hex_width = self.hex_size * 1.5
            hex_height = self.hex_size * math.sqrt(3)
            
            self.camera_x = self.map_area.width / 2 - center_x * hex_width
            self.camera_y = self.map_area.height / 2 - center_y * hex_height
            self.zoom = 1.0
    
    def fit_map_to_view(self):
        """Fit map to view"""
        if not self.hex_data:
            return
        
        min_x = min(x for x, y in self.hex_data.keys())
        max_x = max(x for x, y in self.hex_data.keys())
        min_y = min(y for x, y in self.hex_data.keys())
        max_y = max(y for x, y in self.hex_data.keys())
        
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        zoom_x = self.map_area.width / (width * hex_width)
        zoom_y = self.map_area.height / (height * hex_height)
        
        self.zoom = min(self.max_zoom, max(self.min_zoom, min(zoom_x, zoom_y) * 0.8))
        self.reset_view()
    
    def save_json(self):
        """Save map as JSON"""
        if not self.hex_data:
            return
        
        filename = f"maps/generated_stable_{self.seed}.json"
        self.export_map_data(filename)
        print(f"Saved: {filename}")
    
    def copy_to_game(self):
        """Copy to game maps folder"""
        if not self.hex_data:
            return
        
        os.makedirs("maps", exist_ok=True)
        filename = f"maps/generated_stable_{self.seed}.json"
        self.export_map_data(filename)
        print(f"Copied to: {filename}")
    
    def export_map_data(self, filename):
        """Export map data to JSON file"""
        export_data = {
            "seed": self.seed,
            "dimensions": {"chunks": len(self.generated_chunks), "hexes": len(self.hex_data)},
            "hexes": {}
        }
        
        for (hex_x, hex_y), hex_data in self.hex_data.items():
            key = f"{hex_data['q']},{hex_data['r']},{hex_data['s']}"
            export_data["hexes"][key] = {
                "q": hex_data['q'],
                "r": hex_data['r'],
                "s": hex_data['s'],
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
    print("Starting Stable Hex Map Generator...")
    print("Click 'Generate Center' to start, then use directional buttons to expand!")
    
    try:
        app = StableHexGenerator()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()