"""
Main renderer for hex map explorer
"""
import pygame
import math
import time
from typing import Dict, List, Tuple, Optional
from config.constants import TERRAIN_TYPES, UI_COLORS, MIN_HEX_SIZE, MAX_HEX_SIZE, DEFAULT_HEX_SIZE_RATIO
from core.hex import HexCoordinates
from rendering.sprites import PixelArtSprites
from rendering.ui import (
    draw_travel_ui, draw_transport_menu, draw_party_menu, 
    draw_loading_animation, draw_message, draw_menu_button
)


class HexMapRenderer:
    """Renderer with travel UI and modular components"""
    
    def __init__(self, screen: pygame.Surface, hex_map, gen_manager):
        self.screen = screen
        self.hex_map = hex_map
        self.gen_manager = gen_manager
        self.coords = HexCoordinates()
        
        # Initialize responsive sizing
        screen_size = min(screen.get_width(), screen.get_height())
        self.hex_size = max(MIN_HEX_SIZE, min(MAX_HEX_SIZE, int(screen_size * DEFAULT_HEX_SIZE_RATIO)))
        
        self.font = pygame.font.Font(None, max(20, min(32, int(screen_size * 0.03))))
        self.small_font = pygame.font.Font(None, max(14, min(20, int(screen_size * 0.02))))
        
        # UI state
        self.selected_hex = None
        self.show_popup = False
        self.show_transport_menu = False
        self.show_party_menu = False
        self.message = ""
        self.message_timer = 0
        
        # Sprites and animations
        self.sprites = PixelArtSprites()
        
        # Button storage
        self.ui_buttons = {}
        
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
    
    def draw_hex(self, q: int, r: int, hex_obj):
        """Draw a single hexagon"""
        center_x, center_y = self.hex_to_pixel(q, r)
        
        # Cull hexes outside screen bounds
        if abs(center_x - self.screen.get_width() // 2) > self.screen.get_width() // 2 + self.hex_size:
            return
        if abs(center_y - self.screen.get_height() // 2) > self.screen.get_height() // 2 + self.hex_size:
            return
        
        points = [(center_x + ox, center_y + oy) for ox, oy in self.hex_vertex_offsets]
        
        # Determine hex color
        color = TERRAIN_TYPES[hex_obj.terrain]["color"]
        if not hex_obj.explored:
            color = tuple(c // 2 for c in color)  # Darken unexplored hexes
        
        if hex_obj.generating:
            pulse = (math.sin(time.time() * 3) + 1) / 2
            color = tuple(int(c * (0.5 + 0.5 * pulse)) for c in color)
        
        # Draw hex
        pygame.draw.polygon(self.screen, color, points)
        
        # Draw border
        if hex_obj.generating:
            border_color = (255, 255, 0)
        elif hex_obj.explored:
            border_color = (255, 255, 255)
        else:
            border_color = (100, 100, 100)
        
        pygame.draw.polygon(self.screen, border_color, points, 2)
        
        # Show movement cost for visible unexplored hexes
        if hex_obj.visible and not hex_obj.explored:
            cost = TERRAIN_TYPES[hex_obj.terrain]["movement_cost"]
            cost_text = self.small_font.render(str(int(cost)), True, (255, 255, 255))
            cost_rect = cost_text.get_rect(center=(int(center_x), int(center_y)))
            self.screen.blit(cost_text, cost_rect)
        
        # Draw adventurer sprite on current position
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
        terrain_text = self.font.render(f"{hex_obj.terrain.title()}", True, UI_COLORS["text_primary"])
        self.screen.blit(terrain_text, (popup_x + 10, popup_y + 10))
        
        cost_text = self.small_font.render(
            f"Movement cost: {TERRAIN_TYPES[hex_obj.terrain]['movement_cost']}", 
            True, (150, 200, 150)
        )
        self.screen.blit(cost_text, (popup_x + 10, popup_y + 35))
        
        coord_text = self.small_font.render(f"Location: ({hex_obj.q}, {hex_obj.r})", True, (150, 150, 150))
        self.screen.blit(coord_text, (popup_x + 10, popup_y + 55))
        
        # Description
        if hex_obj.generating:
            gen_text = self.font.render("Generating description...", True, UI_COLORS["text_warning"])
            gen_rect = gen_text.get_rect(center=(popup_x + popup_width // 2, popup_y + 120))
            self.screen.blit(gen_text, gen_rect)
        else:
            # Wrap text
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
            for line in lines[:4]:  # Show first 4 lines
                desc_text = self.small_font.render(line, True, UI_COLORS["text_secondary"])
                self.screen.blit(desc_text, (popup_x + 10, popup_y + y_offset))
                y_offset += 20
        
        # Buttons
        button_y = popup_y + 190
        self.ui_buttons["popup_buttons"] = {}
        
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
                explore_text = self.font.render("Explore", True, UI_COLORS["text_primary"])
                self.screen.blit(explore_text, (explore_rect.x + 20, explore_rect.y + 5))
                self.ui_buttons["popup_buttons"]["explore"] = explore_rect
                
                if not can_move:
                    no_mp_text = self.small_font.render(
                        f"Need {TERRAIN_TYPES[hex_obj.terrain]['movement_cost']} MP", 
                        True, (255, 100, 100)
                    )
                    self.screen.blit(no_mp_text, (popup_x + 50, button_y + 35))
            
            elif is_adjacent_explored:
                # Navigate button
                nav_color = (0, 100, 150) if can_move else (100, 100, 100)
                navigate_rect = pygame.Rect(popup_x + 50, button_y, 100, 30)
                pygame.draw.rect(self.screen, nav_color, navigate_rect)
                navigate_text = self.font.render("Navigate", True, UI_COLORS["text_primary"])
                self.screen.blit(navigate_text, (navigate_rect.x + 15, navigate_rect.y + 5))
                self.ui_buttons["popup_buttons"]["navigate"] = navigate_rect
            
            # Close button
            close_rect = pygame.Rect(popup_x + 250, button_y, 100, 30)
            pygame.draw.rect(self.screen, (150, 0, 0), close_rect)
            close_text = self.font.render("Close", True, UI_COLORS["text_primary"])
            self.screen.blit(close_text, (close_rect.x + 30, close_rect.y + 5))
            self.ui_buttons["popup_buttons"]["close"] = close_rect
    
    def handle_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Handle mouse clicks and return action"""
        if self.gen_manager.is_generating():
            return None
        
        # Check menu button
        if "menu" in self.ui_buttons and self.ui_buttons["menu"].collidepoint(pos):
            return "menu"
        
        # Check popup buttons
        if self.show_popup and "popup_buttons" in self.ui_buttons:
            for action, rect in self.ui_buttons["popup_buttons"].items():
                if rect.collidepoint(pos):
                    return f"popup_{action}"
        
        # Check transport/party buttons
        if "travel_ui" in self.ui_buttons:
            for button_name, rect in self.ui_buttons["travel_ui"].items():
                if rect.collidepoint(pos):
                    return button_name
        
        # Check transport menu buttons
        if self.show_transport_menu and "transport_menu" in self.ui_buttons:
            for transport, rect in self.ui_buttons["transport_menu"].items():
                if rect.collidepoint(pos):
                    return f"transport_menu_{transport}"
        
        # Check party menu buttons
        if self.show_party_menu and "party_menu" in self.ui_buttons:
            for button, rect in self.ui_buttons["party_menu"].items():
                if rect.collidepoint(pos):
                    return f"party_menu_{button}"
        
        # If clicking outside popups, close them
        if self.show_popup:
            popup_width = 400
            popup_height = 240
            popup_x = (self.screen.get_width() - popup_width) // 2
            popup_y = (self.screen.get_height() - popup_height) // 2
            popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
            
            if not popup_rect.collidepoint(pos):
                self.show_popup = False
                self.selected_hex = None
                return None
        
        # Select hex
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
    
    def handle_resize(self, width: int, height: int):
        """Handle screen resize"""
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        
        # Update responsive sizing
        screen_size = min(width, height)
        self.hex_size = max(MIN_HEX_SIZE, min(MAX_HEX_SIZE, int(screen_size * DEFAULT_HEX_SIZE_RATIO)))
        self.font = pygame.font.Font(None, max(20, min(32, int(screen_size * 0.03))))
        self.small_font = pygame.font.Font(None, max(14, min(20, int(screen_size * 0.02))))
        self.update_hex_vertices()
    
    def draw_all(self):
        """Draw complete UI"""
        # Clear screen
        self.screen.fill(UI_COLORS["background"])
        
        # Draw map
        self.draw_map()
        
        # Draw UI panels
        self.ui_buttons["travel_ui"] = draw_travel_ui(
            self.screen, self.hex_map.travel_system, self.hex_map, 
            self.selected_hex, self.font, self.small_font
        )
        
        # Draw menus
        if self.show_transport_menu:
            self.ui_buttons["transport_menu"] = draw_transport_menu(
                self.screen, self.hex_map.travel_system, self.hex_map,
                self.font, self.small_font
            )
        
        if self.show_party_menu:
            self.ui_buttons["party_menu"] = draw_party_menu(
                self.screen, self.hex_map.travel_system,
                self.font, self.small_font
            )
        
        # Draw popup
        self.draw_popup()
        
        # Draw loading animation
        draw_loading_animation(
            self.screen, self.gen_manager, self.sprites,
            self.font, self.small_font
        )
        
        # Draw message
        draw_message(self.screen, self.message, self.message_timer, self.font)
        
        # Draw menu button
        self.ui_buttons["menu"] = draw_menu_button(self.screen, self.font)
    
    def close_menus(self):
        """Close all open menus"""
        self.show_transport_menu = False
        self.show_party_menu = False
        self.show_popup = False
        self.selected_hex = None
