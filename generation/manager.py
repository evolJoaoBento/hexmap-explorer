"""
Description generation management system
"""
import threading
import time
from typing import List, Tuple
from core.hex import Hex
from generation.ollama_client import OllamaClient


class GenerationManager:
    """Manages description generation with progress tracking"""
    
    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.generating = False
        self.progress = 0.0
        self.total_hexes = 0
        self.completed_hexes = 0
        self.current_hex_name = ""
        self.generation_thread = None
        self.hexes_to_generate = []
        self.cancel_generation = False
        self.generation_type = "scouting"
    
    def start_generation(self, hexes: List[Tuple[Hex, Tuple[int, int]]], gen_type: str = "scouting"):
        """Start generating descriptions for a list of hexes"""
        if self.generating:
            return
        
        self.hexes_to_generate = hexes
        self.total_hexes = len(hexes)
        self.completed_hexes = 0
        self.progress = 0.0
        self.generating = True
        self.cancel_generation = False
        self.generation_type = gen_type
        
        self.generation_thread = threading.Thread(target=self._generate_worker, daemon=True)
        self.generation_thread.start()
    
    def _generate_worker(self):
        """Worker thread for generation"""
        for hex_obj, coords in self.hexes_to_generate:
            if self.cancel_generation:
                break
            
            self.current_hex_name = f"{hex_obj.terrain} at ({hex_obj.q}, {hex_obj.r})"
            hex_obj.generating = True
            
            description = self.ollama.generate(hex_obj.terrain, coords)
            hex_obj.description = description
            hex_obj.generating = False
            
            self.completed_hexes += 1
            self.progress = self.completed_hexes / self.total_hexes
            
            # Small delay if using Ollama to avoid overwhelming it
            if self.ollama.ollama_available:
                time.sleep(0.1)
        
        self.generating = False
        self.progress = 1.0
    
    def cancel(self):
        """Cancel current generation"""
        self.cancel_generation = True
        if self.generation_thread:
            self.generation_thread.join(timeout=1)
        self.generating = False
    
    def is_generating(self) -> bool:
        """Check if currently generating"""
        return self.generating
    
    def get_progress(self) -> float:
        """Get generation progress (0.0 to 1.0)"""
        return self.progress
    
    def get_status(self) -> dict:
        """Get detailed status information"""
        return {
            "generating": self.generating,
            "progress": self.progress,
            "completed": self.completed_hexes,
            "total": self.total_hexes,
            "current_hex": self.current_hex_name,
            "type": self.generation_type
        }
