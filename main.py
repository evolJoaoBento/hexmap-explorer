#!/usr/bin/env python3
"""
Hex Map Explorer - Main Entry Point
A D&D 5e compatible hex-based exploration tool with AI-generated descriptions.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from application import HexMapExplorer


def main():
    """Main entry point for the application"""
    print("=" * 50)
    print("Hex Map Explorer - D&D 5e Travel System")
    print("=" * 50)
    print("\nTravel Rules:")
    print("- Normal pace: 8 hexes per day (3-mile hexes)")
    print("- Difficult terrain costs more movement")
    print("- Rest to restore movement and scout 2-hex radius")
    print("\nControls:")
    print("- R: Rest (reveals 2-hex radius)")
    print("- P: Change pace (slow/normal/fast)")
    print("- F: Forced march (risk exhaustion)")
    print("- T: Transportation menu")
    print("- Y: Party composition")
    print("-" * 50)
    
    try:
        explorer = HexMapExplorer()
        explorer.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())