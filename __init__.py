# config/__init__.py
"""Configuration module for Hex Map Explorer"""

# core/__init__.py  
"""Core data structures and logic"""
from .hex import Hex, HexCoordinates
from .map import HexMap

__all__ = ['Hex', 'HexCoordinates', 'HexMap']

# travel/__init__.py
"""Travel system and transportation"""
from .system import TravelSystem

__all__ = ['TravelSystem']

# generation/__init__.py
"""AI description generation system"""
from .ollama_client import OllamaClient
from .manager import GenerationManager

__all__ = ['OllamaClient', 'GenerationManager']

# rendering/__init__.py
"""Rendering and UI components"""
from .sprites import PixelArtSprites
from .renderer import HexMapRenderer
from .ui import (
    draw_travel_ui, draw_transport_menu, draw_party_menu,
    draw_loading_animation, draw_message, draw_menu_button
)

__all__ = [
    'PixelArtSprites', 'HexMapRenderer',
    'draw_travel_ui', 'draw_transport_menu', 'draw_party_menu',
    'draw_loading_animation', 'draw_message', 'draw_menu_button'
]

# application/__init__.py
"""Main application logic"""
from .explorer import HexMapExplorer

__all__ = ['HexMapExplorer']

# utils/__init__.py
"""Utility functions and helpers"""
from .file_operations import (
    save_map_dialog, load_map_dialog, quick_save_dialog,
    confirm_dialog, show_error, show_info
)

__all__ = [
    'save_map_dialog', 'load_map_dialog', 'quick_save_dialog',
    'confirm_dialog', 'show_error', 'show_info'
]