"""
UI drawing functions for hex map explorer
"""
import pygame
import time
from typing import Dict, List, Tuple, Any
from config.constants import TERRAIN_TYPES, TRANSPORTATION_MODES, UI_COLORS
from rendering.sprites import PixelArtSprites


def draw_travel_ui(screen: pygame.Surface, travel_system, hex_map, selected_hex, 
                  font: pygame.font.Font, small_font: pygame.font.Font) -> Dict[str, pygame.Rect]:
    """Draw enhanced travel system UI with transport options"""
    buttons = {}
    
    panel_width = 260
    panel_height = 200
    panel_rect = pygame.Rect(10, 50, panel_width, panel_height)
    pygame.draw.rect(screen, UI_COLORS["panel_bg"], panel_rect)
    pygame.draw.rect(screen, UI_COLORS["panel_border"], panel_rect, 1)
    
    title_text = small_font.render("Travel Status", True, UI_COLORS["text_primary"])
    screen.blit(title_text, (15, 55))
    
    transport = TRANSPORTATION_MODES[travel_system.current_transport]
    transport_text = small_font.render(f"Transport: {transport['name']}", True, (200, 200, 255))
    screen.blit(transport_text, (15, 75))
    
    hours = int(travel_system.hours_traveled)
    minutes = int((travel_system.hours_traveled - hours) * 60)
    time_text = small_font.render(f"Day {travel_system.days_traveled + 1}, Hour {hours}:{minutes:02d}", True, UI_COLORS["text_secondary"])
    screen.blit(time_text, (15, 95))
    
    cost_preview = ""
    if selected_hex and selected_hex in hex_map.hexes:
        hex_obj = hex_map.hexes[selected_hex]
        cost = travel_system.get_movement_cost(hex_obj.terrain)
        if cost >= 999:
            cost_preview = " (Impassable!)"
        else:
            cost_preview = f" (Next: {cost:.1f})"
    
    mp_color = UI_COLORS["text_success"] if travel_system.movement_points > 2 else UI_COLORS["text_warning"] if travel_system.movement_points > 0 else UI_COLORS["text_error"]
    mp_text = small_font.render(f"Movement: {travel_system.movement_points:.1f}/{travel_system.max_movement}{cost_preview}", True, mp_color)
    screen.blit(mp_text, (15, 115))
    
    pace_text = small_font.render(f"Pace: {travel_system.current_pace.title()}", True, UI_COLORS["text_secondary"])
    screen.blit(pace_text, (15, 135))
    
    supply_color = UI_COLORS["text_success"] if travel_system.supplies > 5 else UI_COLORS["text_warning"] if travel_system.supplies > 2 else UI_COLORS["text_error"]
    supply_text = small_font.render(f"Supplies: {travel_system.supplies:.1f} days", True, supply_color)
    screen.blit(supply_text, (15, 155))
    
    effective_exhaustion = travel_system.get_effective_exhaustion()
    if effective_exhaustion > 0:
        ex_label = "Mount Exhaustion" if transport["exhaustion_resistant"] else "Exhaustion"
        ex_color = (255, 100, 100)
        ex_text = small_font.render(f"{ex_label}: {effective_exhaustion}", True, ex_color)
        screen.blit(ex_text, (15, 175))
    
    bonuses_y = 195
    if travel_system.has_ranger:
        ranger_text = small_font.render("✓ Ranger (terrain bonus)", True, (100, 255, 100))
        screen.blit(ranger_text, (15, bonuses_y))
        bonuses_y += 18
    if travel_system.has_navigator:
        nav_text = small_font.render("✓ Navigator (+10% speed)", True, (100, 255, 100))
        screen.blit(nav_text, (15, bonuses_y))
        bonuses_y += 18
    if travel_system.has_outlander:
        outlander_text = small_font.render("✓ Outlander (never lost)", True, (100, 255, 100))
        screen.blit(outlander_text, (15, bonuses_y))
        bonuses_y += 18
    
    # Favored terrain active badge
    current_hex = hex_map.hexes.get(hex_map.current_position)
    if travel_system.has_ranger and current_hex and travel_system.favored_terrain == current_hex.terrain:
        bonus_surf = small_font.render("Favored terrain bonus!", True, (100, 255, 100))
        screen.blit(bonus_surf, (15, bonuses_y))
        bonuses_y += 18

    # Transport controls panel
    transport_panel_y = 260
    transport_panel_rect = pygame.Rect(10, transport_panel_y, panel_width, 140)
    pygame.draw.rect(screen, UI_COLORS["panel_bg"], transport_panel_rect)
    pygame.draw.rect(screen, UI_COLORS["panel_border"], transport_panel_rect, 1)
    
    transport_title = small_font.render("Transportation", True, UI_COLORS["text_primary"])
    screen.blit(transport_title, (15, transport_panel_y + 5))
    
    # Quick transport buttons
    quick_transports = ["on_foot", "horse", "boat", "airship"]
    button_width = 60
    button_height = 25
    for i, trans_key in enumerate(quick_transports):
        if trans_key not in TRANSPORTATION_MODES:
            continue
        trans = TRANSPORTATION_MODES[trans_key]
        x = 15 + (i % 4) * (button_width + 5)
        y = transport_panel_y + 30 + (i // 4) * 30
        
        is_current = travel_system.current_transport == trans_key
        button_color = UI_COLORS["button_selected"] if is_current else UI_COLORS["button_normal"]
        button_rect = pygame.Rect(x, y, button_width, button_height)
        
        can_use = True
        if hex_map.current_position in hex_map.hexes:
            current_hex = hex_map.hexes[hex_map.current_position]
            if trans["terrain_modifiers"][current_hex.terrain] >= 999:
                can_use = False
                button_color = (80, 40, 40)
        
        pygame.draw.rect(screen, button_color, button_rect)
        pygame.draw.rect(screen, (150, 150, 150), button_rect, 1)
        
        name = trans_key.replace("_", " ").title()[:7]
        name_text = small_font.render(name, True, UI_COLORS["text_primary"] if can_use else (150, 150, 150))
        text_rect = name_text.get_rect(center=button_rect.center)
        screen.blit(name_text, text_rect)
        
        buttons[f"transport_{trans_key}"] = button_rect
    
    more_button_rect = pygame.Rect(15, transport_panel_y + 60, 240, 25)
    pygame.draw.rect(screen, (70, 70, 100), more_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), more_button_rect, 1)
    more_text = small_font.render("More Transport Options (T)", True, UI_COLORS["text_primary"])
    more_text_rect = more_text.get_rect(center=more_button_rect.center)
    screen.blit(more_text, more_text_rect)
    buttons["more_transport"] = more_button_rect
    
    party_button_rect = pygame.Rect(15, transport_panel_y + 90, 240, 25)
    pygame.draw.rect(screen, (70, 100, 70), party_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), party_button_rect, 1)
    party_text = small_font.render("Party Composition (Y)", True, UI_COLORS["text_primary"])
    party_text_rect = party_text.get_rect(center=party_button_rect.center)
    screen.blit(party_text, party_text_rect)
    buttons["party"] = party_button_rect
    
    controls = [
        "R: Rest | P: Pace | F: Force",
        "T: Transport | Y: Party",
        "S: Resupply (in town)"
    ]
    y_pos = transport_panel_y + 120
    for control in controls:
        text = small_font.render(control, True, (150, 150, 150))
        screen.blit(text, (15, y_pos))
        y_pos += 18
    
    return buttons


