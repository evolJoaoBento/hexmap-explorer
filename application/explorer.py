"""
Complete main application class using all modular components
"""
import pygame
import time
import random
from typing import Tuple
from config.constants import DEFAULT_WINDOW_SIZE, TRANSPORTATION_MODES
from core.map import HexMap
from generation.ollama_client import OllamaClient
from generation.manager import GenerationManager
from rendering.renderer import HexMapRenderer
from utils.file_operations import save_map_dialog, load_map_dialog, quick_save_dialog


class HexMapExplorer:
    """Main application class using modular components"""
    
    def __init__(self):
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
        
        # Initialize modular components
        self.ollama = OllamaClient()
        self.gen_manager = GenerationManager(self.ollama)
        self.hex_map = HexMap(self.gen_manager)
        self.renderer = HexMapRenderer(self.screen, self.hex_map, self.gen_manager)
        
        self.running = True
        self.last_time = time.time()
        
        print("Initializing map with enhanced travel system...")
        self.hex_map.initialize_map()

    def handle_transport_click(self, pos: Tuple[int, int]) -> bool:
        """Handle clicks on transport UI elements"""
        ts = self.hex_map.travel_system
        
        # Check quick transport buttons
        travel_buttons = self.renderer.ui_buttons.get("travel_ui", {})
        for button_name, rect in travel_buttons.items():
            if rect.collidepoint(pos):
                if button_name.startswith("transport_"):
                    transport_key = button_name.replace("transport_", "")
                    return self.change_transport(transport_key)
                elif button_name == "more_transport":
                    self.renderer.show_transport_menu = True
                    self.renderer.show_party_menu = False
                    return True
                elif button_name == "party":
                    self.renderer.show_party_menu = True
                    self.renderer.show_transport_menu = False
                    return True
        
        # Check transport menu buttons
        if self.renderer.show_transport_menu:
            transport_buttons = self.renderer.ui_buttons.get("transport_menu", {})
            for transport_key, rect in transport_buttons.items():
                if rect.collidepoint(pos):
                    if transport_key == "close":
                        self.renderer.show_transport_menu = False
                        return True
                    else:
                        return self.change_transport(transport_key)
        
        return False
    
    def handle_party_click(self, pos: Tuple[int, int]) -> bool:
        """Handle clicks in party menu"""
        if not self.renderer.show_party_menu:
            return False
        
        travel = self.hex_map.travel_system
        party_buttons = self.renderer.ui_buttons.get("party_menu", {})
        
        # Toggle traits
        for attr in ("ranger", "navigator", "outlander"):
            if attr in party_buttons and party_buttons[attr].collidepoint(pos):
                getattr(travel, f"toggle_{attr}")()
                self.renderer.set_message(
                    f"{attr.title()} " +
                    ("joined" if getattr(travel, f"has_{attr}") else "left")
                )
                return True
        
        # Select favored terrain
        if "terrain_buttons" in party_buttons:
            for terrain, rect in party_buttons["terrain_buttons"]:
                if rect.collidepoint(pos):
                    travel.set_favored_terrain(terrain)
                    self.renderer.set_message(f"Favored terrain: {terrain}")
                    return True
        
        # Close menu
        if "close" in party_buttons and party_buttons["close"].collidepoint(pos):
            self.renderer.show_party_menu = False
            return True
        
        return False
    
    def change_transport(self, transport_key: str) -> bool:
        """Change transportation mode with validation"""
        current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
        if current_hex:
            modifier = TRANSPORTATION_MODES[transport_key]["terrain_modifiers"][current_hex.terrain]
            if modifier < 999:
                self.hex_map.travel_system.change_transport(transport_key)
                self.renderer.set_message(f"Changed to {TRANSPORTATION_MODES[transport_key]['name']}")
                return True
            else:
                self.renderer.set_message(f"Cannot use {TRANSPORTATION_MODES[transport_key]['name']} here!")
                return True
        return False
    
    def check_resupply(self) -> bool:
        """Check if current hex is a town/settlement for resupply"""
        current_hex = self.hex_map.hexes.get(self.hex_map.current_position)
        if current_hex and "town" in current_hex.description.lower():
            return True
        # Starting position counts as town
        if self.hex_map.current_position == (0, 0, 0):
            return True
        return False
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.gen_manager.cancel()
            
            elif event.type == pygame.VIDEORESIZE:
                self.handle_resize(event)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not self.gen_manager.is_generating():
                    # Give menus first crack at the click
                    if self.handle_transport_click(event.pos):
                        continue
                    if self.handle_party_click(event.pos):
                        continue
                    
                    # Handle renderer clicks
                    action = self.renderer.handle_click(event.pos)
                    if action == "menu":
                        if self.confirm_return_to_menu():
                            self.return_to_menu()
                    elif action == "popup_explore":
                        success, msg = self.hex_map.explore_hex(*self.renderer.selected_hex)
                        if not success:
                            self.renderer.set_message(msg)
                        self.renderer.show_popup = False
                        self.renderer.selected_hex = None
                    elif action == "popup_navigate":
                        success, msg = self.hex_map.navigate_to_hex(*self.renderer.selected_hex)
                        if not success:
                            self.renderer.set_message(msg)
                        self.renderer.show_popup = False
                        self.renderer.selected_hex = None
                    elif action == "popup_close":
                        self.renderer.show_popup = False
                        self.renderer.selected_hex = None
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_m and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.return_to_menu()
                elif not self.gen_manager.is_generating():
                    if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if save_map_dialog(self.hex_map):
                            self.renderer.set_message("Map saved!")
                        else:
                            self.renderer.set_message("Save cancelled")
                    elif event.key == pygame.K_o and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if load_map_dialog(self.hex_map):
                            self.renderer.set_message("Map loaded!")
                        else:
                            self.renderer.set_message("Load cancelled")
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
                        # Toggle full transport menu
                        self.renderer.show_transport_menu = not self.renderer.show_transport_menu
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
                    if self.gen_manager.is_generating():
                        self.gen_manager.cancel()
                    elif self.renderer.show_transport_menu or self.renderer.show_party_menu or self.renderer.show_popup:
                        self.renderer.close_menus()
                    else:
                        if self.confirm_return_to_menu():
                            self.return_to_menu()
    
    def update(self, dt: float):
        """Update game state"""
        self.renderer.update(dt)
    
    def draw(self):
        """Draw everything"""
        self.renderer.draw_all()
        
        # Status bar with transport info
        transport_name = TRANSPORTATION_MODES[self.hex_map.travel_system.current_transport]["name"]
        if self.gen_manager.is_generating():
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
    
    def handle_resize(self, event):
        """Handle window resize event"""
        self.width = event.w
        self.height = event.h
        self.renderer.handle_resize(self.width, self.height)
    
    def confirm_return_to_menu(self) -> bool:
        """Show confirmation dialog for returning to menu"""
        result = quick_save_dialog(self.hex_map)
        
        if result == "save_and_return":
            return True
        elif result == "return_without_save":
            return True
        else:  # None or cancelled
            return False
    
    def return_to_menu(self):
        """Return to the main menu"""
        self.running = False
        self.ollama.cleanup()
        
        # Import and run main menu (if it exists)
        try:
            from main_menu import MainMenu
            menu = MainMenu()
            menu.run()
        except ImportError:
            print("Main menu not available - exiting to desktop")
    
    def run(self):
        """Main game loop"""
        while self.running:
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time
            
            self.handle_events()
            self.update(dt)
            self.draw()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # Cleanup
        self.gen_manager.cancel()
        self.ollama.cleanup()
        pygame.quit()


# For testing the complete modular system
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
    print("- T: Transportation menu")
    print("- Y: Party composition")
    print("-" * 50)
    
    explorer = HexMapExplorer()
    explorer.run()