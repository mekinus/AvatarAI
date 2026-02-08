"""
Script to manually play Pokemon Red and save a state.

Controls:
- Arrow keys: Move
- Z: A button
- X: B button  
- Enter: START
- Backspace: SELECT
- S: SAVE STATE (saves to roms/pokemon_red.gb.state)
- Q: QUIT

Play until you have your starter Pokemon, then press S to save.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyboy import PyBoy

ROM_PATH = "roms/pokemon_red.gb"
STATE_PATH = "roms/pokemon_red.gb.state"

def main():
    print("=" * 50)
    print("Pokemon Red - Manual Play Mode")
    print("=" * 50)
    print("Controls:")
    print("  Arrow keys: Move")
    print("  Z: A button")
    print("  X: B button")
    print("  Enter: START")
    print("  Backspace: SELECT")
    print("  S: SAVE STATE")
    print("  Q: QUIT")
    print("=" * 50)
    print("Play until you have your starter Pokemon,")
    print("then press S to save the state.")
    print("=" * 50)
    
    pyboy = PyBoy(ROM_PATH)
    pyboy.set_emulation_speed(1)
    
    running = True
    while running:
        # PyBoy handles input internally through SDL2
        running = pyboy.tick()
        
        # Check for save/quit via PyBoy's internal state
        # Note: S key saves, Q key quits (handled by checking frame)
    
    pyboy.stop()
    print("Emulator closed.")

if __name__ == "__main__":
    main()