def draw_transport_menu(screen: pygame.Surface, travel_system, hex_map, font: pygame.font.Font, 
                       small_font: pygame.font.Font) -> Dict[str, Any]:
    """Draw full transportation selection menu"""
    buttons = {}
    
    menu_width = 600
    menu_height = 500
    menu_x = (screen.get_width() - menu_width) // 2
    menu_y = (screen.get_height() - menu_height) // 2
    
    menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
    pygame.draw.rect(screen, (30, 30, 40), menu_rect)
    pygame.draw.rect(screen, (200, 200, 200), menu_rect, 3)
    
    title_text = font.render("Transportation Options", True, UI_COLORS["text_primary"])
    title_rect = title_text.get_rect(center=(menu_x + menu_width // 2, menu_y + 30))
    screen.blit(title_text, title_rect)
    
    current_hex = hex_map.hexes.get(hex_map.current_position)
    if current_hex:
        terrain_text = small_font.render(f"Current Terrain: {current_hex.terrain.title()}", True, UI_COLORS["text_secondary"])
        screen.blit(terrain_text, (menu_x + 20, menu_y + 60))
    
    col_width = 190
    row_height = 100
    cols = 3
    
    y_offset = menu_y + 90
    for i, (trans_key, trans_data) in enumerate(TRANSPORTATION_MODES.items()):
        col = i % cols
        row = i // cols
        
        x = menu_x + 10 + col * col_width
        y = y_offset + row * row_height
        
        can_use = True
        speed_text = ""
        if current_hex:
            modifier = trans_data["terrain_modifiers"][current_hex.terrain]
            if modifier >= 999:
                can_use = False
                speed_text = "Cannot use here!"
            else:
                base_speed = trans_data["base_hexes_per_8h"][travel_system.current_pace]
                effective_speed = base_speed / modifier
                speed_text = f"Speed: {effective_speed:.1f} hex/8h"
        
        box_rect = pygame.Rect(x, y, col_width - 10, row_height - 10)
        
        is_current = travel_system.current_transport == trans_key
        
        if is_current:
            box_color = (60, 60, 100)
            border_color = (255, 255, 100)
        elif not can_use:
            box_color = (60, 30, 30)
            border_color = (150, 50, 50)
        else:
            box_color = UI_COLORS["button_normal"]
            border_color = (100, 100, 150)
        
        pygame.draw.rect(screen, box_color, box_rect)
        pygame.draw.rect(screen, border_color, box_rect, 2)
        
        name_text = small_font.render(trans_data["name"], True, UI_COLORS["text_primary"])
        screen.blit(name_text, (x + 5, y + 5))
        
        speed_color = (150, 150, 150) if can_use else (200, 100, 100)
        speed_surface = small_font.render(speed_text, True, speed_color)
        screen.blit(speed_surface, (x + 5, y + 25))
        
        desc_words = trans_data["description"].split()
        desc_lines = []
        current_line = []
        for word in desc_words:
            test_line = ' '.join(current_line + [word])
            if small_font.size(test_line)[0] < col_width - 20:
                current_line.append(word)
            else:
                if current_line:
                    desc_lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            desc_lines.append(' '.join(current_line))
        
        for j, line in enumerate(desc_lines[:2]):
            line_surface = small_font.render(line, True, (180, 180, 180))
            screen.blit(line_surface, (x + 5, y + 45 + j * 15))
        
        buttons[trans_key] = box_rect
    
    close_button = pygame.Rect(menu_x + menu_width - 110, menu_y + menu_height - 40, 100, 30)
    pygame.draw.rect(screen, (150, 50, 50), close_button)
    pygame.draw.rect(screen, (200, 100, 100), close_button, 2)
    close_text = font.render("Close (ESC)", True, UI_COLORS["text_primary"])
    close_rect = close_text.get_rect(center=close_button.center)
    screen.blit(close_text, close_rect)
    buttons["close"] = close_button
    
    return buttons


def draw_party_menu(screen: pygame.Surface, travel_system, font: pygame.font.Font, 
                   small_font: pygame.font.Font) -> Dict[str, Any]:
    """Draw the party composition and bonuses menu"""
    buttons = {}
    
    menu_width, menu_height = 500, 400
    menu_x = (screen.get_width() - menu_width) // 2
    menu_y = (screen.get_height() - menu_height) // 2

    menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
    pygame.draw.rect(screen, (30, 30, 30), menu_rect)
    pygame.draw.rect(screen, (200, 200, 200), menu_rect, 3)

    # Title
    title = font.render("Party Composition", True, UI_COLORS["text_primary"])
    title_rect = title.get_rect(center=(menu_x + menu_width // 2, menu_y + 30))
    screen.blit(title, title_rect)

    # Toggles for Ranger, Navigator, Outlander
    opts = [
        ("ranger", "Ranger", "Reduces movement cost on favored terrain"),
        ("navigator", "Navigator", "Improves travel speed by 10%"),
        ("outlander", "Outlander", "Prevents getting lost in wilderness")
    ]
    
    y = menu_y + 70
    for attr, label, desc in opts:
        # Checkbox
        btn = pygame.Rect(menu_x + 20, y, 20, 20)
        pygame.draw.rect(screen, (50, 50, 50), btn)
        pygame.draw.rect(screen, (200, 200, 200), btn, 1)
        
        # Checkmark if enabled
        if getattr(travel_system, f"has_{attr}"):
            pygame.draw.line(screen, (100, 255, 100),
                             (btn.left + 4, btn.centery),
                             (btn.centerx, btn.bottom - 4), 2)
            pygame.draw.line(screen, (100, 255, 100),
                             (btn.centerx, btn.bottom - 4),
                             (btn.right - 4, btn.top + 4), 2)
        
        # Label
        txt = font.render(label, True, UI_COLORS["text_primary"])
        screen.blit(txt, (btn.right + 10, y - 2))
        
        # Description
        desc_txt = small_font.render(desc, True, (180, 180, 180))
        screen.blit(desc_txt, (menu_x + 20, y + 25))
        
        buttons[attr] = btn
        y += 60

    # Favored terrain row (only if Ranger is enabled)
    if travel_system.has_ranger:
        fav_label = font.render("Ranger's Favored Terrain:", True, (200, 200, 255))
        screen.blit(fav_label, (menu_x + 20, y))
        y += 30
        
        # Terrain selection buttons
        terrain_buttons = []
        terrains = ["forest", "plains", "mountains", "desert", "swamp", "hills"]
        cols = 3
        button_width = 120
        button_height = 30
        
        for i, terrain in enumerate(terrains):
            col = i % cols
            row = i // cols
            x = menu_x + 20 + col * (button_width + 10)
            terrain_y = y + row * (button_height + 10)
            
            tbtn = pygame.Rect(x, terrain_y, button_width, button_height)
            selected = (travel_system.favored_terrain == terrain)
            color = UI_COLORS["button_selected"] if selected else UI_COLORS["button_normal"]
            
            pygame.draw.rect(screen, color, tbtn)
            pygame.draw.rect(screen, (200, 200, 200), tbtn, 1)
            
            ttxt = small_font.render(terrain.title(), True, UI_COLORS["text_primary"])
            text_rect = ttxt.get_rect(center=tbtn.center)
            screen.blit(ttxt, text_rect)
            
            terrain_buttons.append((terrain, tbtn))
        
        buttons["terrain_buttons"] = terrain_buttons
        y += 80

    # Close button
    close_btn = pygame.Rect(menu_x + menu_width - 110, menu_y + menu_height - 40, 100, 30)
    pygame.draw.rect(screen, (150, 50, 50), close_btn)
    pygame.draw.rect(screen, (200, 100, 100), close_btn, 2)
    close_txt = font.render("Close (ESC)", True, UI_COLORS["text_primary"])
    close_rect = close_txt.get_rect(center=close_btn.center)
    screen.blit(close_txt, close_rect)
    buttons["close"] = close_btn
    
    return buttons


def draw_loading_animation(screen: pygame.Surface, gen_manager, sprites: PixelArtSprites, 
                          font: pygame.font.Font, small_font: pygame.font.Font):
    """Draw loading animation (scouting or resting)"""
    if not gen_manager.is_generating():
        return
    
    status = gen_manager.get_status()
    
    bar_width = 450
    bar_height = 120
    bar_x = (screen.get_width() - bar_width) // 2
    bar_y = screen.get_height() - 140
    
    bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
    pygame.draw.rect(screen, UI_COLORS["panel_bg"], bg_rect)
    pygame.draw.rect(screen, (200, 200, 200), bg_rect, 2)
    
    if status["type"] == "resting":
        title_text = font.render("Resting at camp...", True, UI_COLORS["text_primary"])
        title_rect = title_text.get_rect(center=(screen.get_width() // 2, bar_y + 20))
        screen.blit(title_text, title_rect)
        
        scene = sprites.get_campfire_scene(status["progress"], status["total"])
        scene_scaled = pygame.transform.scale2x(scene)
        scene_rect = scene_scaled.get_rect(center=(screen.get_width() // 2, bar_y + 65))
        screen.blit(scene_scaled, scene_rect)
    else:
        title_text = font.render("Scouting ahead...", True, UI_COLORS["text_primary"])
        title_rect = title_text.get_rect(center=(screen.get_width() // 2, bar_y + 20))
        screen.blit(title_text, title_rect)
        
        scene = sprites.get_scout_scene(status["progress"])
        scene_scaled = pygame.transform.scale2x(scene)
        scene_rect = scene_scaled.get_rect(center=(screen.get_width() // 2, bar_y + 65))
        screen.blit(scene_scaled, scene_rect)
    
    progress_text = f"{status['completed']}/{status['total']} areas discovered"
    text_surface = small_font.render(progress_text, True, (200, 200, 200))
    text_rect = text_surface.get_rect(center=(screen.get_width() // 2, bar_y + 105))
    screen.blit(text_surface, text_rect)


def draw_message(screen: pygame.Surface, message: str, message_timer: float, font: pygame.font.Font):
    """Draw temporary message"""
    if message and message_timer > 0:
        msg_surface = font.render(message, True, UI_COLORS["text_warning"])
        msg_rect = msg_surface.get_rect(center=(screen.get_width() // 2, 100))
        
        # Background
        padding = 10
        bg_rect = msg_rect.inflate(padding * 2, padding)
        pygame.draw.rect(screen, UI_COLORS["panel_bg"], bg_rect)
        pygame.draw.rect(screen, UI_COLORS["text_warning"], bg_rect, 2)
        
        screen.blit(msg_surface, msg_rect)


def draw_menu_button(screen: pygame.Surface, font: pygame.font.Font) -> pygame.Rect:
    """Draw menu button in bottom right corner"""
    menu_button_width = 100
    menu_button_height = 30
    menu_x = screen.get_width() - menu_button_width - 10
    menu_y = screen.get_height() - menu_button_height - 10
    
    menu_button_rect = pygame.Rect(menu_x, menu_y, menu_button_width, menu_button_height)
    
    mouse_pos = pygame.mouse.get_pos()
    if menu_button_rect.collidepoint(mouse_pos):
        button_color = UI_COLORS["button_hover"]
        text_color = UI_COLORS["text_primary"]
    else:
        button_color = UI_COLORS["button_normal"]
        text_color = UI_COLORS["text_secondary"]
    
    pygame.draw.rect(screen, button_color, menu_button_rect)
    pygame.draw.rect(screen, (150, 150, 150), menu_button_rect, 2)
    
    menu_text = font.render("MENU", True, text_color)
    menu_text_rect = menu_text.get_rect(center=(menu_x + menu_button_width // 2, menu_y + menu_button_height // 2))
    screen.blit(menu_text, menu_text_rect)
    
    return menu_button_rect