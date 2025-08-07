"""
Map Preview Window - Navigate generated maps before importing
"""
import pygame
import json
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Tuple, Optional
import sys


class HexMapPreview:
    """Preview window for generated maps with navigation"""
    
    def __init__(self, width=1000, height=700):
        pygame.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Hex Map Preview - Drag to pan, scroll to zoom")
        self.clock = pygame.time.Clock()
        
        # Map data
        self.hexes = {}
        self.map_data = None
        
        # View state
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.min_zoom = 0.2  # Increased minimum zoom to keep hexes visible
        self.max_zoom = 3.0
        
        # Interaction state
        self.dragging = False
        self.last_mouse_pos = (0, 0)
        
        # Rendering
        self.hex_size = 20
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 16)
        
        # Terrain colors (matching game colors)
        self.terrain_colors = {
            "water": (65, 105, 225),
            "plains": (144, 238, 144), 
            "forest": (34, 139, 34),
            "mountains": (139, 137, 137),
            "hills": (160, 82, 45),
            "desert": (238, 203, 173),
            "swamp": (47, 79, 79),
            "tundra": (176, 224, 230),
            # Add fallback for unknown terrains
            "unknown": (100, 100, 100)
        }
        
        self.running = True
        
    def load_map(self, map_data):
        """Load map data for preview"""
        self.map_data = map_data
        self.hexes = {}
        
        # Convert hex list to dict for easy lookup
        for hex_data in map_data.get("hexes", []):
            q, r, s = hex_data["q"], hex_data["r"], hex_data["s"]
            self.hexes[(q, r, s)] = hex_data
        
        print(f"Loaded {len(self.hexes)} hexes for preview")
        
        # Reset view to center
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        
    def hex_to_screen(self, q, r) -> Tuple[float, float]:
        """Convert hex coordinates to screen coordinates"""
        # Standard hex-to-pixel conversion
        x = self.hex_size * (3/2 * q) * self.zoom
        y = self.hex_size * (math.sqrt(3)/2 * q + math.sqrt(3) * r) * self.zoom
        
        # Apply camera offset and center on screen
        screen_x = x - self.camera_x + self.width / 2
        screen_y = y - self.camera_y + self.height / 2
        
        return screen_x, screen_y
        
    def screen_to_hex(self, screen_x, screen_y) -> Tuple[int, int, int]:
        """Convert screen coordinates to hex coordinates"""
        # Reverse the hex_to_screen calculation
        x = (screen_x - self.width / 2 + self.camera_x) / self.zoom
        y = (screen_y - self.height / 2 + self.camera_y) / self.zoom
        
        # Convert to hex coordinates
        if self.hex_size * self.zoom < 1:  # Avoid division by zero
            return 0, 0, 0
            
        q = (2/3 * x) / self.hex_size
        r = (-1/3 * x + math.sqrt(3)/3 * y) / self.hex_size
        s = -q - r
        
        # Round to nearest integers
        rq, rr, rs = round(q), round(r), round(s)
        
        # Handle rounding errors
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - s)
        
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        else:
            rs = -rq - rr
            
        return rq, rr, rs
    
    def draw_hex(self, q, r, hex_data):
        """Draw a single hexagon"""
        screen_x, screen_y = self.hex_to_screen(q, r)
        
        # Skip if outside screen bounds (with margin)
        margin = self.hex_size * self.zoom + 50
        if (screen_x < -margin or screen_x > self.width + margin or
            screen_y < -margin or screen_y > self.height + margin):
            return
            
        # Get terrain color
        terrain = hex_data.get("terrain", "plains")
        color = self.terrain_colors.get(terrain, self.terrain_colors["unknown"])
        
        # Calculate hex vertices
        vertices = []
        # Ensure minimum visible size even when zoomed out
        effective_size = max(2, self.hex_size * self.zoom)
        
        for i in range(6):
            angle = math.pi / 3 * i
            vertex_x = screen_x + effective_size * math.cos(angle)
            vertex_y = screen_y + effective_size * math.sin(angle)
            vertices.append((vertex_x, vertex_y))
        
        # Draw the hex
        if len(vertices) >= 3:
            try:
                pygame.draw.polygon(self.screen, color, vertices)
                # Draw border with minimum thickness of 1
                border_thickness = max(1, int(self.zoom))
                pygame.draw.polygon(self.screen, (0, 0, 0), vertices, border_thickness)
            except (ValueError, TypeError) as e:
                # Skip invalid polygons
                pass
    
    def draw_map(self):
        """Draw all visible hexes"""
        # Get screen bounds in world coordinates
        margin = self.hex_size * self.zoom * 2  # Extra margin for safety
        
        # Calculate visible bounds more accurately
        screen_bounds = [
            (0, 0), (self.width, 0),
            (0, self.height), (self.width, self.height),
            (self.width//2, 0), (self.width//2, self.height),
            (0, self.height//2), (self.width, self.height//2)
        ]
        
        # Get hex coordinates for all screen corners and edges
        hex_bounds = [self.screen_to_hex(x, y) for x, y in screen_bounds]
        
        # Find the actual range of hexes that might be visible
        if hex_bounds:
            qs = [h[0] for h in hex_bounds]
            rs = [h[1] for h in hex_bounds]
            
            min_q = min(qs) - 3
            max_q = max(qs) + 3  
            min_r = min(rs) - 3
            max_r = max(rs) + 3
        else:
            # Fallback if bounds calculation fails
            min_q, max_q = -10, 10
            min_r, max_r = -10, 10
        
        # Draw hexes in the visible area
        drawn_count = 0
        total_in_bounds = 0
        for (q, r, s), hex_data in self.hexes.items():
            if min_q <= q <= max_q and min_r <= r <= max_r:
                total_in_bounds += 1
                # Additional screen bounds check
                screen_x, screen_y = self.hex_to_screen(q, r)
                if (-margin <= screen_x <= self.width + margin and 
                    -margin <= screen_y <= self.height + margin):
                    self.draw_hex(q, r, hex_data)
                    drawn_count += 1
        
        # Optional debug info (uncomment if needed)
        # if hasattr(self, 'debug_counter'):
        #     self.debug_counter += 1
        # else:
        #     self.debug_counter = 0
        # if self.debug_counter % 60 == 0:
        #     print(f"Drawn: {drawn_count}/{len(self.hexes)} hexes")
    
    def draw_ui(self):
        """Draw UI elements"""
        # Map info
        if self.map_data:
            info_lines = [
                f"Seed: {self.map_data.get('seed', 'Unknown')}",
                f"Size: {self.map_data.get('width', '?')}x{self.map_data.get('height', '?')}",
                f"Hexes: {len(self.hexes)}",
                f"Zoom: {self.zoom:.1f}x"
            ]
            
            for i, line in enumerate(info_lines):
                text = self.small_font.render(line, True, (255, 255, 255))
                self.screen.blit(text, (10, 10 + i * 20))
        
        # Instructions
        instructions = [
            "Drag: Pan around the map",
            "Scroll: Zoom in/out",
            "ESC: Close preview"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, (200, 200, 200))
            self.screen.blit(text, (10, self.height - 60 + i * 20))
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.dragging = True
                    self.last_mouse_pos = event.pos
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    
                    # Update camera position
                    self.camera_x -= dx
                    self.camera_y -= dy
                    
                    self.last_mouse_pos = event.pos
                    
            elif event.type == pygame.MOUSEWHEEL:
                # Zoom with mouse wheel
                mouse_x, mouse_y = pygame.mouse.get_pos()
                
                # Get world position before zoom
                old_world_x = (mouse_x - self.width/2 + self.camera_x) / self.zoom
                old_world_y = (mouse_y - self.height/2 + self.camera_y) / self.zoom
                
                # Apply zoom
                zoom_factor = 1.1 if event.y > 0 else 0.9
                self.zoom *= zoom_factor
                self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom))
                
                # Adjust camera to keep mouse position stable
                new_world_x = (mouse_x - self.width/2 + self.camera_x) / self.zoom
                new_world_y = (mouse_y - self.height/2 + self.camera_y) / self.zoom
                
                self.camera_x += (new_world_x - old_world_x) * self.zoom
                self.camera_y += (new_world_y - old_world_y) * self.zoom
                
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.size
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
    
    def run(self):
        """Main preview loop"""
        while self.running:
            self.handle_events()
            
            # Clear screen
            self.screen.fill((30, 30, 40))  # Dark blue background
            
            # Draw map
            self.draw_map()
            
            # Draw UI
            self.draw_ui()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()


def preview_map_file():
    """Standalone function to preview a map file"""
    try:
        # Create a hidden tkinter root for file dialog
        root = tk.Tk()
        root.withdraw()
        
        # Ask user to select a map file
        filename = filedialog.askopenfilename(
            title="Select Map to Preview",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            root.destroy()
            return
        
        # Load map data
        try:
            with open(filename, 'r') as f:
                map_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load map file: {e}")
            root.destroy()
            return
        
        root.destroy()
        
        # Validate map data
        if "hexes" not in map_data:
            print("Error: Invalid map file - no hexes found")
            return
        
        # Create and run preview
        preview = HexMapPreview()
        preview.load_map(map_data)
        preview.run()
        
    except Exception as e:
        print(f"Preview error: {e}")
        try:
            messagebox.showerror("Error", f"Preview failed: {e}")
        except:
            pass


if __name__ == "__main__":
    preview_map_file()