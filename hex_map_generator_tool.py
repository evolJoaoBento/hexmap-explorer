"""
Hex Map Terrain Generator Tool
A GUI tool for generating and previewing hex maps with different dimensions
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import json
import math
from PIL import Image, ImageDraw, ImageTk
import sys
import os

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generation.minecraft_biomes import MinecraftBiomeGenerator
    from config.constants import TERRAIN_TYPES
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the hexcrawl directory")
    sys.exit(1)


class HexMapGeneratorTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hex Map Terrain Generator")
        self.root.geometry("800x600")
        
        # Generator and map data
        self.biome_generator = None
        self.current_seed = random.randint(1, 1000000)
        self.map_width = 20
        self.map_height = 20
        self.hex_map_data = {}
        self.preview_image = None
        
        self.setup_ui()
        self.generate_new_map()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Controls frame
        controls_frame = ttk.LabelFrame(main_frame, text="Map Generation Settings", padding="10")
        controls_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Seed controls
        ttk.Label(controls_frame, text="Seed:").grid(row=0, column=0, sticky=tk.W)
        self.seed_var = tk.StringVar(value=str(self.current_seed))
        seed_entry = ttk.Entry(controls_frame, textvariable=self.seed_var, width=15)
        seed_entry.grid(row=0, column=1, padx=(5, 10))
        
        ttk.Button(controls_frame, text="Random Seed", 
                  command=self.randomize_seed).grid(row=0, column=2, padx=(0, 20))
        
        # Dimensions controls
        ttk.Label(controls_frame, text="Width:").grid(row=0, column=3, sticky=tk.W)
        self.width_var = tk.StringVar(value=str(self.map_width))
        width_spin = ttk.Spinbox(controls_frame, from_=5, to=50, width=8, 
                                textvariable=self.width_var)
        width_spin.grid(row=0, column=4, padx=(5, 10))
        
        ttk.Label(controls_frame, text="Height:").grid(row=0, column=5, sticky=tk.W)
        self.height_var = tk.StringVar(value=str(self.map_height))
        height_spin = ttk.Spinbox(controls_frame, from_=5, to=50, width=8,
                                 textvariable=self.height_var)
        height_spin.grid(row=0, column=6, padx=(5, 10))
        
        # Generation button
        ttk.Button(controls_frame, text="Generate Map", 
                  command=self.generate_new_map).grid(row=0, column=7, padx=(10, 0))
        
        # Info panel
        info_frame = ttk.LabelFrame(main_frame, text="Map Information", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), padx=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=8, width=30)
        info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        # Preview panel
        preview_frame = ttk.LabelFrame(main_frame, text="Map Preview", padding="10")
        preview_frame.grid(row=1, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # Canvas for map preview
        self.preview_canvas = tk.Canvas(preview_frame, bg='white')
        canvas_scroll_v = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_canvas.yview)
        canvas_scroll_h = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_canvas.xview)
        self.preview_canvas.configure(yscrollcommand=canvas_scroll_v.set, xscrollcommand=canvas_scroll_h.set)
        
        self.preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_scroll_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
        canvas_scroll_h.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Export controls
        export_frame = ttk.LabelFrame(main_frame, text="Export Options", padding="10")
        export_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(export_frame, text="Save as JSON", 
                  command=self.save_as_json).grid(row=0, column=0, pady=2, sticky=tk.W)
        ttk.Button(export_frame, text="Save as Image", 
                  command=self.save_as_image).grid(row=1, column=0, pady=2, sticky=tk.W)
        ttk.Button(export_frame, text="Copy to Game", 
                  command=self.copy_to_game).grid(row=2, column=0, pady=2, sticky=tk.W)
    
    def randomize_seed(self):
        """Generate a random seed"""
        self.current_seed = random.randint(1, 1000000)
        self.seed_var.set(str(self.current_seed))
    
    def generate_new_map(self):
        """Generate a new hex map with current settings"""
        try:
            # Get settings from UI
            self.current_seed = int(self.seed_var.get())
            self.map_width = int(self.width_var.get())
            self.map_height = int(self.height_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for seed and dimensions")
            return
        
        # Create biome generator
        self.biome_generator = MinecraftBiomeGenerator(self.current_seed)
        
        # Generate hex map data using offset coordinates
        self.hex_map_data = {}
        biome_counts = {}
        
        for col in range(self.map_width):
            for row in range(self.map_height):
                # Convert offset coordinates to cube coordinates
                q = col - (row - (row & 1)) // 2
                r = row
                s = -q - r
                
                # Generate terrain for this hex
                terrain = self.biome_generator.select_biome(q, r, s)
                
                # Store hex data
                self.hex_map_data[(col, row)] = {
                    'q': q, 'r': r, 's': s,
                    'terrain': terrain,
                    'col': col, 'row': row
                }
                
                # Count biomes
                biome_counts[terrain] = biome_counts.get(terrain, 0) + 1
        
        # Update info display
        self.update_info_display(biome_counts)
        
        # Generate preview
        self.generate_preview()
    
    def update_info_display(self, biome_counts):
        """Update the information display"""
        self.info_text.delete(1.0, tk.END)
        
        info = f"Map Dimensions: {self.map_width} x {self.map_height}\n"
        info += f"Total Hexes: {len(self.hex_map_data)}\n"
        info += f"Seed: {self.current_seed}\n\n"
        info += "Terrain Distribution:\n"
        info += "-" * 20 + "\n"
        
        total_hexes = len(self.hex_map_data)
        for terrain, count in sorted(biome_counts.items()):
            percentage = (count / total_hexes) * 100
            terrain_info = TERRAIN_TYPES.get(terrain, {"description": "Unknown"})
            info += f"{terrain.title()}: {count} ({percentage:.1f}%)\n"
            info += f"  {terrain_info['description']}\n\n"
        
        self.info_text.insert(tk.END, info)
    
    def generate_preview(self):
        """Generate visual preview of the hex map"""
        if not self.hex_map_data:
            return
        
        # Calculate hex size and image dimensions
        hex_size = 20  # Radius of each hex
        hex_width = hex_size * 2
        hex_height = hex_size * math.sqrt(3)
        
        # Calculate image size
        img_width = int(self.map_width * hex_width * 0.75 + hex_size)
        img_height = int(self.map_height * hex_height + hex_height * 0.5)
        
        # Create image
        img = Image.new('RGB', (img_width, img_height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Draw hexes
        for (col, row), hex_data in self.hex_map_data.items():
            # Calculate hex center position
            x = col * hex_width * 0.75 + hex_size
            y = row * hex_height + (col % 2) * hex_height * 0.5 + hex_size
            
            # Get terrain color
            terrain = hex_data['terrain']
            color = TERRAIN_TYPES.get(terrain, {"color": (128, 128, 128)})["color"]
            
            # Generate hex vertices
            vertices = []
            for i in range(6):
                angle = math.pi / 3 * i
                vertex_x = x + hex_size * math.cos(angle)
                vertex_y = y + hex_size * math.sin(angle)
                vertices.append((vertex_x, vertex_y))
            
            # Draw filled hex
            draw.polygon(vertices, fill=color, outline='black')
        
        # Convert to PhotoImage for tkinter
        self.preview_image = img
        img_tk = ImageTk.PhotoImage(img)
        
        # Update canvas
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
        
        # Keep reference to prevent garbage collection
        self.preview_canvas.image = img_tk
    
    def save_as_json(self):
        """Save the hex map data as JSON"""
        if not self.hex_map_data:
            messagebox.showwarning("Warning", "No map data to save. Generate a map first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Hex Map as JSON"
        )
        
        if filename:
            try:
                # Convert to format compatible with game
                export_data = {
                    "seed": self.current_seed,
                    "dimensions": {"width": self.map_width, "height": self.map_height},
                    "hexes": {}
                }
                
                for (col, row), hex_data in self.hex_map_data.items():
                    key = f"{hex_data['q']},{hex_data['r']},{hex_data['s']}"
                    export_data["hexes"][key] = {
                        "q": hex_data['q'],
                        "r": hex_data['r'],
                        "s": hex_data['s'],
                        "terrain": hex_data['terrain'],
                        "description": f"A {TERRAIN_TYPES[hex_data['terrain']]['description'].lower()}",
                        "explored": False,
                        "visible": False
                    }
                
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Success", f"Map saved as {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save map: {e}")
    
    def save_as_image(self):
        """Save the preview image"""
        if not self.preview_image:
            messagebox.showwarning("Warning", "No preview image to save. Generate a map first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Map Preview as Image"
        )
        
        if filename:
            try:
                self.preview_image.save(filename)
                messagebox.showinfo("Success", f"Image saved as {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")
    
    def copy_to_game(self):
        """Copy map data to game directory for immediate use"""
        if not self.hex_map_data:
            messagebox.showwarning("Warning", "No map data to copy. Generate a map first.")
            return
        
        try:
            # Generate filename with seed
            filename = f"maps/generated_map_seed_{self.current_seed}.json"
            
            # Create maps directory if it doesn't exist
            os.makedirs("maps", exist_ok=True)
            
            # Convert to format compatible with game
            export_data = {
                "seed": self.current_seed,
                "dimensions": {"width": self.map_width, "height": self.map_height},
                "hexes": {}
            }
            
            for (col, row), hex_data in self.hex_map_data.items():
                key = f"{hex_data['q']},{hex_data['r']},{hex_data['s']}"
                export_data["hexes"][key] = {
                    "q": hex_data['q'],
                    "r": hex_data['r'],
                    "s": hex_data['s'],
                    "terrain": hex_data['terrain'],
                    "description": f"A {TERRAIN_TYPES[hex_data['terrain']]['description'].lower()}",
                    "explored": False,
                    "visible": False
                }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Success", 
                              f"Map copied to game directory!\n\n"
                              f"File: {filename}\n"
                              f"You can now load this map in the game using 'Load Map'.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy map to game: {e}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    print("Starting Hex Map Generator Tool...")
    
    try:
        app = HexMapGeneratorTool()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()