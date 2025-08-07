"""
Stable GUI map generator with minimal dependencies
"""
import json
import random
import math
import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import os

class StableMapGenerator:
    """Stable map generator"""
    
    def __init__(self, seed=None):
        self.seed = seed if seed else random.randint(0, 1000000)
        random.seed(self.seed)
    
    def simple_noise(self, x, y, scale=1.0):
        """Simple pseudo-noise function using sine waves"""
        return (math.sin(x * scale) + math.cos(y * scale) + math.sin((x + y) * scale * 0.5)) / 3.0
    
    def fractal_noise(self, x, y, octaves=4, persistence=0.5, scale=0.01):
        """Generate fractal noise for more realistic terrain"""
        value = 0
        amplitude = 1
        frequency = scale
        max_value = 0
        
        for i in range(octaves):
            value += self.simple_noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2
        
        return value / max_value
    
    def generate_realistic_map(self, width, height):
        """Generate realistic terrain using improved algorithms"""
        hex_data = []
        
        # Generate multiple noise layers for different features
        for y in range(-height//2, height//2):
            for x in range(-width//2, width//2):
                q, r, s = x, y, -x-y
                
                # Set consistent random seed for this position
                random.seed(self.seed + x*1000 + y)
                
                # Multiple noise layers for realistic terrain
                # Continental shape (large scale)
                continent_noise = self.fractal_noise(x, y, octaves=3, scale=0.005, persistence=0.6)
                
                # Regional variation (medium scale) 
                regional_noise = self.fractal_noise(x, y, octaves=4, scale=0.02, persistence=0.5)
                
                # Local detail (small scale)
                local_noise = self.fractal_noise(x, y, octaves=6, scale=0.08, persistence=0.4)
                
                # Elevation calculation - increase range and add peaks
                elevation = (continent_noise * 0.6) + (regional_noise * 0.3) + (local_noise * 0.1)
                
                # Add some mountain peaks using additional noise
                mountain_noise = self.fractal_noise(x + 9000, y + 9000, octaves=2, scale=0.03)
                if mountain_noise > 0.4:  # Lower threshold for more mountains
                    elevation += 0.4  # Create mountain peaks
                
                # Add some randomness for variety
                elevation += (random.random() - 0.5) * 0.1
                
                # Distance-based falloff (but much gentler than before)
                distance = math.sqrt(x*x + y*y)
                max_dist = min(width, height) * 0.45
                distance_factor = max(0.1, 1 - (distance / max_dist) ** 1.2)  # Even gentler falloff
                elevation = elevation * distance_factor
                
                # Temperature based on latitude and local variation
                lat = abs(y) / (height * 0.5)
                temp_base = 1.0 - lat
                temp_noise = self.fractal_noise(x + 1000, y + 1000, octaves=3, scale=0.03)
                temperature = temp_base + temp_noise * 0.3
                
                # Moisture based on distance to water and local variation
                moisture_noise = self.fractal_noise(x + 2000, y + 2000, octaves=4, scale=0.04)
                moisture = 0.5 + moisture_noise * 0.5
                
                # Determine terrain based on elevation, temperature, and moisture
                # Adjusted thresholds based on actual value ranges
                if elevation < 0.0:
                    terrain = "water"  # Deep water/ocean
                elif elevation < 0.1:
                    if temperature > 0.5 and moisture > 0.5:
                        terrain = "swamp"
                    else:
                        terrain = "water"  # Shallow water/lakes
                elif elevation < 0.2:
                    # Low elevation - coastal areas
                    if moisture > 0.6:
                        terrain = "swamp"
                    elif temperature > 0.8 and moisture < 0.4:
                        terrain = "desert" 
                    elif temperature < 0.3:
                        terrain = "tundra"
                    else:
                        terrain = "plains"
                elif elevation < 0.35:
                    # Medium-low elevation - main land areas
                    if temperature < 0.3:
                        terrain = "tundra"
                    elif temperature > 0.7 and moisture < 0.5:
                        terrain = "desert"
                    elif moisture > 0.3 and temperature > 0.4:
                        terrain = "forest"
                    else:
                        terrain = "plains"
                elif elevation < 0.5:
                    # Medium-high elevation - hills and forests
                    if temperature < 0.4:
                        terrain = "tundra"
                    elif moisture > 0.4 and temperature > 0.5:
                        terrain = "forest"
                    else:
                        terrain = "hills"
                else:
                    # High elevation - mountains
                    if temperature < 0.5:
                        terrain = "tundra"  # Cold peaks
                    else:
                        terrain = "mountains"
                
                # Add some coastal variation and archipelagos
                if terrain == "water":
                    # Create some islands and coastal features
                    island_noise = self.fractal_noise(x + 3000, y + 3000, octaves=2, scale=0.1)
                    if island_noise > 0.4 and elevation > -0.3:
                        terrain = "plains" if temperature > 0.5 else "tundra"
                        
                # Create more realistic continent shapes with peninsulas and bays
                elif terrain != "water":
                    # Add coastal erosion effect
                    coastal_noise = self.fractal_noise(x + 4000, y + 4000, octaves=3, scale=0.06)
                    if elevation < 0.1 and coastal_noise < -0.3:
                        # Create bays and inlets
                        terrain = "water"
                    elif elevation < 0.2 and coastal_noise > 0.4:
                        # Create peninsulas and headlands
                        terrain = "plains"
                        
                # Add river systems (simple approximation)
                if terrain != "water" and elevation > 0.1:
                    river_noise = self.fractal_noise(x + 5000, y + 5000, octaves=2, scale=0.05)
                    # Rivers more likely in areas that drain toward lower elevation
                    river_probability = (0.6 - elevation) * 0.1
                    if abs(river_noise) < 0.1 and random.random() < river_probability:
                        terrain = "water"  # Rivers
                        
                # Improve biome transitions - add transition zones
                if terrain == "desert" and elevation > 0.2:
                    transition_noise = self.fractal_noise(x + 6000, y + 6000, octaves=2, scale=0.07)
                    if transition_noise > 0.2:
                        terrain = "plains"  # Desert edge
                        
                elif terrain == "forest" and temperature < 0.4:
                    transition_noise = self.fractal_noise(x + 7000, y + 7000, octaves=2, scale=0.07)
                    if transition_noise > 0.3:
                        terrain = "plains"  # Forest edge
                        
                elif terrain == "tundra" and temperature > 0.3:
                    transition_noise = self.fractal_noise(x + 8000, y + 8000, octaves=2, scale=0.07)
                    if transition_noise > 0.2:
                        terrain = "plains"  # Tundra edge
                
                hex_data.append({
                    "q": q, "r": r, "s": s,
                    "terrain": terrain,
                    "description": "Generated terrain",
                    "explored": False,
                    "visible": False, 
                    "generating": False
                })
        
        return {
            "seed": self.seed,
            "width": width,
            "height": height,
            "generator": "stable",
            "version": "1.0",
            "current_position": [0, 0, 0],
            "hexes": hex_data,
            "travel_data": {
                "current_pace": "normal",
                "current_transport": "on_foot",
                "movement_points": 8,
                "exhaustion_level": 0,
                "party_members": []
            }
        }

class SimpleGUI:
    """Simple, stable GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Map Generator")
        self.root.geometry("400x300")
        
        # Variables
        self.size_var = tk.StringVar(value="Medium (100x100)")
        self.seed_var = tk.StringVar()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup simple UI"""
        # Title
        tk.Label(self.root, text="Realistic Map Generator v2.0", font=("Arial", 14, "bold")).pack(pady=5)
        tk.Label(self.root, text="Advanced Terrain Generation", font=("Arial", 10), fg="gray").pack()
        
        # Size selection
        tk.Label(self.root, text="Map Size:").pack()
        size_frame = tk.Frame(self.root)
        size_frame.pack(pady=5)
        
        for size in ["Small (50x50)", "Medium (100x100)", "Large (150x150)"]:
            tk.Radiobutton(size_frame, text=size, variable=self.size_var, value=size).pack()
        
        # Seed
        tk.Label(self.root, text="Seed (optional):").pack(pady=(20,0))
        tk.Entry(self.root, textvariable=self.seed_var, width=20).pack()
        
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Random", command=self.random_seed).pack(side=tk.LEFT, padx=5)
        
        # Generate button
        tk.Button(self.root, text="Generate & Save Map", 
                 command=self.generate_map, bg="green", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=20)
        
        # Status
        self.status = tk.Label(self.root, text="Ready")
        self.status.pack()
    
    def random_seed(self):
        """Generate random seed"""
        self.seed_var.set(str(random.randint(0, 999999)))
    
    def get_size(self):
        """Get map dimensions"""
        size = self.size_var.get()
        if "50x50" in size:
            return 50, 50
        elif "150x150" in size:
            return 150, 150
        else:
            return 100, 100
    
    def generate_map(self):
        """Generate and save map"""
        try:
            self.status.config(text="Generating...")
            self.root.update()
            
            width, height = self.get_size()
            seed = None
            if self.seed_var.get().strip():
                try:
                    seed = int(self.seed_var.get())
                except ValueError:
                    seed = hash(self.seed_var.get())
            
            # Generate
            generator = StableMapGenerator(seed)
            map_data = generator.generate_realistic_map(width, height)
            
            # Save
            filename = filedialog.asksaveasfilename(
                title="Save Map",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=f"realistic_map_{map_data['seed']}.json"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    json.dump(map_data, f, indent=2)
                
                messagebox.showinfo("Success", 
                    f"Map generated successfully!\n\n"
                    f"Size: {width}x{height}\n"
                    f"Hexes: {len(map_data['hexes'])}\n"
                    f"Seed: {map_data['seed']}\n"
                    f"File: {filename}")
                
                self.status.config(text="Map saved successfully!")
            else:
                self.status.config(text="Cancelled")
                
        except Exception as e:
            messagebox.showerror("Error", f"Generation failed: {e}")
            self.status.config(text="Error occurred")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()

def main():
    """Main function"""
    try:
        app = SimpleGUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        try:
            tk.messagebox.showerror("Error", f"Failed to start: {e}")
        except:
            pass

if __name__ == "__main__":
    main()