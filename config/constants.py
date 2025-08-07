"""
Configuration constants for Hex Map Explorer
"""

# Hex terrain types with movement costs (basic version only)
TERRAIN_TYPES = {
    "forest": {"color": (34, 139, 34), "description": "Dense woodland", "movement_cost": 1.5},
    "plains": {"color": (144, 238, 144), "description": "Open grasslands", "movement_cost": 1},
    "mountains": {"color": (139, 137, 137), "description": "Rocky peaks", "movement_cost": 3},
    "water": {"color": (65, 105, 225), "description": "Deep waters", "movement_cost": 999},
    "desert": {"color": (238, 203, 173), "description": "Sandy dunes", "movement_cost": 2},
    "swamp": {"color": (47, 79, 79), "description": "Murky wetlands", "movement_cost": 3},
    "tundra": {"color": (176, 224, 230), "description": "Frozen wasteland", "movement_cost": 2},
    "hills": {"color": (160, 82, 45), "description": "Rolling hills", "movement_cost": 1.5}
}

# Travel pace settings (3-mile hexes)
TRAVEL_PACE = {
    "slow": {"hexes_per_8h": 6, "name": "Slow", "exhaustion_free_hours": 8},
    "normal": {"hexes_per_8h": 8, "name": "Normal", "exhaustion_free_hours": 8},
    "fast": {"hexes_per_8h": 10, "name": "Fast", "exhaustion_free_hours": 8}
}

# Transportation modes with their properties
TRANSPORTATION_MODES = {
    "on_foot": {
        "name": "On Foot",
        "icon": "👟",
        "base_hexes_per_8h": {"slow": 6, "normal": 8, "fast": 10},
        "terrain_modifiers": {
            "forest": 1.0, "plains": 1.0, "mountains": 1.0, "water": 999,
            "desert": 1.0, "swamp": 1.0, "tundra": 1.0, "hills": 1.0
        },
        "exhaustion_resistant": False,
        "requires_rest": True,
        "description": "Standard travel by foot"
    },
    "horse": {
        "name": "Horse",
        "icon": "🐴",
        "base_hexes_per_8h": {"slow": 9, "normal": 12, "fast": 15},
        "terrain_modifiers": {
            "forest": 1.2, "plains": 0.8, "mountains": 1.5, "water": 999,
            "desert": 1.1, "swamp": 2.0, "tundra": 1.2, "hills": 0.9
        },
        "exhaustion_resistant": True,
        "requires_rest": True,
        "description": "Mounted on horseback - faster on open terrain"
    },
    "boat": {
        "name": "Boat/Ship",
        "icon": "⛵",
        "base_hexes_per_8h": {"slow": 8, "normal": 12, "fast": 16},
        "terrain_modifiers": {
            "forest": 999, "plains": 999, "mountains": 999, "water": 0.5,
            "desert": 999, "swamp": 2.0, "tundra": 999, "hills": 999
        },
        "exhaustion_resistant": True,
        "requires_rest": False,
        "description": "Water travel - can only traverse water and swamps"
    },
    "airship": {
        "name": "Airship",
        "icon": "🎈",
        "base_hexes_per_8h": {"slow": 12, "normal": 20, "fast": 28},
        "terrain_modifiers": {
            "forest": 0.8, "plains": 0.8, "mountains": 1.0, "water": 0.8,
            "desert": 0.9, "swamp": 0.8, "tundra": 1.1, "hills": 0.85
        },
        "exhaustion_resistant": True,
        "requires_rest": False,
        "description": "Magical flight - ignores most terrain obstacles"
    }
}


# UI Constants
DEFAULT_WINDOW_SIZE = (1024, 768)
MIN_HEX_SIZE = 20
MAX_HEX_SIZE = 40
DEFAULT_HEX_SIZE_RATIO = 0.04

# Colors
UI_COLORS = {
    "background": (30, 30, 30),
    "panel_bg": (40, 40, 40),
    "panel_border": (100, 100, 100),
    "text_primary": (255, 255, 255),
    "text_secondary": (200, 200, 200),
    "text_success": (0, 255, 0),
    "text_warning": (255, 255, 0),
    "text_error": (255, 0, 0),
    "button_normal": (60, 60, 80),
    "button_hover": (80, 80, 120),
    "button_selected": (80, 80, 120)
}

# Generation settings
OLLAMA_DEFAULT_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "qwen2.5:3b"
GENERATION_TIMEOUT = 10
DESCRIPTION_CACHE_SIZE = 1000
