"""
Training script for Pokemon Red RL agent.
Uses PPO via stable-baselines3.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from game_layer.pyboy_client import PyBoyClient
from rl_layer.pokemon_agent import PokemonEnvironment, PokemonRLAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def create_gym_env(pyboy_client, frame_skip: int = 4):
    """Create a Gymnasium-compatible environment."""
    import gymnasium as gym
    from gymnasium import spaces
    import numpy as np
    
    env = PokemonEnvironment(
        pyboy_client=pyboy_client,
        frame_skip=frame_skip,
        use_screen=False  # Use RAM features for faster training
    )
    
    class PokemonGymEnv(gym.Env):
        def __init__(self):
            super().__init__()
            self.env = env
            self.observation_space = spaces.Box(
                low=0, high=1,
                shape=(10,),
                dtype=np.float32
            )
            self.action_space = spaces.Discrete(9)
        
        def reset(self, seed=None, options=None):
            obs = self.env.reset()
            return obs, {}
        
        def step(self, action):
            obs, reward, done, info = self.env.step(action)
            return obs, reward, done, False, info
        
        def render(self):
            pass
    
    return PokemonGymEnv()


def train(args):
    """Main training function."""
    logger.info(f"Starting training with {args.timesteps} timesteps")
    logger.info(f"ROM: {args.rom}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Headless: {args.headless}")
    logger.info(f"Speed: {args.speed}")
    
    # Create output directories
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Initialize PyBoy
    logger.info("Initializing PyBoy...")
    pyboy_client = PyBoyClient(
        rom_path=args.rom,
        headless=args.headless,
        speed=args.speed,
        sound=False
    )
    
    if not pyboy_client.start():
        logger.error("Failed to start PyBoy")
        return False
    
    # Load save state if available
    state_path = args.rom + ".state"
    if os.path.exists(state_path) and args.use_state:
        logger.info(f"Loading save state: {state_path}")
        pyboy_client.load_state(state_path)
    
    # Create Gym environment
    logger.info("Creating Gymnasium environment...")
    gym_env = create_gym_env(pyboy_client, frame_skip=args.frame_skip)
    
    # Initialize or load model
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
        
        if args.load and os.path.exists(args.load):
            logger.info(f"Loading existing model: {args.load}")
            model = PPO.load(args.load, env=gym_env, device=args.device)
        else:
            logger.info("Creating new PPO model...")
            model = PPO(
                "MlpPolicy",
                gym_env,
                learning_rate=3e-4,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                verbose=1,
                tensorboard_log=str(log_dir),
                device=args.device
            )
        
        # Setup callbacks
        checkpoint_callback = CheckpointCallback(
            save_freq=args.save_freq,
            save_path=str(checkpoint_dir),
            name_prefix="pokemon_ppo"
        )
        
        # Train
        logger.info(f"Starting training for {args.timesteps} timesteps...")
        model.learn(
            total_timesteps=args.timesteps,
            callback=checkpoint_callback,
            progress_bar=False
        )
        
        # Save final model
        model.save(args.output)
        logger.info(f"Model saved to: {args.output}")
        
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.error("Install with: pip install stable-baselines3[extra]")
        return False
    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        return False
    finally:
        pyboy_client.stop()
        logger.info("PyBoy stopped")


def main():
    parser = argparse.ArgumentParser(description="Train Pokemon Red RL Agent")
    
    parser.add_argument(
        "--rom",
        type=str,
        default="roms/pokemon_red.gb",
        help="Path to Pokemon ROM"
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=100000,
        help="Total training timesteps"
    )
    parser.add_argument(
        "--save-freq",
        type=int,
        default=10000,
        help="Checkpoint save frequency (steps)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/pokemon_ppo.zip",
        help="Output model path"
    )
    parser.add_argument(
        "--load",
        type=str,
        default=None,
        help="Load existing model to continue training"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without display window"
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=0,
        help="Emulator speed (0 = max speed)"
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=4,
        help="Frames to skip between actions"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device for training (auto, cuda, cpu)"
    )
    parser.add_argument(
        "--use-state",
        action="store_true",
        default=True,
        help="Load .state file if available"
    )
    
    args = parser.parse_args()
    
    success = train(args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
