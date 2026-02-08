"""
Agente de Reinforcement Learning para jogar Pokémon.
Usa PPO (Proximal Policy Optimization) via stable-baselines3.
"""

import logging
import os
from typing import Optional, Dict, Any, Tuple, List
from enum import IntEnum
import numpy as np

logger = logging.getLogger(__name__)


class PokemonAction(IntEnum):
    """Ações disponíveis no Game Boy."""
    NOOP = 0
    A = 1
    B = 2
    START = 3
    SELECT = 4
    UP = 5
    DOWN = 6
    LEFT = 7
    RIGHT = 8


class PokemonEnvironment:
    """
    Ambiente Gymnasium para Pokémon Red/Blue.
    Wrapper do PyBoy para uso com stable-baselines3.
    """
    
    def __init__(
        self,
        pyboy_client,
        frame_skip: int = 4,
        use_screen: bool = False
    ):
        """
        Args:
            pyboy_client: Instância de PyBoyClient
            frame_skip: Frames para pular entre ações
            use_screen: Se True, observação inclui frame da tela
        """
        self.pyboy = pyboy_client
        self.frame_skip = frame_skip
        self.use_screen = use_screen
        
        # Espaço de ações: 9 (noop + 8 botões)
        self.n_actions = 9
        
        # Estado anterior para calcular reward
        self.prev_state: Dict[str, Any] = {}
        self.episode_steps = 0
        self.max_steps = 10000
        
        # Tracking de progresso
        self.visited_positions = set()
        self.total_xp = 0
        self.battles_won = 0
        
        logger.info(f"PokemonEnvironment criado (frame_skip={frame_skip})")
    
    @property
    def observation_space_shape(self) -> Tuple[int, ...]:
        """Forma do espaço de observação."""
        if self.use_screen:
            return (144, 160, 3)  # Game Boy screen
        return (10,)  # RAM features
    
    @property
    def action_space_n(self) -> int:
        """Número de ações."""
        return self.n_actions
    
    def reset(self) -> np.ndarray:
        """Reseta o ambiente."""
        self.episode_steps = 0
        self.visited_positions = set()
        self.total_xp = 0
        self.battles_won = 0
        
        # Pega estado inicial
        self.prev_state = self.pyboy.get_pokemon_state()
        
        return self._get_observation()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Executa uma ação no ambiente.
        
        Args:
            action: Índice da ação (0-8)
        
        Returns:
            (observation, reward, done, info)
        """
        # Executa ação
        self._execute_action(action)
        
        # Avança frames
        self.pyboy.tick(self.frame_skip)
        
        # Pega novo estado
        new_state = self.pyboy.get_pokemon_state()
        
        # Calcula reward
        reward = self._calculate_reward(new_state)
        
        # Verifica se terminou
        self.episode_steps += 1
        done = self._check_done(new_state)
        
        # Info adicional
        info = {
            "steps": self.episode_steps,
            "hp": new_state.get("hp_percent", 100),
            "level": new_state.get("party_level", 0),
            "in_battle": new_state.get("in_battle", False),
            "badges": new_state.get("badges", 0),
        }
        
        # Atualiza estado anterior
        self.prev_state = new_state
        
        return self._get_observation(), reward, done, info
    
    def _execute_action(self, action: int):
        """Executa ação no emulador."""
        try:
            from game_layer.pyboy_client import GameBoyButton
        except ImportError:
            from ..game_layer.pyboy_client import GameBoyButton
        
        action_map = {
            PokemonAction.NOOP: None,
            PokemonAction.A: GameBoyButton.A,
            PokemonAction.B: GameBoyButton.B,
            PokemonAction.START: GameBoyButton.START,
            PokemonAction.SELECT: GameBoyButton.SELECT,
            PokemonAction.UP: GameBoyButton.UP,
            PokemonAction.DOWN: GameBoyButton.DOWN,
            PokemonAction.LEFT: GameBoyButton.LEFT,
            PokemonAction.RIGHT: GameBoyButton.RIGHT,
        }
        
        button = action_map.get(PokemonAction(action))
        if button is not None:
            self.pyboy.press_button(button, frames=8)
    
    def _get_observation(self) -> np.ndarray:
        """Retorna observação atual."""
        if self.use_screen:
            frame = self.pyboy.get_frame()
            if frame is not None:
                return frame.astype(np.float32) / 255.0
            return np.zeros((144, 160, 3), dtype=np.float32)
        
        # Observação baseada em RAM
        state = self.pyboy.get_pokemon_state()
        
        obs = np.array([
            state.get("hp_percent", 100) / 100.0,
            state.get("party_level", 5) / 100.0,
            state.get("in_battle", False) * 1.0,
            state.get("enemy_hp", 0) / 100.0 if state.get("in_battle") else 0,
            state.get("player_x", 0) / 255.0,
            state.get("player_y", 0) / 255.0,
            state.get("map_id", 0) / 255.0,
            state.get("badges", 0) / 8.0,
            state.get("text_box_open", False) * 1.0,
            state.get("menu_open", False) * 1.0,
        ], dtype=np.float32)
        
        return obs
    
    def _calculate_reward(self, new_state: Dict) -> float:
        """
        Calcula reward baseado na mudança de estado.
        
        Reward shaping para Pokémon:
        - XP gain: +
        - Level up: ++
        - Badge: +++
        - New area: +
        - HP loss: -
        - Fainted: ---
        """
        reward = 0.0
        
        # Level up
        new_level = new_state.get("party_level", 0)
        old_level = self.prev_state.get("party_level", 0)
        if new_level > old_level:
            reward += 10.0 * (new_level - old_level)
            logger.debug(f"Level up! +{10.0 * (new_level - old_level)} reward")
        
        # Badge
        new_badges = new_state.get("badges", 0)
        old_badges = self.prev_state.get("badges", 0)
        if new_badges > old_badges:
            reward += 100.0
            logger.debug("Badge obtained! +100 reward")
        
        # HP management
        new_hp = new_state.get("hp_percent", 100)
        old_hp = self.prev_state.get("hp_percent", 100)
        
        if new_hp < old_hp:
            # Penalidade por perder HP
            reward -= (old_hp - new_hp) * 0.1
        elif new_hp > old_hp:
            # Bonus por curar
            reward += 1.0
        
        # Fainted (HP = 0)
        if new_hp == 0 and old_hp > 0:
            reward -= 20.0
            logger.debug("Pokemon fainted! -20 reward")
        
        # Exploração
        position = (
            new_state.get("player_x", 0),
            new_state.get("player_y", 0),
            new_state.get("map_id", 0)
        )
        
        if position not in self.visited_positions:
            self.visited_positions.add(position)
            reward += 1.0  # Increased bonus for exploration (was 0.01)
            
        # Stuck Penalty (hitting wall)
        # Se não moveu e não está em batalha/texto/menu, penaliza
        prev_position = (
            self.prev_state.get("player_x", 0),
            self.prev_state.get("player_y", 0),
            self.prev_state.get("map_id", 0)
        )
        
        is_busy = (
            new_state.get("in_battle", False) or 
            new_state.get("text_box_open", False) or 
            new_state.get("menu_open", False)
        )
        
        if position == prev_position and not is_busy:
            reward -= 0.1  # Penalidade por ficar parado/bater na parede
        
        # Battle won
        was_in_battle = self.prev_state.get("in_battle", False)
        is_in_battle = new_state.get("in_battle", False)
        
        if was_in_battle and not is_in_battle:
            # Batalha terminou
            if new_state.get("hp_percent", 0) > 0:
                # Provavelmente venceu
                reward += 5.0
                self.battles_won += 1
        
        # Penalidade por ficar parado
        if position == self.prev_state.get("position"):
            reward -= 0.01
        
        return reward
    
    def _check_done(self, state: Dict) -> bool:
        """Verifica se episódio terminou."""
        # Max steps
        if self.episode_steps >= self.max_steps:
            return True
        
        # Todos Pokémon fainted (game over)
        if state.get("party_count", 1) > 0 and state.get("hp_percent", 100) == 0:
            # Verifica se todos estão fainted
            # Simplificação: se HP do primeiro é 0, considera done
            return True
        
        return False


class PokemonRLAgent:
    """
    Agente RL usando PPO para jogar Pokémon.
    """
    
    def __init__(
        self,
        env: PokemonEnvironment,
        model_path: Optional[str] = None,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        device: str = "auto"
    ):
        """
        Args:
            env: Ambiente de Pokémon
            model_path: Caminho para modelo salvo (opcional)
            learning_rate: Taxa de aprendizado
            n_steps: Steps por update
            batch_size: Tamanho do batch
            n_epochs: Épocas por update
            gamma: Fator de desconto
            device: "cuda", "cpu" ou "auto"
        """
        self.env = env
        self.model_path = model_path
        self.model = None
        self.device = device
        
        # Hiperparâmetros
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.gamma = gamma
        
        # Stats
        self.total_steps = 0
        self.episodes_completed = 0
        
        logger.info(f"PokemonRLAgent criado (device={device})")
    
    def initialize(self) -> bool:
        """Inicializa o modelo PPO."""
        try:
            from stable_baselines3 import PPO
            from stable_baselines3.common.vec_env import DummyVecEnv
            import gymnasium as gym
            
            # Cria wrapper Gymnasium
            gym_env = self._create_gym_env()
            
            if self.model_path and os.path.exists(self.model_path):
                # Carrega modelo existente
                logger.info(f"Carregando modelo: {self.model_path}")
                self.model = PPO.load(self.model_path, env=gym_env)
            else:
                # Cria novo modelo
                logger.info("Criando novo modelo PPO")
                self.model = PPO(
                    "MlpPolicy" if not self.env.use_screen else "CnnPolicy",
                    gym_env,
                    learning_rate=self.learning_rate,
                    n_steps=self.n_steps,
                    batch_size=self.batch_size,
                    n_epochs=self.n_epochs,
                    gamma=self.gamma,
                    verbose=1,
                    device=self.device
                )
            
            return True
            
        except ImportError as e:
            logger.error(f"Dependências faltando: {e}")
            logger.error("Instale com: pip install stable-baselines3 gymnasium")
            return False
        except Exception as e:
            logger.error(f"Erro ao inicializar RL agent: {e}")
            return False
    
    def _create_gym_env(self):
        """Cria ambiente compatível com Gymnasium."""
        import gymnasium as gym
        from gymnasium import spaces
        
        class PokemonGymEnv(gym.Env):
            def __init__(inner_self):
                super().__init__()
                inner_self.env = self.env
                
                # Define spaces
                if self.env.use_screen:
                    inner_self.observation_space = spaces.Box(
                        low=0, high=1,
                        shape=(144, 160, 3),
                        dtype=np.float32
                    )
                else:
                    inner_self.observation_space = spaces.Box(
                        low=0, high=1,
                        shape=(10,),
                        dtype=np.float32
                    )
                
                inner_self.action_space = spaces.Discrete(9)
            
            def reset(inner_self, seed=None, options=None):
                obs = inner_self.env.reset()
                return obs, {}
            
            def step(inner_self, action):
                obs, reward, done, info = inner_self.env.step(action)
                return obs, reward, done, False, info
            
            def render(inner_self):
                pass
        
        return PokemonGymEnv()
    
    def predict(self, observation: np.ndarray, deterministic: bool = False) -> int:
        """
        Prediz próxima ação.
        
        Args:
            observation: Observação atual
            deterministic: Se True, usa política determinística
        
        Returns:
            Índice da ação
        """

        if self.model is None:
            # Random action se modelo não inicializado
            action = np.random.randint(0, self.env.n_actions)

            return action
        
        action, _ = self.model.predict(observation, deterministic=deterministic)
        action_int = int(action)

        return action_int
    
    def train(self, total_timesteps: int = 100000, save_freq: int = 10000):
        """
        Treina o agente.
        
        Args:
            total_timesteps: Total de steps de treino
            save_freq: Frequência de save (em steps)
        """
        if self.model is None:
            logger.error("Modelo não inicializado")
            return
        
        from stable_baselines3.common.callbacks import CheckpointCallback
        
        # Callback para salvar checkpoints
        if self.model_path:
            checkpoint_callback = CheckpointCallback(
                save_freq=save_freq,
                save_path=os.path.dirname(self.model_path),
                name_prefix="pokemon_ppo"
            )
            callbacks = [checkpoint_callback]
        else:
            callbacks = []
        
        logger.info(f"Iniciando treino: {total_timesteps} timesteps")
        self.model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=True
        )
        
        # Salva modelo final
        if self.model_path:
            self.model.save(self.model_path)
            logger.info(f"Modelo salvo: {self.model_path}")
    
    def save(self, path: Optional[str] = None):
        """Salva o modelo."""
        save_path = path or self.model_path
        if self.model and save_path:
            self.model.save(save_path)
            logger.info(f"Modelo salvo: {save_path}")
    
    def load(self, path: str):
        """Carrega modelo salvo."""
        try:
            from stable_baselines3 import PPO
            
            gym_env = self._create_gym_env()
            self.model = PPO.load(path, env=gym_env)
            self.model_path = path
            logger.info(f"Modelo carregado: {path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            return False


class SimpleAgent:
    """
    Agente simples sem RL (regras básicas).
    Útil para testes ou quando não quer treinar.
    """
    
    def __init__(self, pyboy_client, vision_analyzer=None):
        self.pyboy = pyboy_client
        self.vision_analyzer = vision_analyzer
        self.action_queue: List[int] = []
        self.stuck_counter = 0
        self.last_position = None
        
    def predict(self, observation: np.ndarray = None, vision_analysis: dict = None) -> int:
        """
        Prediz ação usando regras simples.
        
        Args:
            observation: Observação (não usado)
            vision_analysis: Análise visual do frame (opcional)
        """
        state = self.pyboy.get_pokemon_state()
        
        # PRIORIDADE 1: Detectar menu inicial (title screen)
        # Se map_id = 0 e não está em batalha, provavelmente está no menu inicial
        if vision_analysis:
            screen_type = vision_analysis.get("screen_type")
            # Converte enum para string se necessário
            if hasattr(screen_type, 'value'):
                screen_type_str = screen_type.value
            else:
                screen_type_str = str(screen_type)
                
            if screen_type_str == "title":
                # Spam START/A no title screen para garantir que inicie
                # Alterna entre START e A para passar menus
                action = np.random.choice([PokemonAction.START, PokemonAction.A], p=[0.7, 0.3])
                return action
        
        # Se map_id = 0 e party_count = 0, provavelmente intro/title (fallback se vision falhar)
        if state.get("map_id", 0) == 0 and state.get("party_count", 0) == 0:
             # Spam START/A
            action = np.random.choice([PokemonAction.START, PokemonAction.A], p=[0.7, 0.3])
            return action
        
        # Se em batalha
        if state.get("in_battle", False):
            # HP crítico? Tenta fugir ou usar item
            if state.get("hp_percent", 100) < 20:
                action = PokemonAction.B  # Tenta fugir
                return action
            
            # Ataca
            action = PokemonAction.A
            return action
        
        # Se caixa de texto aberta (diálogo)
        if state.get("text_box_open"):
            action = PokemonAction.A  # Avança texto
            return action
            
        # Se menu aberto (e NÃO é texto, e NÃO está em batalha) -> fecha com B
        if state.get("menu_open"):
            action = PokemonAction.B  # Fecha menu / Volta
            return action
        
        # Exploração: movimento aleatório (mas com preferência para frente)
        # Se não mudou de posição em muitas ações, tenta outra direção
        current_pos = (state.get("player_x", 0), state.get("player_y", 0))
        if current_pos == self.last_position:
            self.stuck_counter += 1
            if self.stuck_counter > 5:
                # Tenta direção diferente
                action = np.random.choice([
                    PokemonAction.UP,
                    PokemonAction.DOWN,
                    PokemonAction.LEFT,
                    PokemonAction.RIGHT
                ])
                self.stuck_counter = 0
            else:
                # Continua na mesma direção
                action = PokemonAction.UP  # Preferência para cima
        else:
            self.stuck_counter = 0
            # Movimento aleatório normal
            action = np.random.choice([
                PokemonAction.UP,
                PokemonAction.DOWN,
                PokemonAction.LEFT,
                PokemonAction.RIGHT
            ])
        
        self.last_position = current_pos
        return action

