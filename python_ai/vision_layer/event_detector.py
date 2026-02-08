"""
Sistema de detecção de eventos de jogo.
Monitora mudanças de estado e dispara eventos para o LLM reagir.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .pokemon_vision import GameScreen

logger = logging.getLogger(__name__)


class GameEvent(Enum):
    """Tipos de eventos de jogo."""
    # Batalha
    BATTLE_START = "battle_start"
    BATTLE_END = "battle_end"
    VICTORY = "victory"
    DEFEAT = "defeat"
    
    # HP
    LOW_HP = "low_hp"
    CRITICAL_HP = "critical_hp"
    HP_RECOVERED = "hp_recovered"
    
    # Pokémon
    NEW_POKEMON = "new_pokemon"
    POKEMON_FAINTED = "pokemon_fainted"
    POKEMON_LEVELED_UP = "pokemon_leveled_up"
    EVOLUTION = "evolution"
    
    # Progresso
    NEW_MAP = "new_map"
    BADGE_OBTAINED = "badge_obtained"
    
    # UI
    DIALOG_OPENED = "dialog_opened"
    MENU_OPENED = "menu_opened"
    
    # Especial
    STUCK = "stuck"  # Agente travado
    IDLE = "idle"  # Sem ação por muito tempo


@dataclass
class GameEventData:
    """Dados de um evento."""
    event_type: GameEvent
    timestamp: datetime
    data: Dict[str, Any]
    priority: int = 1  # 1=normal, 2=alta, 3=urgente
    
    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "priority": self.priority,
        }


class EventDetector:
    """
    Detecta eventos monitorando mudanças de estado.
    """
    
    def __init__(
        self,
        callback: Optional[Callable[[GameEventData], None]] = None,
        cooldown_sec: float = 5.0
    ):
        """
        Args:
            callback: Função chamada quando evento detectado
            cooldown_sec: Tempo mínimo entre eventos do mesmo tipo
        """
        self.callback = callback
        self.cooldown_sec = cooldown_sec
        
        # Estado anterior para comparação
        self.prev_state: Dict[str, Any] = {}
        self.prev_screen: Optional[GameScreen] = None
        self.prev_position: Optional[tuple] = None
        
        # Controle de cooldown
        self.last_event_time: Dict[GameEvent, datetime] = {}
        
        # Fila de eventos
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # Tracking
        self.stuck_counter = 0
        self.last_position_time: Optional[datetime] = None
        
        logger.info("EventDetector inicializado")
    
    def _can_fire_event(self, event_type: GameEvent) -> bool:
        """Verifica se evento pode ser disparado (cooldown)."""
        if event_type not in self.last_event_time:
            return True
        
        elapsed = (datetime.now() - self.last_event_time[event_type]).total_seconds()
        return elapsed >= self.cooldown_sec
    
    def _fire_event(
        self,
        event_type: GameEvent,
        data: Dict[str, Any],
        priority: int = 1
    ):
        """Dispara um evento."""
        if not self._can_fire_event(event_type):
            return
        
        event = GameEventData(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            priority=priority
        )
        
        self.last_event_time[event_type] = datetime.now()
        
        logger.info(f"Evento: {event_type.value} | {data}")
        
        # Adiciona à fila
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Fila de eventos cheia")
        
        # Callback
        if self.callback:
            try:
                self.callback(event)
            except Exception as e:
                logger.error(f"Erro no callback: {e}")
    
    def process_state(
        self,
        game_state: Dict[str, Any],
        vision_analysis: Dict[str, Any]
    ):
        """
        Processa estado atual e detecta eventos.
        
        Args:
            game_state: Estado da RAM (do PyBoyClient.get_pokemon_state())
            vision_analysis: Análise visual (do PokemonVision.analyze_frame())
        """
        screen_type = vision_analysis.get("screen_type", GameScreen.UNKNOWN)
        
        # --- Eventos de Batalha ---
        was_in_battle = self.prev_state.get("in_battle", False)
        is_in_battle = game_state.get("in_battle", False)
        
        if not was_in_battle and is_in_battle:
            enemy_species = game_state.get("enemy_species", 0)
            self._fire_event(
                GameEvent.BATTLE_START,
                {
                    "enemy_species": enemy_species,
                    "enemy_level": game_state.get("enemy_level", 0),
                },
                priority=2
            )
        
        if was_in_battle and not is_in_battle:
            self._fire_event(
                GameEvent.BATTLE_END,
                {"result": "unknown"},
                priority=1
            )
        
        # --- Eventos de HP ---
        hp_percent = game_state.get("hp_percent", 100)
        prev_hp = self.prev_state.get("hp_percent", 100)
        
        if hp_percent <= 20 and prev_hp > 20:
            self._fire_event(
                GameEvent.CRITICAL_HP,
                {"hp_percent": hp_percent},
                priority=3  # Urgente
            )
        elif hp_percent <= 50 and prev_hp > 50:
            self._fire_event(
                GameEvent.LOW_HP,
                {"hp_percent": hp_percent},
                priority=2
            )
        elif hp_percent > 80 and prev_hp <= 50:
            self._fire_event(
                GameEvent.HP_RECOVERED,
                {"hp_percent": hp_percent},
                priority=1
            )
        
        # --- Eventos de Level Up ---
        level = game_state.get("party_level", 0)
        prev_level = self.prev_state.get("party_level", 0)
        
        if level > prev_level and prev_level > 0:
            self._fire_event(
                GameEvent.POKEMON_LEVELED_UP,
                {"new_level": level, "old_level": prev_level},
                priority=2
            )
        
        # --- Eventos de Mapa ---
        position = (
            game_state.get("player_x", 0),
            game_state.get("player_y", 0),
            game_state.get("map_id", 0)
        )
        
        if self.prev_position:
            prev_map = self.prev_position[2]
            curr_map = position[2]
            
            # Só dispara NEW_MAP se mudou para um mapa significativo (não 0)
            if curr_map != prev_map and curr_map > 0 and prev_map > 0:
                self._fire_event(
                    GameEvent.NEW_MAP,
                    {"map_id": curr_map, "prev_map": prev_map},
                    priority=1
                )
        
        # --- Detecção de Stuck ---
        if self.prev_position == position:
            self.stuck_counter += 1
            if self.stuck_counter >= 100:  # ~10 segundos sem mover
                self._fire_event(
                    GameEvent.STUCK,
                    {"position": position, "duration": self.stuck_counter},
                    priority=2
                )
                self.stuck_counter = 0
        else:
            self.stuck_counter = 0
        
        # --- Eventos de Tela (Vision) ---
        if screen_type != self.prev_screen:
            if screen_type == GameScreen.VICTORY:
                self._fire_event(
                    GameEvent.VICTORY,
                    {"screen": screen_type.value},
                    priority=2
                )
            elif screen_type == GameScreen.FAINTED:
                self._fire_event(
                    GameEvent.POKEMON_FAINTED,
                    {"screen": screen_type.value},
                    priority=3
                )
            elif screen_type == GameScreen.EVOLUTION:
                self._fire_event(
                    GameEvent.EVOLUTION,
                    {"screen": screen_type.value},
                    priority=2
                )
            # DIALOG_OPENED removido - muito frequente e não relevante
            # elif screen_type == GameScreen.DIALOG:
            #     self._fire_event(
            #         GameEvent.DIALOG_OPENED,
            #         {},
            #         priority=1
            #     )
        
        # --- Badge ---
        badges = game_state.get("badges", 0)
        prev_badges = self.prev_state.get("badges", 0)
        
        if badges > prev_badges:
            self._fire_event(
                GameEvent.BADGE_OBTAINED,
                {"badges": badges, "new_badge": badges - prev_badges},
                priority=3
            )
        
        # Atualiza estado anterior
        self.prev_state = game_state.copy()
        self.prev_screen = screen_type
        self.prev_position = position
    
    async def get_next_event(self, timeout: float = 0.1) -> Optional[GameEventData]:
        """
        Pega próximo evento da fila.
        
        Args:
            timeout: Tempo máximo de espera
        
        Returns:
            Evento ou None se timeout
        """
        try:
            return await asyncio.wait_for(
                self.event_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    def get_pending_events(self) -> List[GameEventData]:
        """Retorna todos os eventos pendentes (não-bloqueante)."""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events
    
    def clear_events(self):
        """Limpa fila de eventos."""
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# Mapeamento de eventos para prompts do LLM
EVENT_PROMPTS = {
    GameEvent.BATTLE_START: "Uma batalha Pokémon começou! {data}",
    GameEvent.BATTLE_END: "A batalha terminou!",
    GameEvent.VICTORY: "Vitória! Ganhamos a batalha!",
    GameEvent.DEFEAT: "Oh não, perdemos a batalha...",
    GameEvent.LOW_HP: "HP está baixo ({hp_percent:.0f}%)! Cuidado!",
    GameEvent.CRITICAL_HP: "HP CRÍTICO ({hp_percent:.0f}%)! Precisamos curar AGORA!",
    GameEvent.HP_RECOVERED: "HP recuperado! Agora temos {hp_percent:.0f}%",
    GameEvent.NEW_POKEMON: "Um novo Pokémon apareceu!",
    GameEvent.POKEMON_FAINTED: "Nosso Pokémon desmaiou!",
    GameEvent.POKEMON_LEVELED_UP: "Level UP! Agora somos nível {new_level}!",
    GameEvent.EVOLUTION: "Evolução! Nosso Pokémon está evoluindo!",
    GameEvent.NEW_MAP: "Entramos em uma nova área!",
    GameEvent.BADGE_OBTAINED: "CONSEGUIMOS UMA INSÍGNIA! Total: {badges}",
    GameEvent.STUCK: "Parece que estamos presos... Vamos tentar outra direção.",
    GameEvent.IDLE: "Hmm, não fizemos nada por um tempo...",
}


def get_event_prompt(event: GameEventData) -> str:
    """Gera prompt para o LLM baseado no evento."""
    template = EVENT_PROMPTS.get(event.event_type, "Algo aconteceu no jogo.")
    try:
        return template.format(**event.data)
    except KeyError:
        return template.format(data=event.data)

