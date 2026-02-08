"""
Script to test the trained RL agent in isolation.
Loads the model and runs it, printing actions to console.
"""
import sys
import os
import time
import numpy as np
from pathlib import Path

# Add python_ai to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_layer.pyboy_client import PyBoyClient, GameBoyButton
from rl_layer.pokemon_agent import PokemonEnvironment, PokemonRLAgent

ROM_PATH = "roms/pokemon_red.gb"
STATE_PATH = "roms/pokemon_red.gb.state"
MODEL_PATH = "models/pokemon_ppo.zip"

def main():
    print(f"Loading ROM: {ROM_PATH}")
    client = PyBoyClient(ROM_PATH, headless=False, speed=1)
    client.start()
    
    if os.path.exists(STATE_PATH):
        print(f"Loading state: {STATE_PATH}")
        client.load_state(STATE_PATH)
    else:
        print("No save state found! Agent might be confused.")

    print("Initializing Agent...")
    env = PokemonEnvironment(client, frame_skip=4, use_screen=False)
    agent = PokemonRLAgent(env, model_path=MODEL_PATH)
    
    if not agent.initialize():
        print("Failed to load model!")
        return

    print("Agent loaded. Starting loop...")
    print("Press Ctrl+C to stop.")
    
    try:
        frame_count = 0
        while True:
            # Emulate
            client.tick(1)
            frame_count += 1
            
            # Action every 12 frames
            if frame_count % 12 == 0:
                obs = env._get_observation()
                action = agent.predict(obs, deterministic=False)
                
                action_name = "NOOP"
                if action > 0:
                    btn = list(GameBoyButton)[action] # This map might be offset, let's use the explicit map
                    # 1:A, 2:B, 3:START, 4:SELECT, 5:UP, 6:DOWN, 7:LEFT, 8:RIGHT
                    names = ["NOOP", "A", "B", "START", "SELECT", "UP", "DOWN", "LEFT", "RIGHT"]
                    action_name = names[action]
                    
                    # Execute
                    # Simple press for test (blocking is fine here to debugging)
                    client.press_button(getattr(GameBoyButton, action_name), frames=4)
                
                print(f"Step {frame_count}: Action {action} ({action_name}) - HP: {obs[0]*100:.1f}%")
                
    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()

if __name__ == "__main__":
    main()
