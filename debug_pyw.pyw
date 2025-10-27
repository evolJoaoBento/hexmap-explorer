import os
import sys
import traceback

try:
    # Fix working directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Add to path
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    print(f"Script dir: {script_dir}")
    print(f"Working dir: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}")
    
    # Try to import required modules
    print("Testing imports...")
    import pygame
    print("✅ pygame imported")
    
    import tkinter
    print("✅ tkinter imported")
    
    # Try to import your custom modules
    try:
        from application import HexMapExplorer
        print("✅ application module imported")
    except Exception as e:
        print(f"❌ application import failed: {e}")
    
    # Now run the actual main menu
    from main_menu import *
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    input("Press Enter to close...")
