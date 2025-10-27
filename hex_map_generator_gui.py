"""
Hex Map Terrain Generator Tool - GUI Version
A cross-platform GUI tool for generating and previewing hex maps
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import random
import json
import math
import sys
import os
import time

# Add current directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from generation.minecraft_biomes import MinecraftBiomeGenerator
    from config.constants import TERRAIN_TYPES
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the hexcrawl directory")
    sys.exit(1)


class HexMapGeneratorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hex Map Terrain Generator")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Data
        self.biome_generator = None
        self.current_seed = random.randint(1, 1000000)
        self.map_width = 15
        self.map_height = 15
        self.hex_map_data = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Generation Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Row 1: Seed controls
        seed_frame = ttk.Frame(settings_frame)
        seed_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(seed_frame, text="Seed:").pack(side=tk.LEFT)
        self.seed_var = tk.StringVar(value=str(self.current_seed))
        seed_entry = ttk.Entry(seed_frame, textvariable=self.seed_var, width=12)
        seed_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Button(seed_frame, text="Random", 
                  command=self.randomize_seed).pack(side=tk.LEFT, padx=(0, 20))
        
        # Row 2: Dimension controls
        dim_frame = ttk.Frame(settings_frame)
        dim_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(dim_frame, text="Dimensions:").pack(side=tk.LEFT)
        
        ttk.Label(dim_frame, text="W:").pack(side=tk.LEFT, padx=(10, 0))
        self.width_var = tk.StringVar(value=str(self.map_width))
        width_spin = ttk.Spinbox(dim_frame, from_=5, to=200, width=6, 
                                textvariable=self.width_var)
        width_spin.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(dim_frame, text="H:").pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value=str(self.map_height))
        height_spin = ttk.Spinbox(dim_frame, from_=5, to=200, width=6,
                                 textvariable=self.height_var)
        height_spin.pack(side=tk.LEFT, padx=(2, 20))
        
        # Generate button
        self.generate_btn = ttk.Button(dim_frame, text="Generate Map", 
                                      command=self.generate_new_map)
        self.generate_btn.pack(side=tk.LEFT)
        
        # Status label instead of progress bar (more stable)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(dim_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(10, 0))
        
        # Content frame with two columns
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left column - Info and controls
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # Info display
        info_frame = ttk.LabelFrame(left_frame, text="Map Information", padding="5")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=15, width=35, wrap=tk.WORD, font=('Courier', 9))
        info_scroll = ttk.Scrollbar(info_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=info_scroll.set)
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Export buttons
        export_frame = ttk.LabelFrame(left_frame, text="Export", padding="5")
        export_frame.pack(fill=tk.X)
        
        ttk.Button(export_frame, text="Save as JSON", 
                  command=self.save_as_json).pack(fill=tk.X, pady=1)
        ttk.Button(export_frame, text="Copy to Game", 
                  command=self.copy_to_game).pack(fill=tk.X, pady=1)
        
        # Right column - ASCII Preview
        right_frame = ttk.LabelFrame(content_frame, text="Map Preview", padding="5")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.preview_text = tk.Text(right_frame, font=('Courier', 8), wrap=tk.NONE)
        preview_scroll_v = ttk.Scrollbar(right_frame, orient="vertical", command=self.preview_text.yview)
        preview_scroll_h = ttk.Scrollbar(right_frame, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(yscrollcommand=preview_scroll_v.set, xscrollcommand=preview_scroll_h.set)
        
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scroll_v.pack(side=tk.RIGHT, fill=tk.Y)
        preview_scroll_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Generate initial map
        self.root.after(100, self.generate_new_map)
    
    def randomize_seed(self):
        """Generate a random seed"""
        self.current_seed = random.randint(1, 1000000)
        self.seed_var.set(str(self.current_seed))
    
    def generate_new_map(self):
        """Generate a new hex map with current settings"""
        try:
            # Update status
            self.status_var.set("Generating...")
            self.generate_btn.config(state='disabled')
            self.root.update()
            
            # Get settings from UI
            try:
                self.current_seed = int(self.seed_var.get())
                self.map_width = int(self.width_var.get())
                self.map_height = int(self.height_var.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numbers")
                return
            
            # Validate dimensions
            if self.map_width > 200 or self.map_height > 200:
                if not messagebox.askyesno("Large Map Warning", 
                    f"Generating a {self.map_width}x{self.map_height} map may take a while and use significant memory. Continue?"):
                    return
            
            # Create biome generator
            self.biome_generator = MinecraftBiomeGenerator(self.current_seed)
            
            # Generate hex map data with progress updates
            self.hex_map_data = {}
            biome_counts = {}
            total_hexes = self.map_width * self.map_height
            
            for col in range(self.map_width):
                for row in range(self.map_height):
                    # Update progress every 100 hexes for large maps
                    if (col * self.map_height + row) % 100 == 0:
                        progress = ((col * self.map_height + row) / total_hexes) * 100
                        self.status_var.set(f"Generating... {progress:.0f}%")
                        self.root.update()
                    
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
            
            # Update displays
            self.status_var.set("Updating display...")
            self.root.update()
            self.update_displays(biome_counts)
            
            self.status_var.set(f"Complete! {total_hexes} hexes generated")
            
        except Exception as e:
            messagebox.showerror("Error", f"Generation failed: {e}")
            self.status_var.set("Error occurred")
        finally:
            # Re-enable button
            self.generate_btn.config(state='normal')
    
    def update_displays(self, biome_counts):
        """Update the information and preview displays"""
        self.update_info_display(biome_counts)
        self.update_preview_display()
    
    def update_info_display(self, biome_counts):
        """Update the information display"""
        self.info_text.delete(1.0, tk.END)
        
        info = f"Map: {self.map_width} x {self.map_height}\\n"
        info += f"Hexes: {len(self.hex_map_data)}\\n"
        info += f"Seed: {self.current_seed}\\n\\n"
        info += "Terrain Distribution:\\n"
        info += "-" * 25 + "\\n"
        
        total_hexes = len(self.hex_map_data)
        for terrain, count in sorted(biome_counts.items()):
            percentage = (count / total_hexes) * 100
            terrain_info = TERRAIN_TYPES.get(terrain, {"description": "Unknown"})
            info += f"{terrain.title()}: {count} ({percentage:.1f}%)\\n"
            info += f"  {terrain_info['description']}\\n\\n"
        
        self.info_text.insert(tk.END, info)
    
    def update_preview_display(self):
        """Update the ASCII preview display"""
        self.preview_text.delete(1.0, tk.END)
        
        if not self.hex_map_data:
            return
        
        # Create terrain symbol mapping
        terrain_symbols = {
            'water': '~', 'forest': 'T', 'plains': '.', 'mountains': '^',
            'desert': 'S', 'swamp': 'M', 'tundra': 'I', 'hills': 'h'
        }
        
        # For very large maps, show a scaled down version
        show_width = min(self.map_width, 100)
        show_height = min(self.map_height, 100)
        scale_x = self.map_width / show_width
        scale_y = self.map_height / show_height
        
        preview = f"ASCII Preview ({self.map_width}x{self.map_height})"
        if show_width != self.map_width or show_height != self.map_height:
            preview += f" - Scaled to {show_width}x{show_height}\\n"
        else:
            preview += "\\n"
            
        preview += "Legend: ~ Water, T Forest, . Plains, ^ Mountains\\n"
        preview += "        S Desert, M swaMp, I Ice/tundra, h Hills\\n"
        preview += "-" * (show_width * 2 + 5) + "\\n"
        
        for display_row in range(show_height):
            line = ""
            # Indent every other row for hex offset
            if display_row % 2 == 1:
                line += " "
            
            for display_col in range(show_width):
                # Map display coordinates to actual map coordinates
                actual_col = int(display_col * scale_x)
                actual_row = int(display_row * scale_y)
                
                if (actual_col, actual_row) in self.hex_map_data:
                    terrain = self.hex_map_data[(actual_col, actual_row)]['terrain']
                    symbol = terrain_symbols.get(terrain, '?')
                    line += symbol + " "
                else:
                    line += "? "
            line += "\\n"
            preview += line
        
        if show_width != self.map_width or show_height != self.map_height:
            preview += f"\\nNote: Preview scaled from {self.map_width}x{self.map_height} to fit display"
        
        self.preview_text.insert(tk.END, preview)
    
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
                              f"Map copied to game!\\n\\n"
                              f"File: {filename}\\n"
                              f"Load this in the game using 'Load Map'.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy map to game: {e}")
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


def main():
    """Main entry point"""
    print("Starting Hex Map Generator GUI...")
    
    try:
        app = HexMapGeneratorGUI()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()