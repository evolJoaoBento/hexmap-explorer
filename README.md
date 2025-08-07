# Hex Map Explorer

A modular D&D 5e-compatible hex-based exploration tool with AI-generated descriptions, dynamic travel system, and rich visualization features.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/pygame-2.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## Features

### Core Functionality
- **Hex-based exploration** - Navigate through a procedurally generated hex map
- **D&D 5e travel rules** - Authentic movement mechanics with normal/slow/fast pace
- **AI-powered descriptions** - Dynamic location descriptions using Ollama LLM
- **Pixel art visualization** - Beautiful animated sprites for all terrain types
- **Save/Load system** - Persistent game state with JSON save files
- **Party management** - Track party composition and member conditions
- **Transportation modes** - Horses, boats, airships, and more
- **Day/Night cycle** - Visual time progression with lighting effects

### Terrain Types
- **Forest** - Dense woodlands with difficult terrain
- **Mountains** - Impassable peaks requiring detours
- **Ocean** - Water hexes requiring boats or flight
- **Plains** - Open grasslands with easy movement
- **Desert** - Sandy expanses with harsh conditions
- **Swamp** - Wetlands with very difficult terrain
- **Tundra** - Frozen wastelands
- **Volcanic** - Dangerous lava fields
- **Cities** - Settlements and urban areas
- **Roads** - Improved travel paths

## Prerequisites

- **Python 3.8+**
- **Pygame 2.0+**
- **Pillow (PIL)**
- **Requests**
- **Ollama** (optional, for AI descriptions)

## Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/hexcrawl.git
cd hexcrawl
```

### Step 2: Install Python Dependencies
```bash
# Core dependencies
pip install pygame pillow requests

# Optional: For building standalone executable
pip install pyinstaller
```

### Step 3: Install Ollama (Optional, for AI Descriptions)
1. Download Ollama from [https://ollama.ai](https://ollama.ai)
2. Install and run Ollama
3. Pull the recommended model:
```bash
ollama pull qwen2.5:3b
```
4. Start Ollama server:
```bash
ollama serve
```

> **Note:** The application works without Ollama, using fallback descriptions instead.

## Quick Start

### Option 1: Run with Main Menu (Recommended)
```bash
python main_menu.py
```

### Option 2: Direct Launch
```bash
python main.py
```

### Option 3: Create Standalone Executable
```bash
# Windows
pyinstaller --onefile --windowed --icon=hex_explorer.ico main_menu.py

# macOS/Linux
pyinstaller --onefile --windowed main_menu.py
```

The executable will be created in the `dist/` folder.

## Controls

### Movement & Navigation
- **Click hex** - Move to adjacent hex (costs movement points)
- **Arrow keys** - Pan the map view
- **Mouse wheel** - Zoom in/out
- **Space** - Center view on party

### Actions
- **R** - Rest (reveals 2-hex radius, restores movement)
- **P** - Change pace (slow/normal/fast)
- **F** - Forced march (risk exhaustion)
- **T** - Transportation menu
- **Y** - Party composition
- **G** - Toggle hex grid
- **H** - Toggle UI panels
- **Escape** - Menu/Options

### File Operations
- **Ctrl+S** - Save game
- **Ctrl+L** - Load game
- **Ctrl+N** - New map

## Project Structure

```
hexcrawl/
├── main.py                   # Direct entry point
├── main_menu.py              # Menu entry point
├── config/
│   ├── constants.py          # Game constants and settings
│   └── __init__.py
├── core/
│   ├── hex.py                # Hex data structures
│   ├── map.py                # Map management
│   └── __init__.py
├── travel/
│   ├── system.py             # Travel mechanics
│   └── __init__.py
├── generation/
│   ├── ollama_client.py      # AI client
│   ├── manager.py            # Generation queue
│   └── __init__.py
├── rendering/
│   ├── renderer.py           # Main renderer
│   ├── sprites.py            # Pixel art generator
│   ├── ui.py                 # UI components
│   └── __init__.py
├── application/
│   ├── explorer.py           # Main application
│   └── __init__.py
├── utils/
│   ├── file_operations.py    # Save/load
│   └── __init__.py
└── maps/                     # Pre-made maps
    └── islands.json          # Example map
```

## Configuration

### Ollama Settings
Edit `config/constants.py` to change:
- `OLLAMA_DEFAULT_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_DEFAULT_MODEL`: LLM model to use (default: qwen2.5:3b)
- `GENERATION_TIMEOUT`: API timeout in seconds

### Game Settings
Modify in `config/constants.py`:
- `HEX_SIZE`: Size of hex tiles
- `NORMAL_PACE`: Hexes per day at normal pace
- `VISION_RANGE`: Visibility radius
- `UI_COLORS`: Interface color scheme

## Troubleshooting

### "Module not found" Errors
- Ensure all `__init__.py` files exist in module directories
- Run from the project root directory
- Check Python path includes the project directory

### Ollama Not Working
1. Verify Ollama is running: `ollama list`
2. Check the URL in settings matches your Ollama server
3. Ensure the model is installed: `ollama pull qwen2.5:3b`
4. Test connection: `curl http://localhost:11434/api/tags`

### Save Files Not Loading
- Verify the save file contains valid JSON
- Check file permissions
- Ensure the save file has a "hexes" field

### Performance Issues
- Reduce `CHUNK_SIZE` in constants.py
- Disable animations in sprites.py
- Lower `MAX_CONCURRENT_GENERATIONS`

## Game Mechanics

### Movement System
- **Normal Pace**: 8 hexes/day (24 miles)
- **Slow Pace**: 6 hexes/day (18 miles) - Allows stealth
- **Fast Pace**: 10 hexes/day (30 miles) - -5 to passive Perception

### Terrain Movement Costs
| Terrain | Movement Cost | Special |
|---------|--------------|---------|
| Plains | 1.0x | Normal movement |
| Forest | 1.5x | Difficult terrain |
| Swamp | 2.0x | Very difficult |
| Desert | 1.5x | Extreme heat |
| Mountains | Impassable | Requires detour |
| Ocean | Impassable | Requires boat/flight |
| Road | 0.75x | Faster travel |

### Transportation Modes
| Mode | Speed Modifier | Terrain Access |
|------|---------------|----------------|
| On Foot | 1.0x | Standard |
| Horse | 1.5x | No mountains/ocean |
| Boat | 1.0x | Water only |
| Airship | 2.0x | All terrain |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- D&D 5e travel rules by Wizards of the Coast
- Pygame community for the excellent game framework
- Ollama for local LLM capabilities
- Pixel art inspired by classic RPGs

## Resources

- [D&D 5e Travel Rules](https://www.dndbeyond.com/sources/basic-rules/adventuring#Travel)
- [Pygame Documentation](https://www.pygame.org/docs/)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [Hex Grid Math](https://www.redblobgames.com/grids/hexagons/)

## Roadmap

- [ ] Encounter system with combat
- [ ] Weather effects on travel
- [ ] NPC settlements and trading
- [ ] Quest system
- [ ] Multiplayer support
- [ ] Mobile companion app
- [ ] Custom terrain editor
- [ ] Mod support

---

**Made for D&D adventurers everywhere**

Run `python main_menu.py` to start your adventure!