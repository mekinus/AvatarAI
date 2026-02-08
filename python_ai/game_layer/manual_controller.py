"""
Sistema de Controle Manual do PyBoy.
Permite alternar entre modo AI e modo Manual (teclado).
"""

import logging
import asyncio
import threading
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ControlMode(Enum):
    """Modos de controle do PyBoy."""
    AI = "ai"           # IA controla (automático)
    MANUAL = "manual"   # Você controla (teclado)


class ManualController:
    """
    Controlador manual para PyBoy.
    Permite alternar entre controle da IA e controle manual via teclado.
    """
    
    def __init__(
        self,
        pyboy_client,
        state_path: str = "roms/pokemon_red.gb.state",
        on_mode_change: Optional[Callable[[ControlMode], None]] = None,
        on_message: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            pyboy_client: Instância do PyBoyClient
            state_path: Caminho para salvar/carregar estado
            on_mode_change: Callback quando modo muda
            on_message: Callback para enviar feedback (ex: "Jogo salvo")
        """
        self.pyboy_client = pyboy_client
        self.state_path = state_path
        self.on_mode_change = on_mode_change
        self.on_message = on_message
        self.mode = ControlMode.AI
        self.keyboard_listener = None
        self.running = False
        
        # Mapeamento de teclas para botões do Game Boy
        self.key_mapping = {
            'w': 'up',
            's': 'down',
            'a': 'left',
            'd': 'right',
            'j': 'a',      # J = botão A
            'k': 'b',      # K = botão B
            'u': 'start',  # U = Start
            'i': 'select', # I = Select
            # Setas também funcionam
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right',
        }
        
        # Teclas de controle do sistema
        self.toggle_key = 'f1'      # F1 alterna entre AI/Manual
        self.save_key = 'f5'        # F5 salva estado
        self.load_key = 'f9'        # F9 carrega estado
        self.fast_forward_key = 'space' # Space acelera (TODO)
        
        # Estado das teclas (para evitar repetição)
        self.pressed_keys = set()
        
        logger.info(f"ManualController inicializado (State path: {state_path})")
    
    def set_mode(self, mode: ControlMode):
        """Define o modo de controle."""
        if mode != self.mode:
            old_mode = self.mode
            self.mode = mode
            logger.info(f"Modo de controle alterado: {old_mode.value} -> {mode.value}")
            
            if self.on_mode_change:
                self.on_mode_change(mode)
    
    def toggle_mode(self):
        """Alterna entre AI e Manual."""
        if self.mode == ControlMode.AI:
            self.set_mode(ControlMode.MANUAL)
        else:
            self.set_mode(ControlMode.AI)
    
    def is_manual(self) -> bool:
        """Verifica se está em modo manual."""
        return self.mode == ControlMode.MANUAL
    
    def is_ai(self) -> bool:
        """Verifica se está em modo AI."""
        return self.mode == ControlMode.AI
    
    def start_keyboard_listener(self):
        """Inicia o listener de teclado em thread separada."""
        if self.running:
            return
        
        try:
            from pynput import keyboard
            
            def on_press(key):
                if not self.running:
                    return False
                
                try:
                    # Tecla normal
                    key_char = key.char.lower() if hasattr(key, 'char') and key.char else None
                except AttributeError:
                    key_char = None
                
                # Teclas especiais
                key_name = None
                if hasattr(key, 'name'):
                    key_name = key.name.lower()
                
                # Toggle de modo (F1)
                # Verifica se tecla F1 não está pressionada para evitar repetição rápida (debounce)
                if key_name and key_name == self.toggle_key:
                    if key_name not in self.pressed_keys:
                        self.pressed_keys.add(key_name)
                        self.toggle_mode()
                    return
                
                # Save (F5)
                if key_name and key_name == self.save_key:
                    if key_name not in self.pressed_keys:
                        self.pressed_keys.add(key_name)
                        self.save_game()
                    return
                
                # Load (F9)
                if key_name and key_name == self.load_key:
                    if key_name not in self.pressed_keys:
                        self.pressed_keys.add(key_name)
                        self.load_game()
                    return
                
                # Se está em modo manual, processa input do jogo
                if self.is_manual():
                    # Verifica mapeamento
                    game_button = None
                    if key_char and key_char in self.key_mapping:
                        game_button = self.key_mapping[key_char]
                    elif key_name and key_name in self.key_mapping:
                        game_button = self.key_mapping[key_name]
                    
                    if game_button and game_button not in self.pressed_keys:
                        self.pressed_keys.add(game_button)
                        self._press_button(game_button)
            
            def on_release(key):
                if not self.running:
                    return False
                
                try:
                    key_char = key.char.lower() if hasattr(key, 'char') and key.char else None
                except AttributeError:
                    key_char = None
                
                key_name = None
                if hasattr(key, 'name'):
                    key_name = key.name.lower()
                
                # Libera teclas de sistema
                if key_name in [self.toggle_key, self.save_key, self.load_key]:
                    self.pressed_keys.discard(key_name)
                    return
                
                # Remove da lista de pressionados
                game_button = None
                if key_char and key_char in self.key_mapping:
                    game_button = self.key_mapping[key_char]
                elif key_name and key_name in self.key_mapping:
                    game_button = self.key_mapping[key_name]
                
                if game_button and game_button in self.pressed_keys:
                    self.pressed_keys.discard(game_button)
                    self._release_button(game_button)
            
            self.running = True
            self.keyboard_listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release
            )
            self.keyboard_listener.start()
            
            logger.info(f"Keyboard listener iniciado (F1=Toggle, F5=Save, F9=Load, WASD=Movimento)")
            
        except ImportError:
            logger.warning("pynput não instalado. Controle manual via teclado desabilitado.")
            logger.warning("Para habilitar: pip install pynput")
    
    def save_game(self):
        """Salva o estado atual do jogo."""
        if not self.pyboy_client:
            return
        
        try:
            success = self.pyboy_client.save_state(self.state_path)
            if success:
                msg = "✅ Jogo salvo com sucesso!"
                logger.info(msg)
                if self.on_message:
                    self.on_message(msg)
            else:
                msg = "❌ Erro ao salvar jogo."
                logger.error(msg)
                if self.on_message:
                    self.on_message(msg)
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            
    def load_game(self):
        """Carrega o último estado salvo."""
        if not self.pyboy_client:
            return
        
        try:
            success = self.pyboy_client.load_state(self.state_path)
            if success:
                msg = "📂 Jogo carregado com sucesso!"
                logger.info(msg)
                if self.on_message:
                    self.on_message(msg)
            else:
                msg = "❌ Erro ao carregar (arquivo não existe?)."
                logger.error(msg)
                if self.on_message:
                    self.on_message(msg)
        except Exception as e:
            logger.error(f"Erro ao carregar: {e}")

    def _press_button(self, button: str):
        """Pressiona um botão no PyBoy."""
        if self.pyboy_client and self.pyboy_client.pyboy:
            try:
                self.pyboy_client.pyboy.button(button)
                logger.debug(f"Botão pressionado: {button}")
            except Exception as e:
                logger.error(f"Erro ao pressionar botão: {e}")
    
    def _release_button(self, button: str):
        """Solta um botão no PyBoy."""
        if self.pyboy_client and self.pyboy_client.pyboy:
            try:
                self.pyboy_client.pyboy.button_release(button)
                logger.debug(f"Botão solto: {button}")
            except Exception as e:
                logger.error(f"Erro ao soltar botão: {e}")
    
    def stop(self):
        """Para o listener de teclado."""
        self.running = False
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            self.keyboard_listener = None
        
        # Solta todas as teclas
        self.pressed_keys.clear()
        
        logger.info("ManualController parado")
    
    def process_chat_command(self, message: str) -> bool:
        """
        Processa comandos de chat para controle.
        
        Args:
            message: Mensagem do chat
        
        Returns:
            True se foi um comando de controle processado
        """
        msg_lower = message.strip().lower()
        
        # Comandos para tomar controle
        if msg_lower in ['!takeover', '!manual', '!control', '!me']:
            self.set_mode(ControlMode.MANUAL)
            return True
        
        # Comandos para devolver para IA
        if msg_lower in ['!auto', '!ai', '!release', '!bot']:
            self.set_mode(ControlMode.AI)
            return True
        
        # Toggle
        if msg_lower in ['!toggle', '!switch']:
            self.toggle_mode()
            return True
        
        # Save
        if msg_lower in ['!save', '!savegame']:
            self.save_game()
            return True
        
        # Load
        if msg_lower in ['!load', '!loadgame']:
            self.load_game()
            return True
        
        return False
    
    def get_status_message(self) -> str:
        """Retorna mensagem de status do modo atual."""
        if self.mode == ControlMode.MANUAL:
            return "🎮 MODO MANUAL - Você está no controle! (F1 ou !ai para devolver)"
        else:
            return "🤖 MODO IA - Bot está jogando (F1 ou !manual para assumir)"
