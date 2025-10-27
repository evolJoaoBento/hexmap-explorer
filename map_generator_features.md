# Hex Map Generator - Feature Overview

## 🎯 Visual Hex Map Generator

### **Main Features:**
- ✅ **Visual Hex Map Display** - See your generated map with proper hex shapes
- ✅ **Color-Coded Terrains** - Each biome has its distinct color
- ✅ **Interactive Interface** - Hover and click on hexes for details
- ✅ **Scrollable Canvas** - Navigate large maps easily
- ✅ **Terrain Legend** - Visual guide showing all terrain types
- ✅ **Real-time Generation** - Generate maps from 5x5 up to 100x100

### **Interactive Features:**
- 🖱️ **Mouse Hover** - Shows hex position and terrain in tooltip
- 🖱️ **Click Details** - Click any hex to see full coordinate information
- 📊 **Statistics Panel** - Real-time terrain distribution and percentages
- 🎲 **Seed Control** - Set specific seeds or randomize
- 💾 **Export Options** - Save as JSON or copy directly to game

### **Visual Elements:**
- 🟦 **Water** - Blue hexes (~)
- 🟢 **Forest** - Green hexes (T)
- 🟫 **Hills** - Brown hexes (h)
- 🏔️ **Mountains** - Gray hexes (^)
- 🟡 **Desert** - Tan hexes (S)
- 🟣 **Swamp** - Dark teal hexes (M)
- ❄️ **Tundra** - Light blue hexes (I)
- 🟩 **Plains** - Light green hexes (.)

### **Usage Instructions:**

#### **Generate a Map:**
1. Set desired **Width** and **Height** (5-100)
2. Enter a **Seed** or click "Random"
3. Click **"Generate Map"**
4. View the visual map on the right panel

#### **Explore the Map:**
- **Hover** over hexes to see terrain type and coordinates
- **Click** on any hex for detailed information popup
- **Scroll** to navigate large maps
- **Check the legend** to understand terrain colors

#### **Export Your Map:**
- **Save JSON** - Export to any location
- **Copy to Game** - Automatically saves to game's maps/ folder

### **Technical Details:**
- **Terrain Generation**: Uses Minecraft-style 6D biome system
- **Coordinate System**: Supports both offset and cube coordinates
- **Map Sizes**: 5x5 minimum, 100x100 maximum
- **File Format**: Compatible with main hex crawler game
- **Performance**: Optimized for smooth interaction

### **Available Tools:**

1. **`hex_map_generator_stable.py`** - **✅ MOST STABLE** - Reliable expandable world generator
   - Square chunks of 10x10 hexes for stability
   - Simple N, S, E, W expansion buttons
   - Guaranteed to work without crashes
   - Best for creating expandable worlds reliably
   
2. **`hex_map_generator_pygame.py`** - **🎮 RECOMMENDED** - High-performance Pygame version with hexagonal maps
   - **Hexagonal map generation** - Natural, organic world shapes
   - **Radius-based sizing** - Maps grow from center outward (radius 3-50)
   - **Minecraft biome system** - Authentic 6D terrain generation
   - **Smooth navigation** - 60 FPS zooming and panning
   - **Cube coordinate display** - Shows proper hex coordinates
   
3. **`hex_map_generator_simple.py`** - Basic tkinter GUI with visual preview
4. **`hex_map_generator_reliable.py`** - Command-line version (up to 200x200)
5. **`hex_map_generator_cli.py`** - Full CLI features (up to 500x500)

### **Example Workflow:**
```bash
# Launch the visual generator
python hex_map_generator_simple.py

# Generate a 30x30 world with seed 12345
# Explore the visual map by hovering and clicking
# Export directly to your game for immediate play
```

The visual map generator provides the best experience for previewing and understanding your generated hex worlds before using them in the main game!