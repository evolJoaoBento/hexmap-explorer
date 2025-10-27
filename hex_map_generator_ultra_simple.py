"""
Ultra Simple Hex Map Generator
No external dependencies, pure Python/Pygame
"""
import pygame
import math
import random
import json
import os

class UltraSimpleHexGenerator:
    def __init__(self):
        # Initialize pygame
        pygame.init()
        
        # Screen settings
        self.SCREEN_WIDTH = 1200
        self.SCREEN_HEIGHT = 800
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        pygame.display.set_caption("Ultra Simple Hex Map Generator")
        
        # Colors
        self.COLORS = {
            'background': (20, 25, 30),
            'ui_bg': (40, 45, 50),
            'ui_border': (100, 110, 120),
            'text': (255, 255, 255),
            'button': (60, 70, 80),
            'button_hover': (80, 90, 100),
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
        try:
            self.font_small = pygame.font.Font(None, 20)
            self.font_medium = pygame.font.Font(None, 24)
            self.font_large = pygame.font.Font(None, 32)
        except:
            pygame.font.init()
            self.font_small = pygame.font.Font(None, 20)
            self.font_medium = pygame.font.Font(None, 24)
            self.font_large = pygame.font.Font(None, 32)
        
        # Map settings
        self.map_width = 20
        self.map_height = 20
        self.seed = random.randint(1, 1000000)
        self.hex_data = {}
        self.biome_counts = {}
        
        # Available terrains
        self.terrains = ['water', 'forest', 'plains', 'mountains', 'desert', 'hills', 'swamp', 'tundra']
        
        # View settings
        self.camera_x = 400
        self.camera_y = 400
        self.zoom = 1.0
        self.hex_size = 20
        
        # Navigation
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        
        # UI elements
        self.ui_panel_width = 250
        self.buttons = {}
        self.create_buttons()
        
        # Clock
        self.clock = pygame.time.Clock()
        self.running = True
    
    def create_buttons(self):
        """Create UI buttons"""
        button_width = 100
        button_height = 30
        x = 10
        y = 100
        
        self.buttons['generate'] = pygame.Rect(x, y, button_width, button_height)
        y += 40
        self.buttons['clear'] = pygame.Rect(x, y, button_width, button_height)
        y += 40
        self.buttons['small'] = pygame.Rect(x, y, button_width, button_height)
        y += 40
        self.buttons['medium'] = pygame.Rect(x, y, button_width, button_height)
        y += 40
        self.buttons['large'] = pygame.Rect(x, y, button_width, button_height)
        y += 40
        self.buttons['save'] = pygame.Rect(x, y, button_width, button_height)
    
    def generate_map(self):
        """Generate a simple random map"""
        print(f"Generating {self.map_width}x{self.map_height} map...")
        
        # Clear existing data
        self.hex_data.clear()
        self.biome_counts.clear()
        
        # Set random seed
        random.seed(self.seed)
        
        # Generate each hex
        for x in range(self.map_width):
            for y in range(self.map_height):
                # Simple random terrain selection
                terrain = random.choice(self.terrains)
                
                # Store hex data (simplified)
                self.hex_data[(x, y)] = {
                    'terrain': terrain,
                    'x': x,
                    'y': y
                }
                
                # Count terrains
                if terrain not in self.biome_counts:
                    self.biome_counts[terrain] = 0
                self.biome_counts[terrain] += 1
        
        print(f"Generated {len(self.hex_data)} hexes")
        
        # Reset view
        self.camera_x = 400
        self.camera_y = 400
        self.zoom = 1.0
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    # Check button clicks
                    mouse_pos = event.pos
                    for button_name, button_rect in self.buttons.items():
                        if button_rect.collidepoint(mouse_pos):
                            self.handle_button(button_name)
                
                elif event.button == 3:  # Right click - start drag
                    self.dragging = True
                    self.last_mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    self.dragging = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx
                    self.camera_y += dy
                    self.last_mouse_pos = event.pos
            
            elif event.type == pygame.MOUSEWHEEL:
                # Simple zoom
                if event.y > 0:
                    self.zoom = min(3.0, self.zoom * 1.1)
                else:
                    self.zoom = max(0.3, self.zoom * 0.9)
            
            elif event.type == pygame.KEYDOWN:
                # Arrow key navigation
                if event.key == pygame.K_LEFT:
                    self.camera_x += 20
                elif event.key == pygame.K_RIGHT:
                    self.camera_x -= 20
                elif event.key == pygame.K_UP:
                    self.camera_y += 20
                elif event.key == pygame.K_DOWN:
                    self.camera_y -= 20
                elif event.key == pygame.K_r:
                    # Reset view
                    self.camera_x = 400
                    self.camera_y = 400
                    self.zoom = 1.0
    
    def handle_button(self, button_name):
        """Handle button clicks"""
        if button_name == 'generate':
            self.generate_map()
        elif button_name == 'clear':
            self.hex_data.clear()
            self.biome_counts.clear()
        elif button_name == 'small':
            self.map_width = 10
            self.map_height = 10
        elif button_name == 'medium':
            self.map_width = 25
            self.map_height = 25
        elif button_name == 'large':
            self.map_width = 50
            self.map_height = 50
        elif button_name == 'save':
            self.save_map()
    
    def draw_hex(self, x, y, size, color):
        """Draw a simple hexagon"""
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = x + size * math.cos(angle)
            py = y + size * math.sin(angle)
            points.append((px, py))
        
        pygame.draw.polygon(self.screen, color, points)
        pygame.draw.polygon(self.screen, (0, 0, 0), points, 1)  # Black border
    
    def draw_map(self):
        """Draw the hex map"""
        if not self.hex_data:
            return
        
        # Draw each hex
        hex_width = self.hex_size * 1.5
        hex_height = self.hex_size * math.sqrt(3)
        
        for (hx, hy), hex_info in self.hex_data.items():
            # Calculate screen position
            x = hx * hex_width * self.zoom + self.camera_x
            y = hy * hex_height * self.zoom + self.camera_y
            
            # Offset odd columns
            if hx % 2 == 1:
                y += hex_height * self.zoom * 0.5
            
            # Only draw if on screen
            if -50 < x < self.SCREEN_WIDTH and -50 < y < self.SCREEN_HEIGHT:
                terrain = hex_info['terrain']
                color = self.COLORS.get(terrain, (128, 128, 128))
                self.draw_hex(x, y, self.hex_size * self.zoom, color)
    
    def draw_ui(self):
        """Draw the UI panel"""
        # Draw background
        pygame.draw.rect(self.screen, self.COLORS['ui_bg'], 
                        (0, 0, self.ui_panel_width, self.SCREEN_HEIGHT))
        pygame.draw.line(self.screen, self.COLORS['ui_border'],
                        (self.ui_panel_width, 0), 
                        (self.ui_panel_width, self.SCREEN_HEIGHT), 2)
        
        # Draw title
        title = self.font_large.render("Hex Generator", True, self.COLORS['text'])
        self.screen.blit(title, (10, 10))
        
        # Draw info
        y = 50
        info_text = [
            f"Size: {self.map_width}x{self.map_height}",
            f"Hexes: {len(self.hex_data)}",
            f"Zoom: {self.zoom:.1f}x"
        ]
        
        for text in info_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, y))
            y += 20
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        
        button_labels = {
            'generate': 'Generate',
            'clear': 'Clear',
            'small': 'Small (10x10)',
            'medium': 'Medium (25x25)',
            'large': 'Large (50x50)',
            'save': 'Save Map'
        }
        
        for button_name, button_rect in self.buttons.items():
            # Check hover
            if button_rect.collidepoint(mouse_pos):
                color = self.COLORS['button_hover']
            else:
                color = self.COLORS['button']
            
            pygame.draw.rect(self.screen, color, button_rect)
            pygame.draw.rect(self.screen, self.COLORS['ui_border'], button_rect, 1)
            
            # Draw label
            label = button_labels.get(button_name, button_name)
            text = self.font_small.render(label, True, self.COLORS['text'])
            text_rect = text.get_rect(center=button_rect.center)
            self.screen.blit(text, text_rect)
        
        # Draw terrain counts
        if self.biome_counts:
            y = 350
            title = self.font_medium.render("Terrains:", True, self.COLORS['text'])
            self.screen.blit(title, (10, y))
            y += 25
            
            for terrain, count in sorted(self.biome_counts.items()):
                # Draw color box
                color = self.COLORS.get(terrain, (128, 128, 128))
                pygame.draw.rect(self.screen, color, (10, y, 12, 12))
                
                # Draw text
                text = f"{terrain}: {count}"
                surface = self.font_small.render(text, True, self.COLORS['text'])
                self.screen.blit(surface, (25, y))
                y += 15
        
        # Draw help
        y = self.SCREEN_HEIGHT - 80
        help_text = [
            "Right drag: Pan",
            "Mouse wheel: Zoom",
            "Arrows: Move",
            "R: Reset view"
        ]
        
        for text in help_text:
            surface = self.font_small.render(text, True, self.COLORS['text'])
            self.screen.blit(surface, (10, y))
            y += 18
    
    def save_map(self):
        """Save the map to JSON"""
        if not self.hex_data:
            print("No map to save!")
            return
        
        # Create maps directory
        os.makedirs("maps", exist_ok=True)
        
        # Create filename
        filename = f"maps/ultra_simple_{self.seed}.json"
        
        # Create export data
        export_data = {
            "seed": self.seed,
            "dimensions": {"width": self.map_width, "height": self.map_height},
            "hexes": {}
        }
        
        # Convert hex data
        for (x, y), hex_info in self.hex_data.items():
            # Simple cube coordinate conversion
            q = x - (y - (y & 1)) // 2
            r = y
            s = -q - r
            
            key = f"{q},{r},{s}"
            export_data["hexes"][key] = {
                "q": q,
                "r": r,
                "s": s,
                "terrain": hex_info['terrain'],
                "description": f"A {hex_info['terrain']} hex",
                "explored": False,
                "visible": False
            }
        
        # Write file
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            print(f"Map saved to {filename}")
        except Exception as e:
            print(f"Failed to save: {e}")
    
    def run(self):
        """Main loop"""
        while self.running:
            self.handle_events()
            
            # Clear screen
            self.screen.fill(self.COLORS['background'])
            
            # Draw map first (behind UI)
            self.draw_map()
            
            # Draw UI on top
            self.draw_ui()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()

def main():
    """Main function"""
    print("Starting Ultra Simple Hex Map Generator...")
    print("This version has no external dependencies!")
    
    try:
        app = UltraSimpleHexGenerator()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()