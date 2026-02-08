"""
Cliente PyBoy para emulação de Game Boy.
Gerencia o emulador, acesso à RAM, frame buffer e inputs.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from enum import IntEnum
import numpy as np

logger = logging.getLogger(__name__)


class GameBoyButton(IntEnum):
    """Botões do Game Boy."""
    A = 0
    B = 1
    SELECT = 2
    START = 3
    RIGHT = 4
    LEFT = 5
    UP = 6
    DOWN = 7


# Endereços de memória do Pokémon Red/Blue
class PokemonMemoryAddresses:
    """Endereços de RAM do Pokémon Red/Blue."""
    # Party Pokemon
    PARTY_COUNT = 0xD163
    PARTY_SPECIES_1 = 0xD164
    PARTY_HP_1 = 0xD16C  # 2 bytes (current HP)
    PARTY_MAX_HP_1 = 0xD18D  # 2 bytes
    PARTY_LEVEL_1 = 0xD18C
    
    # Battle
    IN_BATTLE = 0xD057  # 0 = not in battle, 1+ = in battle
    ENEMY_HP = 0xCFE6  # 2 bytes
    ENEMY_LEVEL = 0xCFF3
    ENEMY_SPECIES = 0xCFE5
    
    # Player
    PLAYER_X = 0xD362
    PLAYER_Y = 0xD361
    MAP_ID = 0xD35E
    
    # Badges & Progress
    BADGES = 0xD356
    MONEY = 0xD347  # 3 bytes BCD
    
    # Menu/State
    TEXT_BOX_OPEN = 0xD125
    MENU_OPEN = 0xCC35


class PyBoyClient:
    """Cliente para emulador PyBoy."""
    
    def __init__(
        self,
        rom_path: str,
        headless: bool = False,
        speed: int = 1,
        sound: bool = False
    ):
        """
        Args:
            rom_path: Caminho para a ROM do jogo
            headless: Se True, roda sem janela
            speed: Velocidade do emulador (1 = normal)
            sound: Habilitar som
        """
        self.rom_path = rom_path
        self.headless = headless
        self.speed = speed
        self.sound = sound
        
        self.pyboy = None
        self.is_running = False
        
        logger.info(f"PyBoyClient inicializado (ROM: {rom_path}, headless: {headless})")
    
    def start(self) -> bool:
        """Inicia o emulador."""
        try:
            from pyboy import PyBoy
            
            window_type = "null" if self.headless else "SDL2"
            
            self.pyboy = PyBoy(
                self.rom_path,
                window=window_type,
                sound=self.sound,
                sound_emulated=self.sound
            )
            
            # Configura velocidade
            self.pyboy.set_emulation_speed(self.speed)
            
            self.is_running = True
            logger.info(f"PyBoy iniciado: {self.rom_path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"ROM não encontrada: {self.rom_path}")
            return False
        except ImportError:
            logger.error("PyBoy não instalado. Instale com: pip install pyboy")
            return False
        except Exception as e:
            logger.error(f"Erro ao iniciar PyBoy: {e}")
            return False
    
    def stop(self):
        """Para o emulador."""
        if self.pyboy:
            self.pyboy.stop()
            self.is_running = False
            logger.info("PyBoy parado")
    
    def tick(self, frames: int = 1) -> bool:
        """
        Avança o emulador por N frames.
        
        Args:
            frames: Número de frames para avançar
        
        Returns:
            True se ainda está rodando
        """
        if not self.pyboy or not self.is_running:
            return False
        
        for _ in range(frames):
            self.pyboy.tick()
        
        return self.is_running
    
    def press_button(self, button: GameBoyButton, frames: int = 8):
        """
        Pressiona um botão por N frames.
        
        Args:
            button: Botão a pressionar
            frames: Duração do press (8 frames ≈ 0.13s)
        """
        if not self.pyboy:
            return
        
        button_name = button.name.lower()
        self.pyboy.button(button_name)
        self.tick(frames)
        self.pyboy.button_release(button_name)
    
    def press_buttons(self, buttons: List[GameBoyButton], frames: int = 8):
        """Pressiona múltiplos botões simultaneamente."""
        if not self.pyboy:
            return
        
        for button in buttons:
            self.pyboy.button(button.name.lower())
        
        self.tick(frames)
        
        for button in buttons:
            self.pyboy.button_release(button.name.lower())
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Captura o frame atual da tela.
        
        Returns:
            Array numpy RGB (160x144x3) ou None
        """
        if not self.pyboy:
            return None
        
        try:
            # PyBoy retorna PIL Image
            screen = self.pyboy.screen.image
            return np.array(screen)
        except Exception as e:
            logger.error(f"Erro ao capturar frame: {e}")
            return None
    
    def read_memory(self, address: int, size: int = 1) -> int:
        """
        Lê valor da memória RAM.
        
        Args:
            address: Endereço de memória
            size: Tamanho em bytes (1 ou 2)
        
        Returns:
            Valor lido
        """
        if not self.pyboy:
            return 0
        
        try:
            if size == 1:
                return self.pyboy.memory[address]
            elif size == 2:
                # Little endian
                low = self.pyboy.memory[address]
                high = self.pyboy.memory[address + 1]
                return (high << 8) | low
            else:
                return self.pyboy.memory[address]
        except Exception as e:
            logger.error(f"Erro ao ler memória 0x{address:04X}: {e}")
            return 0
    
    def get_pokemon_state(self) -> Dict[str, Any]:
        """
        Lê o estado atual do jogo Pokémon.
        
        Returns:
            Dicionário com estado do jogo
        """
        if not self.pyboy:
            return {}
        
        addr = PokemonMemoryAddresses
        
        state = {
            # Party
            "party_count": self.read_memory(addr.PARTY_COUNT),
            "party_hp": self.read_memory(addr.PARTY_HP_1, 2),
            "party_max_hp": self.read_memory(addr.PARTY_MAX_HP_1, 2),
            "party_level": self.read_memory(addr.PARTY_LEVEL_1),
            "party_species": self.read_memory(addr.PARTY_SPECIES_1),
            
            # Battle
            "in_battle": self.read_memory(addr.IN_BATTLE) > 0,
            "enemy_hp": self.read_memory(addr.ENEMY_HP, 2),
            "enemy_level": self.read_memory(addr.ENEMY_LEVEL),
            "enemy_species": self.read_memory(addr.ENEMY_SPECIES),
            
            # Player
            "player_x": self.read_memory(addr.PLAYER_X),
            "player_y": self.read_memory(addr.PLAYER_Y),
            "map_id": self.read_memory(addr.MAP_ID),
            
            # Progress
            "badges": self.read_memory(addr.BADGES),
            
            # UI
            "text_box_open": self.read_memory(addr.TEXT_BOX_OPEN) > 0,
            "menu_open": self.read_memory(addr.MENU_OPEN) > 0,
        }
        
        # Calcula HP percentage
        if state["party_max_hp"] > 0:
            state["hp_percent"] = (state["party_hp"] / state["party_max_hp"]) * 100
        else:
            state["hp_percent"] = 100
        
        return state
    
    def get_hp_percent(self) -> float:
        """Retorna HP do primeiro Pokémon em porcentagem."""
        state = self.get_pokemon_state()
        return state.get("hp_percent", 100)
    
    def is_in_battle(self) -> bool:
        """Verifica se está em batalha."""
        return self.read_memory(PokemonMemoryAddresses.IN_BATTLE) > 0
    
    def get_position(self) -> Tuple[int, int, int]:
        """Retorna posição (x, y, map_id)."""
        addr = PokemonMemoryAddresses
        return (
            self.read_memory(addr.PLAYER_X),
            self.read_memory(addr.PLAYER_Y),
            self.read_memory(addr.MAP_ID)
        )
    
    def save_state(self, path: str) -> bool:
        """Salva o estado do emulador."""
        if not self.pyboy:
            return False
        
        try:
            with open(path, "wb") as f:
                self.pyboy.save_state(f)
            logger.info(f"Estado salvo: {path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")
            return False
    
    def load_state(self, path: str) -> bool:
        """Carrega um estado salvo."""
        if not self.pyboy:
            return False
        
        try:
            with open(path, "rb") as f:
                self.pyboy.load_state(f)
            logger.info(f"Estado carregado: {path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao carregar estado: {e}")
            return False

