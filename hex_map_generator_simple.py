"""
Simple Hex Map Generator - Crash-proof version
No complex GUI, just basic tkinter with bulletproof error handling
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import random
import json
import sys
import os
import math

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generation.minecraft_biomes import MinecraftBiomeGenerator
    from config.constants import TERRAIN_TYPES
    BIOME_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Biome system not available: {e}")
    BIOME_SYSTEM_AVAILABLE = False


class SimpleHexGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hex Map Generator with Visual Preview")
        self.root.geometry("1000x700")
        
        # Simple variables
        self.seed = random.randint(1, 1000000)
        self.width = 20
        self.height = 20
        self.hex_data = {}
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create simple, stable widgets"""
        # Title
        title = tk.Label(self.root, text="Hex Map Generator with Visual Preview", font=("Arial", 16, "bold"))
        title.pack(pady=5)
        
        # Settings frame
        settings = tk.Frame(self.root)
        settings.pack(pady=5)
        
        # Seed
        tk.Label(settings, text="Seed:").grid(row=0, column=0, padx=5)
        self.seed_var = tk.StringVar(value=str(self.seed))
        tk.Entry(settings, textvariable=self.seed_var, width=12).grid(row=0, column=1, padx=5)
        tk.Button(settings, text="Random", command=self.random_seed).grid(row=0, column=2, padx=5)
        
        # Width
        tk.Label(settings, text="Width:").grid(row=0, column=3, padx=(20,5))
        self.width_var = tk.StringVar(value=str(self.width))
        tk.Entry(settings, textvariable=self.width_var, width=8).grid(row=0, column=4, padx=5)
        
        # Height  
        tk.Label(settings, text="Height:").grid(row=0, column=5, padx=5)
        self.height_var = tk.StringVar(value=str(self.height))
        tk.Entry(settings, textvariable=self.height_var, width=8).grid(row=0, column=6, padx=5)
        
        # Generate button
        tk.Button(settings, text="Generate Map", command=self.generate_map, 
                 bg="lightgreen", font=("Arial", 10, "bold")).grid(row=0, column=7, padx=20)
        
        # Status
        self.status = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status, fg="blue").pack()
        
        # Main content frame - split into left info and right visual
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - Info panel
        left_frame = tk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        tk.Label(left_frame, text="Map Information", font=("Arial", 12, "bold")).pack()
        
        self.text = tk.Text(left_frame, height=20, width=35, wrap=tk.WORD)
        text_scroll = tk.Scrollbar(left_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=text_scroll.set)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right side - Visual map preview
        right_frame = tk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="Visual Map Preview", font=("Arial", 12, "bold")).pack()
        
        # Canvas for hex map visualization
        canvas_frame = tk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white', width=500, height=400)
        canvas_scroll_v = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        canvas_scroll_h = tk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=canvas_scroll_v.set, xscrollcommand=canvas_scroll_h.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_scroll_v.pack(side=tk.RIGHT, fill=tk.Y)
        canvas_scroll_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Mouse interaction
        self.canvas.bind("<Motion>", self.on_canvas_hover)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Mouse navigation
        self.canvas.bind("<Button-2>", self.start_pan)  # Middle mouse button
        self.canvas.bind("<B2-Motion>", self.on_pan)    # Middle mouse drag
        self.canvas.bind("<ButtonRelease-2>", self.end_pan)
        
        # Alternative: Right-click drag for panning
        self.canvas.bind("<Button-3>", self.start_pan)  # Right mouse button
        self.canvas.bind("<B3-Motion>", self.on_pan)    # Right mouse drag
        self.canvas.bind("<ButtonRelease-3>", self.end_pan)
        
        # Mouse wheel zooming
        self.canvas.bind("<MouseWheel>", self.on_zoom)  # Windows
        self.canvas.bind("<Button-4>", self.on_zoom)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_zoom)    # Linux scroll down
        
        # Keyboard navigation
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.focus_set()  # Make canvas focusable
        
        # Pan state variables
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        self.zoom_level = 1.0
        
        # Tooltip label
        self.tooltip = tk.Label(right_frame, text="", bg="lightyellow", relief="solid", borderwidth=1)
        self.tooltip.pack_forget()
        
        # Navigation controls
        nav_frame = tk.Frame(right_frame)
        nav_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(nav_frame, text="Navigation:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        tk.Button(nav_frame, text="Zoom In (+)", command=self.zoom_in_center, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Zoom Out (-)", command=self.zoom_out_center, width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Reset View (R)", command=self.reset_view, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Fit Map", command=self.fit_map_to_view, width=8).pack(side=tk.LEFT, padx=2)
        
        # Navigation help
        nav_help = tk.Label(right_frame, text="🖱️ Left: Select | Right/Middle: Pan | Wheel: Zoom | WASD: Navigate", 
                           font=('Arial', 8), fg='gray')
        nav_help.pack(pady=(0,2))
        
        # Buttons frame at bottom
        buttons = tk.Frame(self.root)
        buttons.pack(pady=5)
        
        tk.Button(buttons, text="Save JSON", command=self.save_json).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons, text="Copy to Game", command=self.copy_to_game).pack(side=tk.LEFT, padx=5)
    
    def random_seed(self):
        """Generate random seed"""
        self.seed = random.randint(1, 1000000)
        self.seed_var.set(str(self.seed))
    
    def generate_map(self):
        """Generate hex map safely"""
        try:
            # Get values
            self.seed = int(self.seed_var.get())
            self.width = max(5, min(100, int(self.width_var.get())))
            self.height = max(5, min(100, int(self.height_var.get())))
            
            self.status.set("Generating...")
            self.root.update()
            
            # Clear previous results
            self.text.delete(1.0, tk.END)
            self.hex_data = {}
            
            if BIOME_SYSTEM_AVAILABLE:
                # Use Minecraft biome system
                generator = MinecraftBiomeGenerator(self.seed)
                biome_counts = {}
                
                for col in range(self.width):
                    for row in range(self.height):
                        # Convert to cube coordinates
                        q = col - (row - (row & 1)) // 2
                        r = row
                        s = -q - r
                        
                        # Generate terrain
                        terrain = generator.select_biome(q, r, s)
                        
                        # Store data
                        self.hex_data[(col, row)] = {
                            'q': q, 'r': r, 's': s,
                            'terrain': terrain
                        }
                        
                        biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
            else:
                # Fallback to simple generation
                terrains = ["water", "forest", "plains", "mountains", "desert", "hills"]
                biome_counts = {}
                
                for col in range(self.width):
                    for row in range(self.height):
                        q = col - (row - (row & 1)) // 2
                        r = row
                        s = -q - r
                        
                        terrain = random.choice(terrains)
                        
                        self.hex_data[(col, row)] = {
                            'q': q, 'r': r, 's': s,
                            'terrain': terrain
                        }
                        
                        biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
            
            # Display results
            self.display_results(biome_counts)
            self.draw_visual_map()
            self.status.set(f"Generated {len(self.hex_data)} hexes successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Generation failed: {e}")
            self.status.set("Error occurred")
    
    def display_results(self, biome_counts):
        """Display generation results"""
        result = f"=== HEX MAP GENERATED ===\\n"
        result += f"Dimensions: {self.width} x {self.height}\\n"
        result += f"Total Hexes: {len(self.hex_data)}\\n"
        result += f"Seed: {self.seed}\\n\\n"
        
        result += "TERRAIN DISTRIBUTION:\\n"
        result += "-" * 30 + "\\n"
        
        total = len(self.hex_data)
        for terrain, count in sorted(biome_counts.items()):
            percent = (count / total) * 100
            result += f"{terrain.title()}: {count} ({percent:.1f}%)\\n"
        
        # ASCII preview (small maps only)
        if self.width <= 30 and self.height <= 20:
            result += "\\n" + "ASCII PREVIEW:\\n"
            result += "-" * 30 + "\\n"
            
            symbols = {'water': '~', 'forest': 'T', 'plains': '.', 
                      'mountains': '^', 'desert': 'S', 'hills': 'h',
                      'swamp': 'M', 'tundra': 'I'}
            
            for row in range(self.height):
                line = " " if row % 2 == 1 else ""
                for col in range(self.width):
                    if (col, row) in self.hex_data:
                        terrain = self.hex_data[(col, row)]['terrain']
                        symbol = symbols.get(terrain, '?')
                        line += symbol + " "
                    else:
                        line += "? "
                result += line + "\\n"
        
        self.text.insert(tk.END, result)
    
    def draw_visual_map(self):
        """Draw visual hex map on canvas"""
        if not self.hex_data:
            return
        
        try:
            # Clear canvas
            self.canvas.delete("all")
            
            # Calculate hex size based on map dimensions
            canvas_width = 500
            canvas_height = 400
            
            # Determine hex size to fit the map
            hex_size = min(20, max(5, min(canvas_width // (self.width * 2), canvas_height // (self.height * 2))))
            
            # Get terrain colors (fallback if TERRAIN_TYPES not available)
            if BIOME_SYSTEM_AVAILABLE:
                terrain_colors = {terrain: f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" 
                                for terrain, data in TERRAIN_TYPES.items() 
                                for color in [data["color"]]}
            else:
                terrain_colors = {
                    'water': '#4169e1', 'forest': '#228b22', 'plains': '#90ee90',
                    'mountains': '#8b8970', 'desert': '#f4c2a0', 'hills': '#a0522d',
                    'swamp': '#2f4f4f', 'tundra': '#b0e0e6'
                }
            
            # Calculate map bounds
            hex_width = hex_size * 1.75
            hex_height = hex_size * 1.5
            
            total_width = self.width * hex_width + hex_size
            total_height = self.height * hex_height + hex_size
            
            # Set canvas scroll region
            self.canvas.configure(scrollregion=(0, 0, total_width, total_height))
            
            # Draw legend first
            self.draw_legend(terrain_colors)
            
            # Draw hexes
            for (col, row), hex_info in self.hex_data.items():
                # Calculate hex center position
                x = col * hex_width + hex_size * 1.5
                y = row * hex_height + hex_size + (col % 2) * hex_height * 0.5
                
                # Get terrain color
                terrain = hex_info['terrain']
                color = terrain_colors.get(terrain, '#cccccc')
                
                # Draw hex
                self.draw_hex(x, y, hex_size, color, terrain)
                
        except Exception as e:
            print(f"Error drawing visual map: {e}")
    
    def draw_hex(self, x, y, size, color, terrain):
        """Draw a single hexagon"""
        try:
            # Calculate hex vertices
            points = []
            for i in range(6):
                angle = math.pi / 3 * i
                px = x + size * math.cos(angle)
                py = y + size * math.sin(angle)
                points.extend([px, py])
            
            # Draw filled hex
            self.canvas.create_polygon(points, fill=color, outline='black', width=1)
            
            # Add terrain label for larger hexes
            if size >= 12:
                # Use terrain symbol
                symbols = {
                    'water': '~', 'forest': 'T', 'plains': '.', 'mountains': '^',
                    'desert': 'S', 'hills': 'h', 'swamp': 'M', 'tundra': 'I'
                }
                symbol = symbols.get(terrain, '?')
                self.canvas.create_text(x, y, text=symbol, font=('Arial', str(max(8, size//2)), 'bold'))
                
        except Exception as e:
            print(f"Error drawing hex: {e}")
    
    def draw_legend(self, terrain_colors):
        """Draw terrain legend"""
        try:
            legend_x = 10
            legend_y = 10
            
            self.canvas.create_text(legend_x, legend_y, text="Terrain Legend:", 
                                  anchor='nw', font=('Arial', 10, 'bold'))
            
            y_offset = 25
            for terrain, color in terrain_colors.items():
                if terrain in [hex_info['terrain'] for hex_info in self.hex_data.values()]:
                    # Draw color square
                    self.canvas.create_rectangle(legend_x, legend_y + y_offset, 
                                               legend_x + 15, legend_y + y_offset + 15,
                                               fill=color, outline='black')
                    
                    # Draw terrain name
                    self.canvas.create_text(legend_x + 20, legend_y + y_offset + 7, 
                                          text=terrain.title(), anchor='w', font=('Arial', 9))
                    
                    y_offset += 18
                    
        except Exception as e:
            print(f"Error drawing legend: {e}")
    
    def on_canvas_hover(self, event):
        """Handle mouse hover over canvas"""
        try:
            # Get canvas coordinates
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Find hex under cursor
            hex_info = self.find_hex_at_position(canvas_x, canvas_y)
            
            if hex_info:
                col, row = hex_info
                hex_data = self.hex_data.get((col, row))
                if hex_data:
                    tooltip_text = f"Hex ({col},{row})\\nTerrain: {hex_data['terrain'].title()}\\nCoords: q={hex_data['q']}, r={hex_data['r']}, s={hex_data['s']}"
                    self.tooltip.config(text=tooltip_text)
                    self.tooltip.place(x=event.x + 10, y=event.y + 10)
                    return
            
            # Hide tooltip if no hex found
            self.tooltip.place_forget()
            
        except Exception as e:
            pass  # Ignore hover errors
    
    def on_canvas_click(self, event):
        """Handle canvas click"""
        try:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            hex_info = self.find_hex_at_position(canvas_x, canvas_y)
            if hex_info:
                col, row = hex_info
                hex_data = self.hex_data.get((col, row))
                if hex_data:
                    messagebox.showinfo("Hex Details", 
                        f"Hex Details\\n\\n"
                        f"Grid Position: ({col}, {row})\\n"
                        f"Cube Coordinates: q={hex_data['q']}, r={hex_data['r']}, s={hex_data['s']}\\n"
                        f"Terrain: {hex_data['terrain'].title()}\\n")
        except Exception as e:
            pass  # Ignore click errors
    
    def find_hex_at_position(self, x, y):
        """Find which hex contains the given canvas position"""
        if not self.hex_data:
            return None
        
        try:
            # Calculate which hex grid position this might be
            hex_size = min(20, max(5, min(500 // (self.width * 2), 400 // (self.height * 2))))
            hex_width = hex_size * 1.75
            hex_height = hex_size * 1.5
            
            # Rough estimate of grid position
            rough_col = max(0, min(self.width - 1, int((x - hex_size * 1.5) / hex_width)))
            rough_row = max(0, min(self.height - 1, int((y - hex_size) / hex_height)))
            
            # Check nearby hexes for exact match
            for check_col in range(max(0, rough_col - 1), min(self.width, rough_col + 2)):
                for check_row in range(max(0, rough_row - 1), min(self.height, check_row + 2)):
                    if (check_col, check_row) in self.hex_data:
                        # Calculate hex center
                        hex_x = check_col * hex_width + hex_size * 1.5
                        hex_y = check_row * hex_height + hex_size + (check_col % 2) * hex_height * 0.5
                        
                        # Check if point is within hex
                        distance = math.sqrt((x - hex_x)**2 + (y - hex_y)**2)
                        if distance <= hex_size:
                            return (check_col, check_row)
            
            return None
            
        except Exception as e:
            return None
    
    def start_pan(self, event):
        """Start panning operation"""
        self.canvas.config(cursor="fleur")  # Change cursor to indicate panning
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.is_panning = True
    
    def on_pan(self, event):
        """Handle panning motion"""
        if self.is_panning:
            # Calculate how much to move
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            # Move the canvas view
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")
            
            # Update start position for next movement
            self.pan_start_x = event.x
            self.pan_start_y = event.y
    
    def end_pan(self, event):
        """End panning operation"""
        self.canvas.config(cursor="")  # Reset cursor
        self.is_panning = False
    
    def on_zoom(self, event):
        """Handle mouse wheel zooming"""
        try:
            # Determine zoom direction
            if event.delta > 0 or event.num == 4:  # Zoom in
                zoom_factor = 1.1
            else:  # Zoom out
                zoom_factor = 0.9
            
            # Update zoom level
            new_zoom = self.zoom_level * zoom_factor
            
            # Limit zoom range
            if 0.1 <= new_zoom <= 5.0:
                self.zoom_level = new_zoom
                
                # Get mouse position on canvas
                canvas_x = self.canvas.canvasx(event.x)
                canvas_y = self.canvas.canvasy(event.y)
                
                # Scale the canvas
                self.canvas.scale("all", canvas_x, canvas_y, zoom_factor, zoom_factor)
                
                # Update scroll region
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
        except AttributeError:
            # Handle different event types
            if hasattr(event, 'num'):
                if event.num == 4:  # Scroll up
                    zoom_factor = 1.1
                elif event.num == 5:  # Scroll down
                    zoom_factor = 0.9
                else:
                    return
                
                new_zoom = self.zoom_level * zoom_factor
                if 0.1 <= new_zoom <= 5.0:
                    self.zoom_level = new_zoom
                    canvas_x = self.canvas.canvasx(event.x)
                    canvas_y = self.canvas.canvasy(event.y)
                    self.canvas.scale("all", canvas_x, canvas_y, zoom_factor, zoom_factor)
                    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            pass  # Ignore zoom errors
    
    def on_key_press(self, event):
        """Handle keyboard navigation"""
        try:
            move_distance = 20
            
            # WASD or arrow key navigation
            if event.keysym in ['w', 'W', 'Up']:
                self.canvas.yview_scroll(-1, "units")
            elif event.keysym in ['s', 'S', 'Down']:
                self.canvas.yview_scroll(1, "units")
            elif event.keysym in ['a', 'A', 'Left']:
                self.canvas.xview_scroll(-1, "units")
            elif event.keysym in ['d', 'D', 'Right']:
                self.canvas.xview_scroll(1, "units")
            
            # Zoom with +/- keys
            elif event.keysym in ['plus', 'equal']:
                # Zoom in at center
                center_x = self.canvas.winfo_width() // 2
                center_y = self.canvas.winfo_height() // 2
                canvas_x = self.canvas.canvasx(center_x)
                canvas_y = self.canvas.canvasy(center_y)
                
                new_zoom = self.zoom_level * 1.2
                if new_zoom <= 5.0:
                    self.zoom_level = new_zoom
                    self.canvas.scale("all", canvas_x, canvas_y, 1.2, 1.2)
                    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                    
            elif event.keysym in ['minus', 'underscore']:
                # Zoom out at center
                center_x = self.canvas.winfo_width() // 2
                center_y = self.canvas.winfo_height() // 2
                canvas_x = self.canvas.canvasx(center_x)
                canvas_y = self.canvas.canvasy(center_y)
                
                new_zoom = self.zoom_level * 0.8
                if new_zoom >= 0.1:
                    self.zoom_level = new_zoom
                    self.canvas.scale("all", canvas_x, canvas_y, 0.8, 0.8)
                    self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Reset zoom with 'r' or '0'
            elif event.keysym in ['r', 'R', '0']:
                self.reset_view()
                
        except Exception as e:
            pass  # Ignore keyboard errors
    
    def reset_view(self):
        """Reset canvas view to original state"""
        try:
            # Clear and redraw map
            if self.hex_data:
                self.zoom_level = 1.0
                self.draw_visual_map()
                
                # Center the view
                self.canvas.xview_moveto(0.0)
                self.canvas.yview_moveto(0.0)
                
        except Exception as e:
            pass
    
    def zoom_in_center(self):
        """Zoom in at center of view"""
        try:
            center_x = self.canvas.winfo_width() // 2
            center_y = self.canvas.winfo_height() // 2
            canvas_x = self.canvas.canvasx(center_x)
            canvas_y = self.canvas.canvasy(center_y)
            
            new_zoom = self.zoom_level * 1.2
            if new_zoom <= 5.0:
                self.zoom_level = new_zoom
                self.canvas.scale("all", canvas_x, canvas_y, 1.2, 1.2)
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
        except Exception as e:
            pass
    
    def zoom_out_center(self):
        """Zoom out at center of view"""
        try:
            center_x = self.canvas.winfo_width() // 2
            center_y = self.canvas.winfo_height() // 2
            canvas_x = self.canvas.canvasx(center_x)
            canvas_y = self.canvas.canvasy(center_y)
            
            new_zoom = self.zoom_level * 0.8
            if new_zoom >= 0.1:
                self.zoom_level = new_zoom
                self.canvas.scale("all", canvas_x, canvas_y, 0.8, 0.8)
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
                
        except Exception as e:
            pass
    
    def fit_map_to_view(self):
        """Fit entire map to the current view"""
        try:
            if not self.hex_data:
                return
            
            # Get current canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return
            
            # Get map bounds
            map_bbox = self.canvas.bbox("all")
            if not map_bbox:
                return
            
            map_width = map_bbox[2] - map_bbox[0]
            map_height = map_bbox[3] - map_bbox[1]
            
            # Calculate zoom to fit
            zoom_x = (canvas_width * 0.9) / map_width  # 90% to leave margin
            zoom_y = (canvas_height * 0.9) / map_height
            target_zoom = min(zoom_x, zoom_y)
            
            # Apply zoom relative to current
            zoom_factor = target_zoom / self.zoom_level
            
            # Zoom from center
            center_x = (map_bbox[0] + map_bbox[2]) / 2
            center_y = (map_bbox[1] + map_bbox[3]) / 2
            
            self.zoom_level = target_zoom
            self.canvas.scale("all", center_x, center_y, zoom_factor, zoom_factor)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Center the view on the map
            self.canvas.xview_moveto(0.1)  # Small offset from edge
            self.canvas.yview_moveto(0.1)
            
        except Exception as e:
            pass
    
    def save_json(self):
        """Save as JSON file"""
        if not self.hex_data:
            messagebox.showwarning("Warning", "No data to save")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            
            if filename:
                export_data = {
                    "seed": self.seed,
                    "dimensions": {"width": self.width, "height": self.height},
                    "hexes": {}
                }
                
                for (col, row), hex_data in self.hex_data.items():
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
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Saved: {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")
    
    def copy_to_game(self):
        """Copy to game maps folder"""
        if not self.hex_data:
            messagebox.showwarning("Warning", "No data to copy")
            return
        
        try:
            os.makedirs("maps", exist_ok=True)
            filename = f"maps/generated_simple_{self.seed}.json"
            
            export_data = {
                "seed": self.seed,
                "dimensions": {"width": self.width, "height": self.height},
                "hexes": {}
            }
            
            for (col, row), hex_data in self.hex_data.items():
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
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Success", f"Copied to: {filename}\\nLoad in game with 'Load Map'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Copy failed: {e}")
    
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Application error: {e}")


def main():
    """Main function"""
    print("Starting Simple Hex Map Generator...")
    
    try:
        app = SimpleHexGenerator()
        app.run()
    except Exception as e:
        print(f"Failed to start: {e}")


if __name__ == "__main__":
    main()