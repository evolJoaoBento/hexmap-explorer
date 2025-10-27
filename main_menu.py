import pygame
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import random
import math
import requests

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
        
        # Default UI scale; may be overridden by settings after load
        self.ui_scale = 1.0
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
        
        # Seed selection
        self.current_seed = random.randint(1, 1000000)
        self.seed_input_active = False
        self.seed_input_text = str(self.current_seed)
        # Apply UI scale from settings if present and recompute fonts
        try:
            self.ui_scale = float(self.settings.get("ui_scale", 1.0))
        except Exception:
            self.ui_scale = 1.0
        self.update_font_sizes()
        
        self.running = True
    
    def update_font_sizes(self):
        """Update font sizes based on window size"""
        base_size = min(self.width, self.height)
        scale = getattr(self, "ui_scale", 1.0)
        
        self.title_font = pygame.font.Font(None, int(base_size * 0.09 * scale))
        self.subtitle_font = pygame.font.Font(None, int(base_size * 0.045 * scale))
        self.button_font = pygame.font.Font(None, int(base_size * 0.06 * scale))
        self.desc_font = pygame.font.Font(None, int(base_size * 0.03 * scale))
        self.version_font = pygame.font.Font(None, int(base_size * 0.025 * scale))
    
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
            # Add extra spacing after the first button (New Adventure) to make room for seed UI
            if i == 0:
                y = start_y + i * spacing
            else:
                y = start_y + i * spacing + 40  # Extra 40px spacing for seed UI
            
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
            
            # Store position for seed UI (after New Adventure button)
            if i == 0:  # First button (New Adventure)
                self.new_adventure_bottom = y + button_height + 10
    
    def draw_seed_selection(self, start_y):
        """Draw seed selection UI"""
        # Calculate consistent positioning - more compact layout
        center_x = self.width // 2
        
        # Make it all fit on one line horizontally
        # Label positioning - smaller and more to the left
        seed_label = self.desc_font.render("World Seed:", True, self.desc_color)
        label_x = center_x - 110
        label_y = start_y + 10
        self.screen.blit(seed_label, (label_x, label_y))
        
        # Seed input box - compact and centered
        input_width = 80
        input_height = 25
        input_x = center_x - 20
        input_y = start_y + 5
        input_rect = pygame.Rect(input_x, input_y, input_width, input_height)
        
        # Store for click detection
        self.seed_input_rect = input_rect
        
        # Draw input box
        input_color = (90, 100, 120) if self.seed_input_active else (70, 80, 100)
        border_color = self.title_color if self.seed_input_active else (100, 100, 100)
        pygame.draw.rect(self.screen, input_color, input_rect)
        pygame.draw.rect(self.screen, border_color, input_rect, 2)
        
        # Draw seed text - center it in the input box
        seed_text = self.desc_font.render(str(self.seed_input_text), True, self.button_text)
        text_rect = seed_text.get_rect(center=input_rect.center)
        self.screen.blit(seed_text, text_rect)
        
        # Randomize button - smaller and closer to input
        rand_width = 60
        rand_height = 25
        rand_x = input_x + input_width + 10
        rand_y = start_y + 5
        rand_rect = pygame.Rect(rand_x, rand_y, rand_width, rand_height)
        
        # Store for click detection
        self.randomize_rect = rand_rect
        
        # Check hover for randomize button
        mouse_pos = pygame.mouse.get_pos()
        rand_hover = rand_rect.collidepoint(mouse_pos)
        rand_color = self.button_hover if rand_hover else self.button_color
        
        # Draw randomize button
        pygame.draw.rect(self.screen, rand_color, rand_rect)
        pygame.draw.rect(self.screen, self.title_color if rand_hover else (100, 100, 100), 
                        rand_rect, 2)
        
        # Draw randomize button text - smaller font for compact button
        rand_text = self.version_font.render("Random", True, self.button_text)  # Smaller font
        rand_text_rect = rand_text.get_rect(center=rand_rect.center)
        self.screen.blit(rand_text, rand_text_rect)
    
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
    
    def start_new_game(self):
        """Start a new hex map adventure using modular system"""
        # Use current seed from menu
        seed = self.current_seed
        print(f"Starting new adventure with seed: {seed}")
        self.running = False
        
        # Simple direct launch without complex pygame transitions
        try:
            from application import HexMapExplorer
            
            # Keep the current display and just resize it
            info = pygame.display.Info()
            width = max(1024, min(int(info.current_w * 0.9), 1920))
            height = max(768, min(int(info.current_h * 0.9), 1080))
            
            # Create and run the modular explorer with selected seed
            explorer = HexMapExplorer(seed=seed)
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
            messagebox.showerror("Error", f"Could not load modular game: {e}\n\nMake sure all modules are properly installed.")
            self.running = True
        except Exception as e:
            print(f"Runtime error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to start game: {e}")
            self.running = True
    
    def load_saved_map(self):
        """Load a previously saved map using modular system"""
        root = tk.Tk()
        root.withdraw()
        
        filename = filedialog.askopenfilename(
            title="Load Saved Map",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Check if it's a valid map file
                with open(filename, 'r') as f:
                    data = json.load(f)
                    if "hexes" not in data:
                        raise ValueError("Invalid map file")
                
                # Start modular game with loaded map
                from application import HexMapExplorer
                self.running = False
                
                explorer = HexMapExplorer()
                explorer.hex_map.load_from_json(filename)
                explorer.renderer.set_message("Map loaded from menu!")
                explorer.run()
                
            except ImportError as e:
                messagebox.showerror("Error", f"Could not load modular game: {e}")
                self.running = True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load map: {e}")
                self.running = True
        
        root.destroy()
    
    def import_converted_map(self):
        """Import a converted map with options using modular system"""
        try:
            # Try to import map converter (may not exist in modular version)
            try:
                from map_image_converter import MapImportDialog
            except ImportError:
                messagebox.showwarning("Feature Not Available", 
                    "Map image converter not available in this modular version.\n"
                    "This feature may be added in a future update.")
                return
            
            from application import HexMapExplorer
            from generation import OllamaClient, GenerationManager
            
            self.running = False
            explorer = HexMapExplorer()
            
            # Open import dialog
            root = tk.Tk()
            root.withdraw()
            dialog = MapImportDialog(root, explorer.hex_map)
            root.wait_window(dialog.dialog)
            root.destroy()
            
            # If map was imported, run the game
            if explorer.hex_map.hexes:
                explorer.renderer.set_message("Map imported successfully!")
                explorer.run()
            else:
                self.running = True  # Return to menu if cancelled
                
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")
            self.running = True
    
    def open_converter(self):
        """Open the map image converter"""
        try:
            # Try to import map converter (may not exist in modular version)
            try:
                from map_image_converter import MapImageConverter
            except ImportError:
                messagebox.showwarning("Feature Not Available", 
                    "Map image converter not available in this modular version.\n"
                    "This feature may be added in a future update.")
                return
            
            root = tk.Tk()
            root.withdraw()
            
            converter = MapImageConverter()
            converter.open_converter_window()
            
            # Keep the converter window open
            root.mainloop()
            
        except Exception as e:
            messagebox.showerror("Error", f"Converter failed: {e}")
    
    def open_realistic_generator(self):
        """Open the realistic map generator"""
        try:
            print("Opening realistic map generator...")
            # Use the stable GUI generator
            subprocess.run([sys.executable, "stable_map_generator.py"], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to run map generator: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
    
    def import_map(self):
        """Import any type of map (realistic, converted, etc.)"""
        try:
            # Create custom import dialog
            import_window = tk.Tk()
            import_window.title("Import Map")
            import_window.geometry("400x200")
            
            self.selected_map_file = None
            self.selected_map_data = None
            
            def select_file():
                filename = filedialog.askopenfilename(
                    title="Select Map File",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if filename:
                    try:
                        with open(filename, 'r') as f:
                            map_data = json.load(f)
                        
                        if "hexes" not in map_data:
                            messagebox.showerror("Invalid Map", "This file doesn't contain valid hex map data.")
                            return
                        
                        self.selected_map_file = filename
                        self.selected_map_data = map_data
                        
                        # Update file label
                        file_label.config(text=f"Selected: {filename.split('/')[-1]}")
                        
                        # Enable buttons
                        preview_btn.config(state=tk.NORMAL)
                        import_btn.config(state=tk.NORMAL)
                        
                        # Show map info
                        info_text = f"Size: {map_data.get('width', '?')}x{map_data.get('height', '?')}\n"
                        info_text += f"Hexes: {len(map_data['hexes'])}\n"
                        info_text += f"Seed: {map_data.get('seed', 'Unknown')}"
                        info_label.config(text=info_text)
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to load map: {e}")
            
            def preview_map():
                if self.selected_map_data:
                    try:
                        # Launch map preview
                        subprocess.run([sys.executable, "map_preview.py"], check=True)
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to open preview: {e}")
            
            def import_selected():
                if self.selected_map_data:
                    import_window.destroy()
                    self.start_game_with_map(self.selected_map_data)
            
            def cancel_import():
                import_window.destroy()
            
            # UI Layout
            tk.Label(import_window, text="Import Hex Map", font=("Arial", 14, "bold")).pack(pady=10)
            
            tk.Button(import_window, text="Select Map File", command=select_file, 
                     bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(pady=5)
            
            file_label = tk.Label(import_window, text="No file selected", fg="gray")
            file_label.pack(pady=5)
            
            info_label = tk.Label(import_window, text="", justify=tk.LEFT)
            info_label.pack(pady=5)
            
            button_frame = tk.Frame(import_window)
            button_frame.pack(pady=10)
            
            preview_btn = tk.Button(button_frame, text="Preview Map", command=preview_map, 
                                   state=tk.DISABLED, bg="#2196F3", fg="white")
            preview_btn.pack(side=tk.LEFT, padx=5)
            
            import_btn = tk.Button(button_frame, text="Import & Play", command=import_selected, 
                                  state=tk.DISABLED, bg="#FF9800", fg="white", 
                                  font=("Arial", 10, "bold"))
            import_btn.pack(side=tk.LEFT, padx=5)
            
            tk.Button(button_frame, text="Cancel", command=cancel_import).pack(side=tk.LEFT, padx=5)
            
            # Make it modal
            import_window.transient()
            import_window.grab_set()
            import_window.mainloop()
            
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")
    
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
            messagebox.showerror("Error", f"Failed to start game with imported map: {e}")
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
        """Open settings screen"""
        self.settings_menu()

    def settings_menu(self):
        """Display settings using the pygame window"""
        # Heuristic classification for vision-capable models
        VISION_HINTS = ("llava", "bakllava", "vision", "moondream", "qwen2-vl", "phi-3-vision")

        def fetch_available_models(base_url):
            """Fetch models from Ollama and split into text/vision lists with status."""
            ai_models = []
            vision_models = []
            status = "Not connected"
            status_color = (255, 150, 150)
            try:
                resp = requests.get(base_url.rstrip("/") + "/api/tags", timeout=1.5)
                if resp.status_code == 200:
                    data = resp.json() or {}
                    all_models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    for name in all_models:
                        lname = name.lower()
                        if any(h in lname for h in VISION_HINTS):
                            vision_models.append(name)
                        else:
                            ai_models.append(name)
                    if not ai_models:
                        ai_models = ["qwen2.5:3b", "mistral:7b", "llama3:8b"]
                    if not vision_models:
                        vision_models = ["llava:7b", "bakllava:7b"]
                    status = f"Connected ({len(all_models)} models)"
                    status_color = (150, 255, 150)
                else:
                    ai_models = ["qwen2.5:3b", "mistral:7b", "llama3:8b"]
                    vision_models = ["llava:7b", "bakllava:7b"]
                    status = f"Error {resp.status_code}"
            except Exception:
                ai_models = ["qwen2.5:3b", "mistral:7b", "llama3:8b"]
                vision_models = ["llava:7b", "bakllava:7b"]
            return ai_models, vision_models, status, status_color

        url_text = self.settings.get("ollama_url", "http://localhost:11434")
        ai_options, vision_options, conn_status, conn_color = fetch_available_models(url_text)

        # Ensure currently saved models are present in option lists
        current_ai = self.settings.get("ai_model", ai_options[0])
        current_vision = self.settings.get("vision_model", vision_options[0])
        if current_ai not in ai_options:
            ai_options = [current_ai] + ai_options
        if current_vision not in vision_options:
            vision_options = [current_vision] + vision_options

        ai_index = ai_options.index(current_ai)
        vision_index = vision_options.index(current_vision)

        active_field = None
        show_ai = False
        show_vision = False

        def draw_button(rect, text, hovered):
            """Draw a standard centered button"""
            pygame.draw.rect(self.screen, self.button_hover if hovered else self.button_color, rect)
            pygame.draw.rect(self.screen, self.title_color if hovered else (100, 100, 100), rect, 2)
            surf = self.button_font.render(text, True, self.button_text)
            self.screen.blit(surf, surf.get_rect(center=rect.center))

        def draw_combo(rect, label_text, is_open, hovered):
            """Draw a combo-box like control with arrow box on right"""
            # Base box
            pygame.draw.rect(self.screen, self.button_hover if (hovered or is_open) else self.button_color, rect)
            pygame.draw.rect(self.screen, self.title_color if (hovered or is_open) else (100, 100, 100), rect, 2)

            # Arrow box on right
            padding = 4
            arrow_box_size = max(20, rect.height - padding * 2)
            arrow_box = pygame.Rect(rect.right - arrow_box_size - padding, rect.y + padding, arrow_box_size, arrow_box_size)
            pygame.draw.rect(self.screen, (60, 60, 90), arrow_box)
            pygame.draw.rect(self.screen, (150, 150, 180), arrow_box, 1)

            # Draw arrow (triangle)
            cx = arrow_box.centerx
            cy = arrow_box.centery
            tri_w = max(8, arrow_box.width // 3)
            tri_h = max(5, arrow_box.height // 3)
            if is_open:
                points = [(cx - tri_w // 2, cy + tri_h // 3), (cx + tri_w // 2, cy + tri_h // 3), (cx, cy - tri_h // 2)]
            else:
                points = [(cx - tri_w // 2, cy - tri_h // 3), (cx + tri_w // 2, cy - tri_h // 3), (cx, cy + tri_h // 2)]
            pygame.draw.polygon(self.screen, self.button_text, points)

            # Text clipped to leave room for arrow box
            text_padding = 10
            max_text_width = rect.width - (arrow_box.width + padding * 2 + text_padding)
            display_text = label_text
            while self.button_font.size(display_text)[0] > max_text_width and len(display_text) > 0:
                # clip from middle to keep ends useful
                if len(display_text) <= 4:
                    display_text = "…"
                    break
                left = display_text[: len(display_text)//2 - 2]
                right = display_text[len(display_text)//2 + 1 :]
                display_text = left + "…" + right
            text_surf = self.button_font.render(display_text, True, self.button_text)
            text_rect = text_surf.get_rect()
            text_rect.midleft = (rect.x + text_padding, rect.centery)
            self.screen.blit(text_surf, text_rect)

        def draw_text_field(rect, label, text, active):
            """Draw a left-aligned text field with label and safely clipped content"""
            pygame.draw.rect(self.screen, self.button_hover if active else self.button_color, rect)
            pygame.draw.rect(self.screen, self.title_color if active else (100, 100, 100), rect, 2)
            padding = 10
            # Prefer shorter label if needed (keeps last word like 'URL')
            base = f"{label}: "
            display_text = text
            max_width = rect.width - 2 * padding
            # If the label itself is too wide, abbreviate to last word
            if self.button_font.size(base)[0] > max_width * 0.6:
                short_label = (label.split()[-1] if label.split() else label)[:6]
                base = f"{short_label}: "
            # Clip from the left side preserving the rightmost portion
            while self.button_font.size(base + display_text)[0] > max_width and len(display_text) > 0:
                display_text = display_text[1:]
            if display_text != text:
                display_text = "…" + display_text  # ellipsis
            # Ensure final render never exceeds rect
            composed = base + display_text
            # If still too wide, keep removing from left side
            while self.button_font.size(composed)[0] > max_width and len(display_text) > 0:
                display_text = display_text[1:]
                composed = base + ("…" + display_text if display_text else "")
            # As a last resort, if even base + ellipsis doesn't fit, fall back to just ellipsis
            if self.button_font.size(composed)[0] > max_width:
                composed = "…"
            surf = self.button_font.render(composed, True, self.button_text)
            self.screen.blit(surf, (rect.x + padding, rect.y + rect.height / 2 - surf.get_height() / 2))

        modules_status = []
        try:
            from core import HexMap  # noqa: F401
            modules_status.append("[OK] Core System")
        except Exception:
            modules_status.append("[FAIL] Core System")
        try:
            from travel import TravelSystem  # noqa: F401
            modules_status.append("[OK] Travel System")
        except Exception:
            modules_status.append("[FAIL] Travel System")
        try:
            from generation import OllamaClient  # noqa: F401
            modules_status.append("[OK] AI Generation")
        except Exception:
            modules_status.append("[FAIL] AI Generation")
        try:
            from rendering import HexMapRenderer  # noqa: F401
            modules_status.append("[OK] Renderer")
        except Exception:
            modules_status.append("[FAIL] Renderer")
        status_text = " | ".join(modules_status)

        running = True
        while running and self.running:
            title_surf = self.title_font.render("SETTINGS", True, self.title_color)
            title_rect = title_surf.get_rect(center=(self.width // 2, int(self.height * 0.15)))

            bw = int(self.width * 0.375)
            bh = int(self.height * 0.07)
            x = self.width // 2 - bw // 2
            start_y = int(self.height * 0.3)

            ai_rect = pygame.Rect(x, start_y, bw, bh)
            vision_rect = pygame.Rect(x, start_y + bh + 20, bw, bh)
            # Place URL field and Refresh button side-by-side without overlap
            # Use a short label and size the button to fit text
            label_refresh = "Refresh"
            temp_surf = self.button_font.render(label_refresh, True, self.button_text)
            needed_w = temp_surf.get_width() + 24  # padding
            refresh_width = max(needed_w, 120, int(bw * 0.2))
            url_rect = pygame.Rect(x, start_y + 2 * (bh + 20), bw - refresh_width - 12, bh)
            refresh_rect = pygame.Rect(url_rect.right + 8, url_rect.y, refresh_width, bh)
            # UI Scale control row above Save/Cancel
            scale_y = start_y + 3 * (bh + 20)
            # Measure button widths to align A+ to right edge
            a_minus_label = "A-"
            a_plus_label = "A+"
            a_minus_w = max(60, self.button_font.size(a_minus_label)[0] + 24)
            a_plus_w = max(60, self.button_font.size(a_plus_label)[0] + 24)
            larger_rect = pygame.Rect(x + bw - a_plus_w, scale_y, a_plus_w, bh)
            smaller_rect = pygame.Rect(x, scale_y, a_minus_w, bh)
            scale_display_rect = pygame.Rect(smaller_rect.right + 8, scale_y, max(50, larger_rect.left - (smaller_rect.right + 16)), bh)
            # Save/Cancel below the scale controls
            save_rect = pygame.Rect(self.width // 2 - bw // 2, start_y + 4 * (bh + 20), bw // 2 - 10, bh)
            cancel_rect = pygame.Rect(self.width // 2 + 10, start_y + 4 * (bh + 20), bw // 2 - 10, bh)

            status_surf = self.desc_font.render(status_text, True, self.desc_color)
            status_rect = status_surf.get_rect(center=(self.width // 2, int(self.height * 0.9)))

            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif active_field == "url":
                        if event.key == pygame.K_RETURN:
                            # Apply URL and refresh model lists
                            ai_options, vision_options, conn_status, conn_color = fetch_available_models(url_text)
                            if self.settings.get("ai_model") in ai_options:
                                ai_index = ai_options.index(self.settings.get("ai_model"))
                            else:
                                ai_index = 0
                            if self.settings.get("vision_model") in vision_options:
                                vision_index = vision_options.index(self.settings.get("vision_model"))
                            else:
                                vision_index = 0
                            active_field = None
                        elif event.key == pygame.K_BACKSPACE:
                            url_text = url_text[:-1]
                        else:
                            url_text += event.unicode
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if show_ai:
                        option_rects = [pygame.Rect(ai_rect.x, ai_rect.bottom + i * bh, bw, bh) for i in range(len(ai_options))]
                        for i, r in enumerate(option_rects):
                            if r.collidepoint(mx, my):
                                ai_index = i
                                show_ai = False
                                break
                    if show_vision:
                        option_rects = [pygame.Rect(vision_rect.x, vision_rect.bottom + i * bh, bw, bh) for i in range(len(vision_options))]
                        for i, r in enumerate(option_rects):
                            if r.collidepoint(mx, my):
                                vision_index = i
                                show_vision = False
                                break
                    if ai_rect.collidepoint(mx, my):
                        show_ai = not show_ai
                        show_vision = False
                    elif vision_rect.collidepoint(mx, my):
                        show_vision = not show_vision
                        show_ai = False
                    elif url_rect.collidepoint(mx, my) and not refresh_rect.collidepoint(mx, my):
                        active_field = "url"
                        show_ai = show_vision = False
                    elif refresh_rect.collidepoint(mx, my):
                        # Re-fetch models and update lists while preserving choices if possible
                        ai_options, vision_options, conn_status, conn_color = fetch_available_models(url_text)
                        if self.settings.get("ai_model") in ai_options:
                            ai_index = ai_options.index(self.settings.get("ai_model"))
                        else:
                            ai_index = 0
                        if self.settings.get("vision_model") in vision_options:
                            vision_index = vision_options.index(self.settings.get("vision_model"))
                        else:
                            vision_index = 0
                        active_field = None
                        show_ai = show_vision = False
                    elif save_rect.collidepoint(mx, my):
                        self.settings["ai_model"] = ai_options[ai_index]
                        self.settings["vision_model"] = vision_options[vision_index]
                        self.settings["ollama_url"] = url_text
                        # Persist UI scale
                        try:
                            self.settings["ui_scale"] = round(float(self.ui_scale), 2)
                        except Exception:
                            pass
                        self.save_settings()
                        running = False
                    elif cancel_rect.collidepoint(mx, my):
                        running = False
                    elif smaller_rect.collidepoint(mx, my):
                        # Decrease UI scale, clamp 0.6 - 1.6
                        self.ui_scale = max(0.6, round(self.ui_scale - 0.1, 2))
                        self.update_font_sizes()
                    elif larger_rect.collidepoint(mx, my):
                        # Increase UI scale
                        self.ui_scale = min(1.6, round(self.ui_scale + 0.1, 2))
                        self.update_font_sizes()
                    else:
                        show_ai = show_vision = False

            self.screen.fill(self.bg_color)
            self.screen.blit(title_surf, title_rect)

            ai_label = f"AI Model: {ai_options[ai_index]} {'▲' if show_ai else '▼'}"
            vision_label = f"Vision Model: {vision_options[vision_index]} {'▲' if show_vision else '▼'}"
            # Steady cursor for URL editing to prevent reflow flicker
            cursor = "|" if active_field == "url" else ""

            hovered_url = url_rect.collidepoint(mouse_pos) or active_field == "url"

            draw_combo(ai_rect, ai_label, show_ai, ai_rect.collidepoint(mouse_pos))
            draw_combo(vision_rect, vision_label, show_vision, vision_rect.collidepoint(mouse_pos))
            draw_text_field(url_rect, "Ollama URL", url_text + cursor, hovered_url)
            # Refresh action and connection status
            draw_button(refresh_rect, label_refresh, refresh_rect.collidepoint(mouse_pos))
            conn_surf = self.desc_font.render(f"Ollama: {conn_status}", True, conn_color)
            conn_rect = conn_surf.get_rect(midleft=(url_rect.x, url_rect.bottom + 8))
            self.screen.blit(conn_surf, conn_rect)
            draw_button(save_rect, "Save", save_rect.collidepoint(mouse_pos))
            draw_button(cancel_rect, "Cancel", cancel_rect.collidepoint(mouse_pos))

            # UI scale controls
            draw_button(smaller_rect, a_minus_label, smaller_rect.collidepoint(mouse_pos))
            scale_text = self.button_font.render(f"Text Size: {self.ui_scale:.1f}x", True, self.button_text)
            self.screen.blit(scale_text, scale_display_rect.move(10, (bh - scale_text.get_height()) // 2))
            draw_button(larger_rect, a_plus_label, larger_rect.collidepoint(mouse_pos))

            self.screen.blit(status_surf, status_rect)

            if show_ai:
                for i, opt in enumerate(ai_options):
                    r = pygame.Rect(ai_rect.x, ai_rect.bottom + i * bh, bw, bh)
                    draw_button(r, opt, r.collidepoint(mouse_pos))
            if show_vision:
                for i, opt in enumerate(vision_options):
                    r = pygame.Rect(vision_rect.x, vision_rect.bottom + i * bh, bw, bh)
                    draw_button(r, opt, r.collidepoint(mouse_pos))
            pygame.display.flip()
            self.clock.tick(60)
    
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
        # Check seed input area first
        if hasattr(self, 'seed_input_rect') and self.seed_input_rect.collidepoint(pos):
            self.seed_input_active = True
            return
        elif hasattr(self, 'randomize_rect') and self.randomize_rect.collidepoint(pos):
            self.randomize_seed()
            return
        else:
            self.seed_input_active = False
        
        # Check regular menu buttons
        for i, button in enumerate(self.buttons):
            if button["rect"] and button["rect"].collidepoint(pos):
                button["action"]()
                break
    
    def handle_seed_input(self, event):
        """Handle keyboard input for seed field"""
        if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
            self.seed_input_active = False
            # Validate and update current seed
            try:
                self.current_seed = int(self.seed_input_text)
            except ValueError:
                # Reset to current seed if invalid
                self.seed_input_text = str(self.current_seed)
        elif event.key == pygame.K_BACKSPACE:
            self.seed_input_text = self.seed_input_text[:-1]
        else:
            # Add character if it's a digit and not too long
            if event.unicode.isdigit() and len(self.seed_input_text) < 8:
                self.seed_input_text += event.unicode
    
    def randomize_seed(self):
        """Generate a new random seed"""
        self.current_seed = random.randint(1, 1000000)
        self.seed_input_text = str(self.current_seed)
    
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
                    elif self.seed_input_active:
                        # Handle seed input
                        self.handle_seed_input(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
            
            # Update animations
            self.update_particles()
            
            # Draw everything
            self.draw_background()
            self.draw_title()
            self.draw_buttons()
            # Draw seed selection after buttons are positioned
            if hasattr(self, 'new_adventure_bottom'):
                self.draw_seed_selection(self.new_adventure_bottom)
            self.draw_footer()
            
            pygame.display.flip()

def check_requirements():
    """Check if all required packages are installed"""
    required = ["pygame", "requests", "PIL", "numpy", "tkinter"]
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
            print(f"  [OK] {description}")
        except ImportError as e:
            print(f"  [FAIL] {description} - {e}")
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
                print(f"[OK] Window icon set: {icon_file}")
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
            print(f"[OK] Ollama is running with {len(models)} models")
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
    print("Starting Main Menu...")
    
    # Run main menu
    menu = MainMenu()
    menu.run()