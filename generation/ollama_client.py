"""
Ollama API client for description generation
"""
import requests
import random
from typing import Tuple
from config.constants import TERRAIN_TYPES, OLLAMA_DEFAULT_URL, OLLAMA_DEFAULT_MODEL, GENERATION_TIMEOUT


class OllamaClient:
    """Client for Ollama API with synchronous generation"""
    
    def __init__(self, base_url=OLLAMA_DEFAULT_URL):
        self.base_url = base_url
        self.model = OLLAMA_DEFAULT_MODEL
        self.description_cache = {}
        self.session = requests.Session()
        self.ollama_available = self.check_ollama()
    
    def check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except:
            print("Ollama not detected - using fallback descriptions")
            return False
    
    def generate(self, terrain: str, coords: Tuple[int, int]) -> str:
        """Generate description synchronously"""
        cache_key = f"{terrain}_{coords[0]}_{coords[1]}"
        
        if cache_key in self.description_cache:
            return self.description_cache[cache_key]
        
        if not self.ollama_available:
            return self.get_fallback_description(terrain)
        
        prompt = f"""Generate a brief, evocative description (2-3 sentences) for a hex tile in a fantasy map. 
        The terrain is: {terrain} ({TERRAIN_TYPES[terrain]['description']}).
        Location: hex coordinates ({coords[0]}, {coords[1]}).
        Make it atmospheric and hint at potential discoveries or dangers.
        Description:"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 50,
                        "temperature": 0.7,
                        "top_k": 30,
                        "top_p": 0.85
                    }
                },
                timeout=GENERATION_TIMEOUT
            )
            if response.status_code == 200:
                description = response.json().get("response", "").strip()
                if description:
                    self.description_cache[cache_key] = description
                    return description
        except Exception as e:
            print(f"Generation error: {e}")
            self.ollama_available = False
        
        return self.get_fallback_description(terrain)
    
    def get_fallback_description(self, terrain: str) -> str:
        """Fallback descriptions by terrain type"""
        fallbacks = {
            "forest": [
                "Ancient trees tower overhead, their branches creating a verdant canopy. The air is thick with the scent of moss and decay.",
                "The forest whispers with unseen life and hidden paths. Shadows dance between the massive trunks."
            ],
            "plains": [
                "Endless grasslands ripple in the wind like a golden sea. The horizon seems infinitely distant.",
                "The open plains stretch to the horizon under vast skies. Wild flowers dot the landscape."
            ],
            "mountains": [
                "Jagged peaks pierce the clouds, eternal and imposing. The air grows thin and cold.",
                "Rocky cliffs and steep paths challenge any traveler. Eagles circle overhead."
            ],
            "water": [
                "Deep waters reflect the sky, hiding depths unknown. Gentle waves lap at unseen shores.",
                "The water's surface conceals aquatic mysteries. Strange ripples disturb the calm."
            ],
            "desert": [
                "Sand dunes shift endlessly under the scorching sun. Mirages dance on the horizon.",
                "The desert's harsh beauty masks hidden oases. Wind-carved rocks create natural sculptures."
            ],
            "swamp": [
                "Murky waters and twisted trees create an eerie landscape. Strange bubbles rise from the depths.",
                "The swamp bubbles with mysterious life and decay. Fog drifts between gnarled roots."
            ],
            "tundra": [
                "Frozen wastes stretch endlessly, beautiful and desolate. The wind cuts like ice.",
                "Ice and snow dominate this harsh, unforgiving land. Aurora lights dance overhead."
            ],
            "hills": [
                "Rolling hills create a patchwork of light and shadow. Ancient paths wind between them.",
                "Gentle slopes hide valleys and ancient secrets. Wildflowers carpet the hillsides."
            ]
        }
        return random.choice(fallbacks.get(terrain, ["An unexplored region awaits discovery."]))
    
    def cleanup(self):
        """Cleanup session"""
        if self.session:
            self.session.close()
