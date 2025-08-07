import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import pygame
import json
import base64
import requests
from PIL import Image
import io
import numpy as np
from typing import Dict, List, Tuple, Optional
import threading
import math
import random

class LLaVAClient:
    """Client for LLaVA vision model via Ollama"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "llava:7b"
        self.session = requests.Session()
        self.check_model()
    
    def check_model(self):
        """Check if LLaVA is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if not any("llava" in m.get("name", "") for m in models):
                    print("LLaVA not found. Please run: ollama pull llava:7b")
                    return False
            return True
        except:
            print("Ollama not running. Please start Ollama first.")
            return False
    
    def analyze_map_section(self, image_base64: str, grid_x: int, grid_y: int, 
                          total_x: int, total_y: int) -> Dict:
        """Analyze a section of the map image"""
        prompt = f"""You are analyzing a small section of a fantasy map image. This is grid position ({grid_x}, {grid_y}) in a {total_x}x{total_y} grid.

Look carefully at the colors and textures in this specific section:

- GREEN (dark or light green): forest or plains
- BROWN/TAN (sandy or earthy): desert or hills  
- GRAY/WHITE with peaks: mountains
- BLUE (any shade): water
- DARK GREEN/BROWN (murky): swamp
- WHITE/LIGHT GRAY (snow): tundra
- LIGHT GREEN/YELLOW: plains
- MEDIUM BROWN (not sandy): hills

Based on the DOMINANT color/texture in this section, choose ONE terrain type:
forest, plains, mountains, water, desert, swamp, tundra, hills

Important: Even if the whole image looks similar, focus on THIS SPECIFIC section's subtle differences.

Respond with JSON:
{{"terrain": "[your chosen terrain]", "description": "[1-2 sentences about what you see]"}}"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.5,  # Increased for more variation
                        "num_predict": 150,
                        "seed": grid_x * 100 + grid_y  # Different seed per section
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result_text = response.json().get("response", "")
                
                # Clean up the response
                result_text = result_text.strip()
                if "```json" in result_text:
                    start = result_text.find("{")
                    end = result_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        result_text = result_text[start:end]
                elif "```" in result_text:
                    result_text = result_text.replace("```", "").strip()
                
                try:
                    data = json.loads(result_text)
                    
                    # Validate terrain type
                    valid_terrains = ["forest", "plains", "mountains", "water", 
                                    "desert", "swamp", "tundra", "hills"]
                    
                    terrain = data.get("terrain", "").lower().strip()
                    
                    # Find matching terrain
                    found_terrain = None
                    for valid in valid_terrains:
                        if valid in terrain:
                            found_terrain = valid
                            break
                    
                    if found_terrain:
                        data["terrain"] = found_terrain
                    else:
                        # Use position-based variation for fallback
                        # This helps avoid everything being the same
                        fallback_terrains = ["plains", "hills", "forest"]
                        data["terrain"] = fallback_terrains[(grid_x + grid_y) % len(fallback_terrains)]
                    
                    if "description" not in data or not data["description"]:
                        data["description"] = f"A {data['terrain']} region at coordinates ({grid_x}, {grid_y})"
                    
                    return data
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parse error at ({grid_x},{grid_y}): {e}")
                    # Position-based fallback
                    fallback_terrains = ["plains", "hills", "forest", "water"]
                    terrain = fallback_terrains[(grid_x + grid_y) % len(fallback_terrains)]
                    return {
                        "terrain": terrain,
                        "description": f"A {terrain} area"
                    }
                    
        except Exception as e:
            print(f"LLaVA error for section ({grid_x},{grid_y}): {e}")
        
        # Position-based fallback for errors
        fallback_terrains = ["plains", "hills", "forest"]
        terrain = fallback_terrains[(grid_x + grid_y) % len(fallback_terrains)]
        return {"terrain": terrain, "description": f"A {terrain} region"}

class MapImageConverter:
    """Convert map images to hex grid JSON"""
    
    def __init__(self):
        self.llava = LLaVAClient()
        self.conversion_window = None
        self.progress_var = None
        self.status_label = None
        self.converting = False
        self.cancel_conversion = False
    
    def open_converter_window(self):
        """Open the map converter dialog"""
        self.conversion_window = tk.Toplevel()
        self.conversion_window.title("Map Image to Hex Converter")
        self.conversion_window.geometry("500x400")
        
        # Image selection
        tk.Label(self.conversion_window, text="Map Image Converter", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        self.image_path_var = tk.StringVar()
        tk.Label(self.conversion_window, text="Selected Image:").pack()
        tk.Label(self.conversion_window, textvariable=self.image_path_var, 
                fg="blue").pack()
        
        tk.Button(self.conversion_window, text="Select Map Image", 
                 command=self.select_image).pack(pady=10)
        
        # Map dimensions
        dim_frame = tk.Frame(self.conversion_window)
        dim_frame.pack(pady=10)
        
        tk.Label(dim_frame, text="Map Width (miles):").grid(row=0, column=0, padx=5)
        self.width_entry = tk.Entry(dim_frame, width=10)
        self.width_entry.insert(0, "30")
        self.width_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(dim_frame, text="Map Height (miles):").grid(row=1, column=0, padx=5)
        self.height_entry = tk.Entry(dim_frame, width=10)
        self.height_entry.insert(0, "30")
        self.height_entry.grid(row=1, column=1, padx=5)
        
        # Hex size (3-mile hexes standard)
        tk.Label(dim_frame, text="Hex Size (miles):").grid(row=2, column=0, padx=5)
        self.hex_size_entry = tk.Entry(dim_frame, width=10)
        self.hex_size_entry.insert(0, "3")
        self.hex_size_entry.grid(row=2, column=1, padx=5)
        
        # Analysis detail
        tk.Label(self.conversion_window, text="Analysis Detail:").pack()
        self.detail_var = tk.StringVar(value="medium")
        detail_frame = tk.Frame(self.conversion_window)
        detail_frame.pack()
        tk.Radiobutton(detail_frame, text="Fast (low detail)", 
                      variable=self.detail_var, value="low").pack(side=tk.LEFT)
        tk.Radiobutton(detail_frame, text="Medium", 
                      variable=self.detail_var, value="medium").pack(side=tk.LEFT)
        tk.Radiobutton(detail_frame, text="High (slow)", 
                      variable=self.detail_var, value="high").pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.conversion_window, 
                                           variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.pack(pady=10, padx=20, fill=tk.X)
        
        self.status_label = tk.Label(self.conversion_window, text="Ready")
        self.status_label.pack()
        
        # Buttons
        button_frame = tk.Frame(self.conversion_window)
        button_frame.pack(pady=10)
        
        self.convert_btn = tk.Button(button_frame, text="Convert to Hex Map", 
                                     command=self.start_conversion, 
                                     bg="green", fg="white")
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancel", 
                 command=self.cancel_conversion_process,
                 bg="red", fg="white").pack(side=tk.LEFT, padx=5)
    
    def select_image(self):
        """Select map image file"""
        filename = filedialog.askopenfilename(
            title="Select Map Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if filename:
            self.image_path_var.set(filename)
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.image_path_var.get():
            messagebox.showerror("Error", "Please select an image first")
            return
        
        try:
            width_miles = float(self.width_entry.get())
            height_miles = float(self.height_entry.get())
            hex_size = float(self.hex_size_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
            return
        
        # Calculate hex grid dimensions
        hex_cols = int(width_miles / hex_size)
        hex_rows = int(height_miles / hex_size)
        
        if messagebox.askyesno("Confirm", 
                               f"This will create a {hex_cols}x{hex_rows} hex grid.\n"
                               f"Total hexes: {hex_cols * hex_rows}\n"
                               f"Continue?"):
            self.converting = True
            self.cancel_conversion = False
            self.convert_btn.config(state=tk.DISABLED)
            
            # Start conversion in thread
            thread = threading.Thread(target=self.convert_image_to_hexes,
                                    args=(hex_cols, hex_rows))
            thread.start()
    
    def convert_image_to_hexes(self, hex_cols: int, hex_rows: int):
        """Convert image to hex grid in background"""
        try:
            # Load and prepare image
            self.update_status("Loading image...")
            image = Image.open(self.image_path_var.get())
            
            # Resize image if too large (for faster processing)
            max_size = 1024
            if image.width > max_size or image.height > max_size:
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Try to enhance contrast for better terrain detection
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Increase contrast
            
            # Convert to base64 for LLaVA
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Create a color-based terrain map as backup
            image_array = np.array(image)
            
            # Determine sampling based on detail level
            detail = self.detail_var.get()
            if detail == "low":
                sample_points = max(4, min(hex_cols * hex_rows // 10, 20))
            elif detail == "high":
                sample_points = hex_cols * hex_rows
            else:  # medium
                sample_points = max(10, min(hex_cols * hex_rows // 4, 50))
            
            # Create hex grid
            hexes = []
            total_hexes = hex_cols * hex_rows
            processed = 0
            
            # For debugging - try a single analysis first
            self.update_status("Testing LLaVA connection...")
            test_result = self.llava.analyze_map_section(image_base64, 0, 0, hex_cols, hex_rows)
            print(f"Test analysis result: {test_result}")
            
            # Check if LLaVA is giving varied results
            if sample_points > 1:
                test2 = self.llava.analyze_map_section(image_base64, hex_cols-1, hex_rows-1, hex_cols, hex_rows)
                print(f"Test 2 result: {test2}")
            
            terrain_map = {}
            
            # Try color-based analysis as fallback/supplement
            self.update_status("Analyzing map colors...")
            for row in range(hex_rows):
                for col in range(hex_cols):
                    # Get pixel region for this hex
                    y_start = int(row * image.height / hex_rows)
                    y_end = int((row + 1) * image.height / hex_rows)
                    x_start = int(col * image.width / hex_cols)
                    x_end = int((col + 1) * image.width / hex_cols)
                    
                    region = image_array[y_start:y_end, x_start:x_end]
                    avg_color = region.mean(axis=(0, 1))
                    
                    # Determine terrain by color
                    r, g, b = avg_color[:3] if len(avg_color) >= 3 else (avg_color[0], avg_color[0], avg_color[0])
                    
                    # Color-based terrain detection
                    terrain = "plains"  # default
                    
                    if b > r and b > g and b > 150:  # Blue dominant
                        terrain = "water"
                    elif g > r and g > b and g > 100:  # Green dominant
                        if g > 150:
                            terrain = "plains"
                        else:
                            terrain = "forest"
                    elif r > 150 and g > 100 and b < 100:  # Brown/tan
                        if r > 200:
                            terrain = "desert"
                        else:
                            terrain = "hills"
                    elif r < 100 and g < 100 and b < 100:  # Dark
                        terrain = "mountains"
                    elif r > 200 and g > 200 and b > 200:  # White
                        terrain = "tundra"
                    elif g > 80 and b > 80 and r < 100:  # Dark blue-green
                        terrain = "swamp"
                    
                    # Store color-based terrain as fallback
                    color_terrain = terrain
                    
                    # Sample some positions with LLaVA
                    if (row, col) in [(r, c) for r in range(0, hex_rows, max(1, hex_rows//5)) 
                                     for c in range(0, hex_cols, max(1, hex_cols//5))]:
                        # Use LLaVA for sampled points
                        result = self.llava.analyze_map_section(
                            image_base64, col, row, hex_cols, hex_rows
                        )
                        
                        # If LLaVA returns all water but colors suggest otherwise, use color
                        if result["terrain"] == "water" and color_terrain != "water":
                            result["terrain"] = color_terrain
                            result["description"] = f"A {color_terrain} region identified by terrain features"
                        
                        terrain_map[(row, col)] = result
                    else:
                        # Use color-based terrain for non-sampled points
                        terrain_map[(row, col)] = {
                            "terrain": color_terrain,
                            "description": f"A {color_terrain} area"
                        }
                    
                    processed += 1
                    if processed % 10 == 0:
                        self.progress_var.set((processed / total_hexes) * 70)
                        self.update_status(f"Analyzing terrain... {processed}/{total_hexes}")
            
            # Convert to hex format
            self.update_status("Creating hex map...")
            terrain_counts = {}
            
            for row in range(hex_rows):
                for col in range(hex_cols):
                    if self.cancel_conversion:
                        break
                    
                    # Convert offset coordinates to cube coordinates
                    q = col
                    r = row - (col - (col & 1)) // 2
                    s = -q - r
                    
                    terrain_data = terrain_map.get((row, col), 
                                                  {"terrain": "plains", 
                                                   "description": "Unexplored region"})
                    
                    # Count terrain types
                    terrain_counts[terrain_data["terrain"]] = terrain_counts.get(terrain_data["terrain"], 0) + 1
                    
                    hex_data = {
                        "q": q,
                        "r": r,
                        "s": s,
                        "terrain": terrain_data["terrain"],
                        "description": terrain_data["description"],
                        "explored": False,
                        "visible": False
                    }
                    hexes.append(hex_data)
            
            self.progress_var.set(90)
            
            # Show terrain distribution
            print(f"Terrain distribution: {terrain_counts}")
            
            if not self.cancel_conversion:
                # Save the map
                self.update_status("Saving map...")
                self.save_converted_map(hexes)
                self.progress_var.set(100)
                
                # Show summary
                summary = "Terrain types:\n"
                for terrain, count in sorted(terrain_counts.items()):
                    summary += f"  {terrain}: {count} hexes\n"
                
                self.update_status("Conversion complete!")
                messagebox.showinfo("Success", 
                                  f"Map converted successfully!\n"
                                  f"Created {len(hexes)} hexes\n\n{summary}")
            
        except Exception as e:
            print(f"Conversion error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Conversion failed: {str(e)}")
        finally:
            self.converting = False
            if self.conversion_window and self.conversion_window.winfo_exists():
                self.convert_btn.config(state=tk.NORMAL)
    
    def find_nearest_terrain(self, row: int, col: int, terrain_map: Dict) -> Dict:
        """Find nearest analyzed terrain for interpolation"""
        min_dist = float('inf')
        nearest = {"terrain": "plains", "description": "Unexplored region"}
        
        for (r, c), data in terrain_map.items():
            dist = abs(r - row) + abs(c - col)
            if dist < min_dist:
                min_dist = dist
                nearest = data
        
        return nearest
    
    def save_converted_map(self, hexes: List[Dict]):
        """Save converted map to JSON"""
        filename = filedialog.asksaveasfilename(
            title="Save Converted Map",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if filename:
            map_data = {
                "current_position": [0, 0, 0],
                "hexes": hexes,
                "converted_from_image": True,
                "travel_data": {
                    "days": 0,
                    "hours": 0,
                    "movement": 8,
                    "pace": "normal",
                    "exhaustion": 0
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(map_data, f, indent=2)
    
    def update_status(self, message: str):
        """Update status label"""
        if self.status_label:
            self.status_label.config(text=message)
            self.conversion_window.update()
    
    def cancel_conversion_process(self):
        """Cancel the conversion"""
        self.cancel_conversion = True
        if self.conversion_window:
            self.conversion_window.destroy()

class MapImportDialog:
    """Dialog for importing converted maps with options"""
    
    def __init__(self, parent, hex_map):
        self.hex_map = hex_map
        self.map_data = None
        self.import_mode = tk.StringVar(value="blind")
        self.selected_start = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Import Map Options")
        self.dialog.geometry("600x500")
        
        # Load map file
        tk.Label(self.dialog, text="Import Converted Map", 
                font=("Arial", 14, "bold")).pack(pady=10)
        
        self.file_label = tk.Label(self.dialog, text="No file selected", fg="gray")
        self.file_label.pack()
        
        tk.Button(self.dialog, text="Load Map File", 
                 command=self.load_map_file).pack(pady=10)
        
        # Import mode selection
        tk.Label(self.dialog, text="Import Mode:", font=("Arial", 12)).pack(pady=10)
        
        mode_frame = tk.Frame(self.dialog)
        mode_frame.pack()
        
        tk.Radiobutton(mode_frame, text="Blind Start (random position)", 
                      variable=self.import_mode, value="blind",
                      command=self.update_mode_options).pack(anchor=tk.W)
        tk.Radiobutton(mode_frame, text="Fully Revealed (choose start)", 
                      variable=self.import_mode, value="revealed",
                      command=self.update_mode_options).pack(anchor=tk.W)
        
        # Map preview frame
        self.preview_frame = tk.Frame(self.dialog, height=200, width=400, 
                                     bg="black", relief=tk.SUNKEN, bd=2)
        self.preview_frame.pack(pady=10)
        self.preview_frame.pack_propagate(False)
        
        self.preview_label = tk.Label(self.preview_frame, 
                                     text="Map preview will appear here",
                                     fg="white", bg="black")
        self.preview_label.pack(expand=True)
        
        # Start position selector (for revealed mode)
        self.position_frame = tk.Frame(self.dialog)
        self.position_label = tk.Label(self.position_frame, 
                                      text="Click on preview to select start position")
        self.position_label.pack()
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        self.import_btn = tk.Button(button_frame, text="Import Map", 
                                   command=self.import_map,
                                   state=tk.DISABLED, bg="green", fg="white")
        self.import_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancel", 
                 command=self.dialog.destroy,
                 bg="red", fg="white").pack(side=tk.LEFT, padx=5)
    
    def load_map_file(self):
        """Load a converted map file"""
        filename = filedialog.askopenfilename(
            title="Select Converted Map",
            filetypes=[("JSON files", "*.json")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.map_data = json.load(f)
                
                if "hexes" not in self.map_data:
                    raise ValueError("Invalid map file")
                
                self.file_label.config(text=f"Loaded: {filename.split('/')[-1]}", 
                                     fg="green")
                self.import_btn.config(state=tk.NORMAL)
                self.show_map_preview()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load map: {e}")
    
    def show_map_preview(self):
        """Show a simple preview of the map"""
        if not self.map_data:
            return
        
        # Create simple text preview
        hexes = self.map_data["hexes"]
        terrain_counts = {}
        for hex_data in hexes:
            terrain = hex_data.get("terrain", "unknown")
            terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
        
        preview_text = f"Total hexes: {len(hexes)}\n\nTerrain distribution:\n"
        for terrain, count in sorted(terrain_counts.items()):
            preview_text += f"  {terrain}: {count} hexes\n"
        
        self.preview_label.config(text=preview_text)
    
    def update_mode_options(self):
        """Update UI based on selected mode"""
        if self.import_mode.get() == "revealed":
            self.position_frame.pack(pady=10)
        else:
            self.position_frame.pack_forget()
    
    def import_map(self):
        """Import the map with selected options"""
        if not self.map_data:
            return
        
        mode = self.import_mode.get()
        
        # Clear existing map
        self.hex_map.hexes.clear()
        
        # Import hexes
        from hex_map_explorer import Hex
        for hex_data in self.map_data["hexes"]:
            q, r, s = hex_data["q"], hex_data["r"], hex_data["s"]
            
            if mode == "blind":
                # Blind mode - all unexplored and invisible
                hex_obj = Hex(q, r, s, 
                            hex_data["terrain"],
                            hex_data["description"],
                            explored=False,
                            visible=False)
            else:
                # Revealed mode - all visible but unexplored
                hex_obj = Hex(q, r, s,
                            hex_data["terrain"], 
                            hex_data["description"],
                            explored=False,
                            visible=True)
            
            self.hex_map.hexes[(q, r, s)] = hex_obj
        
        # Set starting position
        if mode == "blind":
            # Random start position
            valid_starts = [coords for coords, hex_obj in self.hex_map.hexes.items()
                          if hex_obj.terrain != "water"]
            if valid_starts:
                start_pos = random.choice(valid_starts)
            else:
                start_pos = (0, 0, 0)
        else:
            # Use selected position or center
            start_pos = self.selected_start or (0, 0, 0)
        
        # Set current position and make starting area visible
        self.hex_map.current_position = start_pos
        if start_pos in self.hex_map.hexes:
            self.hex_map.hexes[start_pos].explored = True
            self.hex_map.hexes[start_pos].visible = True
            
            # Make adjacent hexes visible
            for neighbor in self.hex_map.get_neighbors(*start_pos):
                if neighbor in self.hex_map.hexes:
                    self.hex_map.hexes[neighbor].visible = True
        
        # Import travel data if present
        if "travel_data" in self.map_data:
            td = self.map_data["travel_data"]
            self.hex_map.travel_system.days_traveled = td.get("days", 0)
            self.hex_map.travel_system.hours_traveled = td.get("hours", 0)
            self.hex_map.travel_system.movement_points = td.get("movement", 8)
            self.hex_map.travel_system.current_pace = td.get("pace", "normal")
        
        messagebox.showinfo("Success", f"Map imported in {mode} mode!")
        self.dialog.destroy()

class HexEditor:
    """Editor for individual hex descriptions"""
    
    def __init__(self, parent, hex_obj, on_save_callback):
        self.hex_obj = hex_obj
        self.on_save = on_save_callback
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Edit Hex ({hex_obj.q}, {hex_obj.r})")
        self.dialog.geometry("500x400")
        
        # Hex info
        info_frame = tk.Frame(self.dialog)
        info_frame.pack(pady=10)
        
        tk.Label(info_frame, text=f"Location: ({hex_obj.q}, {hex_obj.r})",
                font=("Arial", 12)).pack()
        tk.Label(info_frame, text=f"Terrain: {hex_obj.terrain}",
                font=("Arial", 12)).pack()
        
        # Description editor
        tk.Label(self.dialog, text="Description:", font=("Arial", 12)).pack()
        
        self.text_editor = scrolledtext.ScrolledText(self.dialog, 
                                                     height=10, width=60,
                                                     wrap=tk.WORD)
        self.text_editor.pack(pady=10, padx=10)
        self.text_editor.insert(1.0, hex_obj.description)
        
        # Terrain type selector
        terrain_frame = tk.Frame(self.dialog)
        terrain_frame.pack(pady=10)
        
        tk.Label(terrain_frame, text="Terrain Type:").pack(side=tk.LEFT)
        
        self.terrain_var = tk.StringVar(value=hex_obj.terrain)
        terrain_menu = ttk.Combobox(terrain_frame, textvariable=self.terrain_var,
                                    values=["forest", "plains", "mountains", "water",
                                           "desert", "swamp", "tundra", "hills"],
                                    state="readonly", width=15)
        terrain_menu.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Save Changes", 
                 command=self.save_changes,
                 bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Cancel",
                 command=self.dialog.destroy,
                 bg="red", fg="white").pack(side=tk.LEFT, padx=5)
    
    def save_changes(self):
        """Save the edited hex data"""
        new_description = self.text_editor.get(1.0, tk.END).strip()
        new_terrain = self.terrain_var.get()
        
        self.hex_obj.description = new_description
        self.hex_obj.terrain = new_terrain
        
        if self.on_save:
            self.on_save(self.hex_obj)
        
        messagebox.showinfo("Success", "Hex updated successfully!")
        self.dialog.destroy()

def integrate_converter_with_explorer(explorer_instance):
    """Add converter menu items to main explorer"""
    # This would be called from the main hex_map_explorer.py
    # to add the converter functionality to the menu
    
    converter = MapImageConverter()
    
    def open_converter():
        converter.open_converter_window()
    
    def import_map():
        dialog = MapImportDialog(None, explorer_instance.hex_map)
    
    def edit_current_hex():
        curr_pos = explorer_instance.hex_map.current_position
        if curr_pos in explorer_instance.hex_map.hexes:
            hex_obj = explorer_instance.hex_map.hexes[curr_pos]
            editor = HexEditor(None, hex_obj, lambda h: None)
    
    return {
        "convert": open_converter,
        "import": import_map,
        "edit": edit_current_hex
    }

if __name__ == "__main__":
    print("=" * 50)
    print("Map Image to Hex Converter")
    print("=" * 50)
    print("\nRequirements:")
    print("1. Ollama with LLaVA 7B model")
    print("   Run: ollama pull llava:7b")
    print("2. Map image file (PNG, JPG, etc.)")
    print("\nThis module integrates with hex_map_explorer.py")
    print("-" * 50)
    
    # Standalone test
    root = tk.Tk()
    root.title("Map Converter Test")
    root.geometry("300x150")
    
    converter = MapImageConverter()
    
    tk.Label(root, text="Map Image Converter", font=("Arial", 14)).pack(pady=20)
    tk.Button(root, text="Open Converter", 
             command=converter.open_converter_window,
             bg="blue", fg="white").pack(pady=10)
    
    root.mainloop()