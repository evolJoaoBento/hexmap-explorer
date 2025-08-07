"""
File operation utilities for saving and loading hex maps
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import time
from typing import Optional


def save_map_dialog(hex_map) -> bool:
    """Show save dialog and save map to JSON file"""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    filename = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Save Hex Map"
    )
    
    if filename:
        try:
            hex_map.save_to_json(filename)
            root.destroy()
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save map:\n{e}")
            root.destroy()
            return False
    
    root.destroy()
    return False


def load_map_dialog(hex_map) -> bool:
    """Show load dialog and load map from JSON file"""
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    filename = filedialog.askopenfilename(
        filetypes=[("JSON files", "*.json")],
        title="Load Hex Map"
    )
    
    if filename:
        try:
            hex_map.load_from_json(filename)
            root.destroy()
            return True
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load map:\n{e}")
            root.destroy()
            return False
    
    root.destroy()
    return False


def quick_save_dialog(hex_map) -> Optional[str]:
    """Show quick save dialog for returning to menu"""
    result = messagebox.askyesnocancel(
        "Return to Menu",
        "Do you want to save your game before returning to the menu?"
    )
    
    if result is True:  # Yes - save and return
        root = tk.Tk()
        root.withdraw()
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"quicksave_{time.strftime('%Y%m%d_%H%M%S')}.json",
            title="Quick Save"
        )
        
        if filename:
            try:
                hex_map.save_to_json(filename)
                root.destroy()
                return "save_and_return"
            except Exception as e:
                messagebox.showerror("Save Error", f"Save failed: {e}")
                root.destroy()
                return None
        
        root.destroy()
        return None
        
    elif result is False:  # No - return without saving
        return "return_without_save"
    else:  # Cancel
        return None


def confirm_dialog(title: str, message: str) -> bool:
    """Show confirmation dialog"""
    return messagebox.askyesno(title, message)


def show_error(title: str, message: str):
    """Show error dialog"""
    messagebox.showerror(title, message)


def show_info(title: str, message: str):
    """Show info dialog"""
    messagebox.showinfo(title, message)
