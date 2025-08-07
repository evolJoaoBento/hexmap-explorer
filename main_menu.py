import pygame
import sys
import json
import os
import random
import math
import textwrap
from PIL import Image
import numpy as np
from stable_map_generator import StableMapGenerator

class MainMenu:
    """Main menu for Hex Map Explorer - Adapted for modular structure"""
    
    def __init__(self):
        pygame.init()
        

        #self.set_window_icon()
        # Set window icon
        if os.path.exists("hex_explorer.ico"):
            try:
                icon = pygame.image.load("hex_explorer.ico")
                pygame.display.set_icon(icon)
            except:
                pass
        # Get display info for responsive sizing
        info = pygame.display.Info()
        self.display_width = info.current_w
        self.display_height = info.current_h
        
        # Set window size (80% of screen or minimum size)
        self.width = max(800, min(int(self.display_width * 0.8), 1920))
        self.height = max(600, min(int(self.display_height * 0.8), 1080))
        
        # Create resizable window
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Hex Map Explorer - Main Menu")
        self.clock = pygame.time.Clock()
        
        # Calculate font sizes based on window size
        self.update_font_sizes()
        
        # Colors
        self.bg_color = (20, 25, 40)
        self.title_color = (255, 215, 0)  # Gold
        self.button_color = (70, 80, 100)
        self.button_hover = (90, 100, 120)
        self.button_text = (255, 255, 255)
        self.desc_color = (180, 180, 180)
        
        # Menu buttons
        self.buttons = [
            {
                "text": "New Adventure",
                "desc": "Start a new procedurally generated hex map",
                "action": self.start_new_game,
                "rect": None
            },
            {
                "text": "Load Map",
                "desc": "Continue a previously saved adventure",
                "action": self.load_saved_map,
                "rect": None
            },
            {
                "text": "Import Map",
                "desc": "Import a generated map or converted image map",
                "action": self.import_map,
                "rect": None
            },
            {
                "text": "Convert Image",
                "desc": "Convert a map image to hex format using AI",
                "action": self.open_converter,
                "rect": None
            },
            {
                "text": "Generate Realistic Map",
                "desc": "Create realistic terrain maps with continents and biomes",
                "action": self.open_realistic_generator,
                "rect": None
            },
            {
                "text": "Settings",
                "desc": "Configure game options and AI models",
                "action": self.open_settings,
                "rect": None
            },
            {
                "text": "Quit",
                "desc": "Exit to desktop",
                "action": self.quit_game,
                "rect": None
            }
        ]
        
        # Animation variables
        self.animation_timer = 0
        self.hex_particles = self.create_hex_particles()
        
        # Selected button
        self.selected_button = None
        self.hover_button = None
        
        # Settings
        self.settings = self.load_settings()
        
        self.running = True
    
    def update_font_sizes(self):
        """Update font sizes based on window size"""
        base_size = min(self.width, self.height)
        
        self.title_font = pygame.font.Font(None, int(base_size * 0.09))
        self.subtitle_font = pygame.font.Font(None, int(base_size * 0.045))
        self.button_font = pygame.font.Font(None, int(base_size * 0.06))
        self.desc_font = pygame.font.Font(None, int(base_size * 0.03))
        self.version_font = pygame.font.Font(None, int(base_size * 0.025))
    
    def handle_resize(self, event):
        """Handle window resize event"""
        self.width = event.w
        self.height = event.h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.update_font_sizes()
        self.hex_particles = self.create_hex_particles()
    
    def create_hex_particles(self):
        """Create floating hex particles for background"""
        particles = []
        particle_count = int((self.width * self.height) / 30000)  # Scale with screen size
        for _ in range(max(10, min(particle_count, 50))):
            particle = {
                "x": random.randint(0, self.width),
                "y": random.randint(0, self.height),
                "size": random.randint(int(self.width * 0.01), int(self.width * 0.04)),
                "speed": random.uniform(0.5, 2),
                "alpha": random.randint(20, 60),
                "rotation": random.uniform(0, 360)
            }
            particles.append(particle)
        return particles
    
    def draw_hex(self, x, y, size, color, alpha=255):
        """Draw a hexagon"""
        surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        points = []
        for i in range(6):
            angle = math.pi / 3 * i
            px = size + size * math.cos(angle)
            py = size + size * math.sin(angle)
            points.append((px, py))
        
        # Draw with alpha
        color_with_alpha = (*color, alpha)
        pygame.draw.polygon(surface, color_with_alpha, points)
        pygame.draw.polygon(surface, (*color, min(255, alpha + 50)), points, 1)
        
        self.screen.blit(surface, (x - size, y - size))
    
    def update_particles(self):
        """Update floating hex particles"""
        for particle in self.hex_particles:
            particle["y"] -= particle["speed"]
            particle["rotation"] += 1
            
            # Reset particle at bottom
            if particle["y"] < -particle["size"] * 2:
                particle["y"] = self.height + particle["size"] * 2
                particle["x"] = random.randint(0, self.width)
    
    def draw_background(self):
        """Draw animated background"""
        self.screen.fill(self.bg_color)
        
        # Draw floating hexagons
        for particle in self.hex_particles:
            self.draw_hex(
                particle["x"], 
                particle["y"], 
                particle["size"],
                (50, 60, 80),
                particle["alpha"]
            )
    
    def draw_title(self):
        """Draw the main title"""
        # Main title
        title_text = self.title_font.render("HEX EXPLORER", True, self.title_color)
        title_rect = title_text.get_rect(center=(self.width // 2, self.height * 0.13))
        
        # Add shadow
        shadow_text = self.title_font.render("HEX EXPLORER", True, (0, 0, 0))
        shadow_rect = shadow_text.get_rect(center=(self.width // 2 + 3, self.height * 0.13 + 3))
        self.screen.blit(shadow_text, shadow_rect)
        self.screen.blit(title_text, title_rect)
        
        # Subtitle
        subtitle = self.subtitle_font.render("D&D 5e Travel System", True, self.desc_color)
        sub_rect = subtitle.get_rect(center=(self.width // 2, self.height * 0.22))
        self.screen.blit(subtitle, sub_rect)
    
    def draw_buttons(self):
        """Draw menu buttons"""
        button_width = int(self.width * 0.375)  # 37.5% of screen width
        button_height = int(self.height * 0.07)  # Slightly smaller buttons
        start_y = int(self.height * 0.25)  # Start higher up
        
        # Calculate even spacing based on number of buttons
        available_height = self.height - start_y - 60  # Leave space for footer
        spacing = available_height // len(self.buttons)  # Even distribution
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, button in enumerate(self.buttons):
            x = self.width // 2 - button_width // 2
            y = start_y + i * spacing
            
            # Ensure buttons don't go off screen
            if y + button_height > self.height - 60:
                y = self.height - 60 - button_height
            
            # Create button rect
            button["rect"] = pygame.Rect(x, y, button_width, button_height)
            
            # Check hover
            is_hover = button["rect"].collidepoint(mouse_pos)
            if is_hover:
                self.hover_button = i
                color = self.button_hover
                # Draw description on hover (to the side if at bottom)
                desc_text = self.desc_font.render(button["desc"], True, self.desc_color)
                if i >= 4:  # For bottom buttons, show description to the side
                    desc_rect = desc_text.get_rect(midleft=(x + button_width + 10, y + button_height // 2))
                else:
                    desc_rect = desc_text.get_rect(center=(self.width // 2, y + button_height + 10))
                
                # Make sure description fits on screen
                if desc_rect.right > self.width - 10:
                    desc_rect.right = self.width - 10
                if desc_rect.bottom > self.height - 30:
                    desc_rect.bottom = y - 5
                    
                self.screen.blit(desc_text, desc_rect)
            else:
                color = self.button_color
            
            # Draw button background
            pygame.draw.rect(self.screen, color, button["rect"])
            pygame.draw.rect(self.screen, self.title_color if is_hover else (100, 100, 100), 
                           button["rect"], 2)
            
            # Draw button text
            text = self.button_font.render(button["text"], True, self.button_text)
            text_rect = text.get_rect(center=(self.width // 2, y + button_height // 2))
            self.screen.blit(text, text_rect)
    
    def draw_footer(self):
        """Draw footer information"""
        version_text = "v1.0 - Modular Architecture | Powered by Qwen 2.5 & LLaVA"
        footer = self.version_font.render(version_text, True, self.desc_color)
        footer_rect = footer.get_rect(center=(self.width // 2, self.height * 0.97))
        self.screen.blit(footer, footer_rect)

        # Controls hint
        controls = self.version_font.render("Click to select | ESC to go back", True, self.desc_color)
        controls_rect = controls.get_rect(center=(self.width // 2, self.height * 0.93))
        self.screen.blit(controls, controls_rect)

    def show_message(self, title, message):
        """Display a simple in-window message"""
        lines = textwrap.wrap(message, 60)
        box = pygame.Rect(self.width * 0.1, self.height * 0.3,
                          self.width * 0.8, self.height * 0.4)

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE
                ):
                    waiting = False

            self.draw_background()
            pygame.draw.rect(self.screen, self.button_color, box)
            pygame.draw.rect(self.screen, self.title_color, box, 2)

            title_surf = self.subtitle_font.render(title, True, self.button_text)
            self.screen.blit(title_surf,
                             title_surf.get_rect(center=(self.width // 2,
                                                         box.y + 40)))

            for i, line in enumerate(lines):
                text_surf = self.desc_font.render(line, True, self.button_text)
                self.screen.blit(text_surf,
                                 (box.x + 20,
                                  box.y + 80 + i * (self.desc_font.get_height() + 5)))

            hint = self.version_font.render(
                "Press ENTER or ESC to continue", True, self.desc_color)
            self.screen.blit(hint,
                             hint.get_rect(center=(self.width // 2, box.bottom - 30)))

            pygame.display.flip()
            self.clock.tick(60)

    def show_text_input(self, title, prompt, initial=""):
        """Prompt the user for text input within the window"""
        text = initial
        pygame.key.start_text_input()
        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.quit_game()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return None
                        elif event.key == pygame.K_RETURN:
                            return text.strip()
                        elif event.key == pygame.K_BACKSPACE:
                            text = text[:-1]
                        elif event.unicode.isprintable():
                            text += event.unicode

                self.draw_background()
                title_surf = self.subtitle_font.render(title, True, self.title_color)
                self.screen.blit(title_surf,
                                 title_surf.get_rect(center=(self.width // 2,
                                                             self.height * 0.2)))

                prompt_surf = self.button_font.render(prompt, True, self.button_text)
                self.screen.blit(prompt_surf,
                                 prompt_surf.get_rect(center=(self.width // 2,
                                                              self.height * 0.35)))

                box = pygame.Rect(self.width * 0.2,
                                   self.height * 0.45,
                                   self.width * 0.6,
                                   self.button_font.get_height() * 1.6)
                pygame.draw.rect(self.screen, self.button_color, box)
                pygame.draw.rect(self.screen, self.title_color, box, 2)
                input_surf = self.button_font.render(text, True, self.title_color)
                self.screen.blit(input_surf,
                                 input_surf.get_rect(center=box.center))

                hint = self.version_font.render(
                    "Enter to confirm, Esc to cancel", True, self.desc_color)
                self.screen.blit(hint,
                                 hint.get_rect(center=(self.width // 2,
                                                       self.height * 0.8)))

                pygame.display.flip()
                self.clock.tick(60)
        finally:
            pygame.key.stop_text_input()

    def show_file_browser(self, title, files):
        """Simple file selector within the window"""
        index = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        index = (index - 1) % len(files)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        index = (index + 1) % len(files)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return files[index]

            self.draw_background()
            title_surf = self.subtitle_font.render(title, True, self.title_color)
            self.screen.blit(title_surf,
                             title_surf.get_rect(center=(self.width // 2,
                                                         self.height * 0.15)))

            start_y = self.height * 0.25
            for i, name in enumerate(files):
                color = self.title_color if i == index else self.button_text
                text = self.button_font.render(name, True, color)
                rect = text.get_rect(center=(self.width // 2,
                                             start_y + i * self.button_font.get_height() * 1.3))
                self.screen.blit(text, rect)

            hint = self.version_font.render(
                "Use arrows to navigate, Enter to select, Esc to cancel",
                True, self.desc_color)
            self.screen.blit(hint,
                             hint.get_rect(center=(self.width // 2,
                                                   self.height * 0.9)))

            pygame.display.flip()
            self.clock.tick(60)

    def convert_image_to_hex_map(self, image_path, width_miles, height_miles, hex_size):
        """Convert an image to hex map data using basic color analysis"""
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            self.show_message("Error", f"Failed to load image: {e}")
            return None

        hex_cols = max(1, int(width_miles / hex_size))
        hex_rows = max(1, int(height_miles / hex_size))
        image = image.resize((hex_cols, hex_rows))
        pixels = np.array(image)

        hexes = []
        for row in range(hex_rows):
            for col in range(hex_cols):
                r, g, b = pixels[row, col]
                terrain = "plains"
                if b > r and b > g and b > 100:
                    terrain = "water"
                elif g > r and g > 100:
                    terrain = "forest" if g < 150 else "plains"
                elif r > 150 and g > 100 and b < 100:
                    terrain = "desert" if r > 200 else "hills"
                elif r < 100 and g < 100 and b < 100:
                    terrain = "mountains"
                elif r > 200 and g > 200 and b > 200:
                    terrain = "tundra"
                elif g > 80 and b > 80 and r < 100:
                    terrain = "swamp"

                q = col
                r_offset = row - (col - (col & 1)) // 2
                s = -q - r_offset
                hexes.append({
                    "q": q,
                    "r": r_offset,
                    "s": s,
                    "terrain": terrain,
                    "description": f"A {terrain} region",
                    "explored": False,
                    "visible": False
                })

        return {"hexes": hexes}

    def show_settings_screen(self):
        """In-window settings configuration"""
        options = [
            ("AI Model", ["qwen2.5:3b", "mistral:7b", "llama3:8b"],
             self.settings.get("ai_model", "qwen2.5:3b")),
            ("Vision Model", ["llava:7b", "bakllava:7b"],
             self.settings.get("vision_model", "llava:7b")),
            ("Ollama URL", None,
             self.settings.get("ollama_url", "http://localhost:11434")),
        ]
        index = 0
        pygame.key.start_text_input()
        try:
            while True:
                self.clock.tick(60)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.quit_game()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            return
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            index = (index - 1) % len(options)
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            index = (index + 1) % len(options)
                        elif event.key in (pygame.K_LEFT, pygame.K_a):
                            name, vals, val = options[index]
                            if vals:
                                val = vals[(vals.index(val) - 1) % len(vals)]
                                options[index] = (name, vals, val)
                        elif event.key in (pygame.K_RIGHT, pygame.K_d):
                            name, vals, val = options[index]
                            if vals:
                                val = vals[(vals.index(val) + 1) % len(vals)]
                                options[index] = (name, vals, val)
                        elif event.key == pygame.K_BACKSPACE and index == 2:
                            name, vals, val = options[index]
                            val = val[:-1]
                            options[index] = (name, vals, val)
                        elif event.key == pygame.K_RETURN:
                            self.settings["ai_model"] = options[0][2]
                            self.settings["vision_model"] = options[1][2]
                            self.settings["ollama_url"] = options[2][2]
                            self.save_settings()
                            self.show_message("Settings", "Settings saved.")
                            return
                        else:
                            if index == 2 and event.unicode.isprintable():
                                name, vals, val = options[index]
                                val += event.unicode
                                options[index] = (name, vals, val)

                self.draw_background()
                title = self.title_font.render("Settings", True, self.title_color)
                self.screen.blit(title,
                                 title.get_rect(center=(self.width // 2,
                                                        self.height * 0.15)))

                start_y = self.height * 0.3
                for i, (name, vals, val) in enumerate(options):
                    color = self.title_color if i == index else self.button_text
                    text = self.button_font.render(f"{name}: {val}", True, color)
                    rect = text.get_rect(center=(self.width // 2,
                                                 start_y + i * self.button_font.get_height() * 1.4))
                    self.screen.blit(text, rect)

                hint = self.version_font.render(
                    "Arrows to change, Enter to save, Esc to cancel",
                    True, self.desc_color)
                self.screen.blit(hint,
                                 hint.get_rect(center=(self.width // 2,
                                                       self.height * 0.9)))

                pygame.display.flip()
        finally:
            pygame.key.stop_text_input()
    
    def start_new_game(self):
        """Start a new hex map adventure using modular system"""
        print("Starting new adventure with modular system...")
        self.running = False
        
        # Simple direct launch without complex pygame transitions
        try:
            from application import HexMapExplorer
            
            # Keep the current display and just resize it
            info = pygame.display.Info()
            width = max(1024, min(int(info.current_w * 0.9), 1920))
            height = max(768, min(int(info.current_h * 0.9), 1080))
            
            # Create and run the modular explorer
            explorer = HexMapExplorer()
            # Update screen size if needed
            if explorer.screen.get_size() != (width, height):
                try:
                    explorer.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    explorer.renderer.handle_resize(width, height)
                except:
                    pass  # Keep current size if resize fails
            
            explorer.run()
            
        except ImportError as e:
            print(f"Import error: {e}")
            self.show_message("Error",
                               f"Could not load modular game: {e}\nMake sure all modules are properly installed.")
            self.running = True
        except Exception as e:
            print(f"Runtime error: {e}")
            import traceback
            traceback.print_exc()
            self.show_message("Error", f"Failed to start game: {e}")
            self.running = True
    
    def load_saved_map(self):
        """Load a previously saved map using modular system"""
        directory = "maps"
        try:
            files = [f for f in os.listdir(directory) if f.endswith(".json")]
        except FileNotFoundError:
            files = []

        if not files:
            self.show_message("No Maps",
                              "No JSON maps found in the 'maps' directory.")
            return

        selection = self.show_file_browser("Select Map", files)
        if not selection:
            return

        filename = os.path.join(directory, selection)
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                if "hexes" not in data:
                    raise ValueError("Invalid map file")

            from application import HexMapExplorer
            self.running = False

            explorer = HexMapExplorer()
            explorer.hex_map.load_from_json(filename)
            explorer.renderer.set_message("Map loaded from menu!")
            explorer.run()

        except ImportError as e:
            self.show_message("Error", f"Could not load modular game: {e}")
            self.running = True
        except Exception as e:
            self.show_message("Error", f"Failed to load map: {e}")
            self.running = True
    def open_converter(self):
        """Convert a map image to hex format within the app"""
        directory = "."
        files = [f for f in os.listdir(directory)
                 if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        if not files:
            self.show_message("No Images",
                              "Place PNG or JPG files in the app directory.")
            return

        selection = self.show_file_browser("Select Image", files)
        if not selection:
            return
        image_path = os.path.join(directory, selection)

        w = self.show_text_input("Convert Image", "Map width in miles:", "30")
        if w is None:
            return
        h = self.show_text_input("Convert Image", "Map height in miles:", "30")
        if h is None:
            return
        size = self.show_text_input("Convert Image", "Hex size in miles:", "3")
        if size is None:
            return
        try:
            width_m = float(w)
            height_m = float(h)
            hex_size = float(size)
        except ValueError:
            self.show_message("Error", "Invalid numeric input.")
            return

        map_data = self.convert_image_to_hex_map(image_path, width_m, height_m, hex_size)
        if not map_data:
            return

        os.makedirs("maps", exist_ok=True)
        out_name = os.path.splitext(os.path.basename(image_path))[0] + "_converted.json"
        with open(os.path.join("maps", out_name), "w") as f:
            json.dump(map_data, f)

        self.start_game_with_map(map_data)

    def open_realistic_generator(self):
        """Generate a realistic map without popups"""
        width_text = self.show_text_input("Generate Map", "Width (hexes):", "50")
        if width_text is None:
            return
        height_text = self.show_text_input("Generate Map", "Height (hexes):", "50")
        if height_text is None:
            return
        try:
            width = int(width_text)
            height = int(height_text)
        except ValueError:
            self.show_message("Error", "Width and height must be numbers.")
            return

        generator = StableMapGenerator()
        map_data = generator.generate_realistic_map(width, height)

        os.makedirs("maps", exist_ok=True)
        out_name = f"realistic_{width}x{height}_{random.randint(1000,9999)}.json"
        with open(os.path.join("maps", out_name), "w") as f:
            json.dump(map_data, f)

        self.start_game_with_map(map_data)

    def import_map(self):
        """Import a map JSON and start exploring"""
        directory = "."
        files = [f for f in os.listdir(directory) if f.lower().endswith(".json")]
        if not files:
            self.show_message("No Maps",
                              "No JSON files found in the app directory.")
            return

        selection = self.show_file_browser("Import Map", files)
        if not selection:
            return

        filename = os.path.join(directory, selection)
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            if "hexes" not in data:
                raise ValueError("Invalid map file")
            self.start_game_with_map(data)
        except Exception as e:
            self.show_message("Error", f"Failed to import map: {e}")

    def start_game_with_map(self, map_data):
        """Start the game with an imported map"""
        try:
            from application import HexMapExplorer
            
            self.running = False
            
            # Create explorer
            explorer = HexMapExplorer()
            
            # Load the map data
            explorer.hex_map.hexes.clear()
            
            # Load hexes
            from core.hex import Hex
            for hex_data in map_data["hexes"]:
                hex_obj = Hex.from_dict(hex_data)
                explorer.hex_map.hexes[(hex_obj.q, hex_obj.r, hex_obj.s)] = hex_obj
            
            # Find a good starting position (preferably land near center)
            start_pos = self.find_good_starting_position(explorer.hex_map.hexes)
            explorer.hex_map.current_position = start_pos
            
            # Make starting area visible and explored
            start_hex = explorer.hex_map.hexes.get(start_pos)
            if start_hex:
                start_hex.explored = True
                start_hex.visible = True
                
                # Make nearby hexes visible
                neighbors = explorer.hex_map.coords.get_neighbors(*start_pos)
                for nq, nr, ns in neighbors:
                    neighbor_hex = explorer.hex_map.hexes.get((nq, nr, ns))
                    if neighbor_hex:
                        neighbor_hex.visible = True
            
            # Load travel data if available
            if "travel_data" in map_data:
                explorer.hex_map.travel_system.load_from_data(map_data["travel_data"])
            
            explorer.hex_map.calculate_distances()
            
            print(f"Loaded map with {len(explorer.hex_map.hexes)} hexes")
            print(f"Starting position: {start_pos}")
            
            explorer.run()
            
        except Exception as e:
            self.show_message("Error",
                              f"Failed to start game with imported map: {e}")
            self.running = True
    
    def find_good_starting_position(self, hexes):
        """Find a good starting position on land near the center"""
        # Try to find land hexes near the center
        candidates = []
        
        for (q, r, s), hex_obj in hexes.items():
            # Skip water hexes
            if hex_obj.terrain == "water":
                continue
            
            # Calculate distance from center
            distance = abs(q) + abs(r) + abs(s)  # Manhattan distance in hex space
            
            # Prefer positions closer to center
            candidates.append((distance, (q, r, s), hex_obj.terrain))
        
        if candidates:
            # Sort by distance and pick the closest land hex
            candidates.sort()
            _, position, terrain = candidates[0]
            print(f"Found starting position at {position} ({terrain})")
            return position
        else:
            # Fallback to (0,0,0) if no good position found
            print("No good starting position found, using (0,0,0)")
            return (0, 0, 0)
    def open_settings(self):
        """Open settings dialog"""
        self.show_settings_screen()

    def load_settings(self):
        """Load settings from file"""
        try:
            with open("settings.json", "r") as f:
                return json.load(f)
        except:
            # Default settings
            return {
                "ai_model": "qwen2.5:3b",
                "vision_model": "llava:7b",
                "ollama_url": "http://localhost:11434"
            }
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def quit_game(self):
        """Exit the application"""
        self.running = False
        pygame.quit()
        sys.exit()
    
    def handle_click(self, pos):
        """Handle mouse clicks"""
        for i, button in enumerate(self.buttons):
            if button["rect"] and button["rect"].collidepoint(pos):
                button["action"]()
                break
    
    def run(self):
        """Main menu loop"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.animation_timer += dt
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit_game()
                    elif event.key == pygame.K_F11:
                        # Toggle fullscreen
                        pygame.display.toggle_fullscreen()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
            
            # Update animations
            self.update_particles()
            
            # Draw everything
            self.draw_background()
            self.draw_title()
            self.draw_buttons()
            self.draw_footer()
            
            pygame.display.flip()

def check_requirements():
    """Check if all required packages are installed"""
    required = ["pygame", "requests", "PIL", "numpy"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Missing required packages:")
        for package in missing:
            print(f"  - {package}")
        print("\nInstall with: pip install pygame requests pillow numpy")
        return False
    
    return True

def check_modular_system():
    """Check if the modular system is properly set up"""
    print("Checking modular system...")
    
    modules = [
        ("config", "Configuration"),
        ("core", "Core Systems"),
        ("travel", "Travel System"),
        ("generation", "AI Generation"),
        ("rendering", "Renderer"),
        ("application", "Main Application"),
        ("utils", "Utilities")
    ]
    
    all_good = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print(f"  ✅ {description}")
        except ImportError as e:
            print(f"  ❌ {description} - {e}")
            all_good = False
    
    return all_good

def set_window_icon(self):
    """Set the window icon using working PNG files"""
    icon_files = [
        "hex_explorer_icon_32x32.png",      # Best size for icons
        "hex_explorer_icon_64x64.png", 
        "hex_explorer_icon_128x128.png",
        "hex_explorer_icon_256x256.png"
    ]
    
    for icon_file in icon_files:
        if os.path.exists(icon_file):
            try:
                icon = pygame.image.load(icon_file)
                pygame.display.set_icon(icon)
                print(f"✅ Window icon set: {icon_file}")
                return True
            except Exception as e:
                print(f"⚠️  Could not load {icon_file}: {e}")
                continue
    
    print("⚠️  No working icon files found")
    return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama is running with {len(models)} models")
            return True
    except:
        pass
    
    print("⚠️  WARNING: Ollama not detected!")
    print("The game will use fallback descriptions.")
    print("\nTo enable AI features:")
    print("  1. Install Ollama from https://ollama.ai")
    print("  2. Run: ollama pull qwen2.5:3b")
    print("  3. Run: ollama pull llava:7b")
    print("  4. Run: ollama serve")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("HEX MAP EXPLORER - MODULAR VERSION")
    print("=" * 50)
    print("\nA D&D 5e-inspired hex crawl adventure game")
    print("with AI-powered descriptions and modular architecture")
    print("-" * 50)
    
    # Check requirements
    if not check_requirements():
        print("\nPlease install missing packages before running.")
        sys.exit(1)
    
    # Check modular system
    if not check_modular_system():
        print("\nModular system not properly set up!")
        print("Make sure all module files are in the correct directories.")
        print("See the modular structure documentation for setup instructions.")
        sys.exit(1)
    
    # Check Ollama (optional)
    check_ollama()
    print("-" * 50)
    print("🚀 Starting Main Menu...")
    
    # Run main menu
    menu = MainMenu()
    menu.run()
