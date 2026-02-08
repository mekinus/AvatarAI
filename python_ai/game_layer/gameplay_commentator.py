"""
Gameplay Commentator - Sistema de comentários contextuais sobre o jogo.
Gera falas naturais da streamer baseadas no estado atual do Pokémon.
"""

import logging
import random
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .pokemon_data import get_pokemon_name, get_map_name, get_badge_names, get_badge_count

logger = logging.getLogger(__name__)


class CommentType(Enum):
    """Tipos de comentário."""
    BATTLE_START = "battle_start"
    BATTLE_ATTACK = "battle_attack"
    BATTLE_WIN = "battle_win"
    BATTLE_LOSE = "battle_lose"
    LOW_HP = "low_hp"
    CRITICAL_HP = "critical_hp"
    HEALED = "healed"
    LEVEL_UP = "level_up"
    NEW_AREA = "new_area"
    BADGE_GET = "badge_get"
    STUCK = "stuck"
    IDLE_EXPLORATION = "idle_exploration"
    WILD_ENCOUNTER = "wild_encounter"


@dataclass
class CommentRequest:
    """Requisição de comentário."""
    comment_type: CommentType
    context: Dict[str, Any]
    priority: int = 1  # 1=baixa, 2=média, 3=alta
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# Templates de comentários (múltiplos para variedade)
COMMENT_TEMPLATES = {
    CommentType.BATTLE_START: [
        "Olha só, um {enemy_name} selvagem! Vamos ver o que ele tem!",
        "Apareceu um {enemy_name}! Hora da batalha!",
        "Eita, um {enemy_name} nível {enemy_level}! Bora lá!",
        "Xii, cruzamos com um {enemy_name}! Vamos enfrentrar?",
        "Um {enemy_name} apareceu! Que emoção!",
    ],
    
    CommentType.WILD_ENCOUNTER: [
        "Nossa, olha quem apareceu! Um {enemy_name}!",
        "Ihh, encontramos um {enemy_name} por aqui!",
        "Ei, é um {enemy_name}! Será que vale a pena capturar?",
    ],
    
    CommentType.BATTLE_ATTACK: [
        "Toma essa!",
        "Vai, {pokemon_name}!",
        "Ataca!",
        "Bora bater!",
    ],
    
    CommentType.BATTLE_WIN: [
        "Ganhamos! Mandou bem, {pokemon_name}!",
        "Vitória! O {enemy_name} foi derrotado!",
        "Boa! Mais uma batalha vencida!",
        "É isso aí! {pokemon_name} arrasou!",
        "Ganhou XP! Bora evoluir logo!",
    ],
    
    CommentType.BATTLE_LOSE: [
        "Não! {pokemon_name} desmaiou!",
        "Xiii, perdemos essa...",
        "Eita, o {enemy_name} era forte demais!",
        "Vamos precisar treinar mais...",
    ],
    
    CommentType.LOW_HP: [
        "Cuidado! HP tá ficando baixo!",
        "Ai ai, precisamos curar logo!",
        "O HP tá em {hp_percent}%! Perigoso!",
        "Vish, melhor correr pro Centro Pokémon...",
    ],
    
    CommentType.CRITICAL_HP: [
        "PARA TUDO! HP tá crítico!",
        "Socorro! Só {hp_percent}% de vida!",
        "Corre pro Pokémon Center AGORA!",
        "Vamos morrer! Precisa curar já!",
    ],
    
    CommentType.HEALED: [
        "Ahh, HP restaurado! Agora sim!",
        "Curado! Vamos voltar à aventura!",
        "HP cheio! Bora meter bronca!",
        "Pronto, tudo curado! Vamos lá!",
    ],
    
    CommentType.LEVEL_UP: [
        "LEVEL UP! {pokemon_name} agora é nível {level}!",
        "Evoluímos! Nível {level}!",
        "Aeee, subimos de nível! Agora é {level}!",
        "{pokemon_name} ficou mais forte! Level {level}!",
    ],
    
    CommentType.NEW_AREA: [
        "Chegamos em {area_name}! Hora de explorar!",
        "Nova área desbloqueada: {area_name}!",
        "Olha, entramos em {area_name}!",
        "Legal, agora estamos em {area_name}!",
    ],
    
    CommentType.BADGE_GET: [
        "CONSEGUIMOS A {badge_name}! Agora temos {badge_count} badges!",
        "Uma insígnia nova! {badge_name} adquirida!",
        "Aeee! Mais uma badge: {badge_name}!",
        "É isso! {badge_count} de 8 badges!",
    ],
    
    CommentType.STUCK: [
        "Hmm, acho que estou preso... Vou tentar outro caminho.",
        "Opa, bati numa parede. Vou por outro lado.",
        "Não consigo ir por aqui. Vamos ver...",
        "Onde eu vou agora? Deixa eu pensar...",
    ],
    
    CommentType.IDLE_EXPLORATION: [
        "Só explorando por aqui...",
        "Vamos ver o que tem nessa área.",
        "Caminhando, caminhando...",
        "Procurando Pokémon selvagens!",
        "Será que tem algo interessante por aqui?",
        "Explorando a região!",
    ],
}


class GameplayCommentator:
    """
    Gera comentários contextuais sobre o gameplay.
    Monitora o estado do jogo e cria falas naturais.
    """
    
    # Tipos de comentário que são baseados em eventos reais do jogo (leitura de memória)
    GAME_EVENT_TYPES = {
        CommentType.BATTLE_START,
        CommentType.BATTLE_WIN,
        CommentType.BATTLE_LOSE,
        CommentType.LOW_HP,
        CommentType.CRITICAL_HP,
        CommentType.HEALED,
        CommentType.LEVEL_UP,
        CommentType.NEW_AREA,
        CommentType.BADGE_GET,
        CommentType.WILD_ENCOUNTER,
    }
    
    # Tipos de comentário "idle/aleatórios" que NÃO são baseados em eventos reais
    IDLE_COMMENT_TYPES = {
        CommentType.STUCK,
        CommentType.IDLE_EXPLORATION,
        CommentType.BATTLE_ATTACK,
    }
    
    def __init__(
        self,
        on_comment: Optional[Callable[[str, int], None]] = None,
        cooldown_sec: float = 15.0,
        min_interval_sec: float = 30.0,
        idle_comment_interval: float = 60.0,
        game_events_only: bool = True
    ):
        """
        Args:
            on_comment: Callback chamado quando há comentário (texto, prioridade)
            cooldown_sec: Tempo mínimo entre comentários do MESMO tipo
            min_interval_sec: Tempo mínimo entre QUALQUER comentário (global)
            idle_comment_interval: Intervalo para comentários idle (segundos)
            game_events_only: Se True, só emite comentários de eventos reais do jogo
        """
        self.on_comment = on_comment
        self.cooldown_sec = cooldown_sec
        self.min_interval_sec = min_interval_sec
        self.idle_comment_interval = idle_comment_interval
        self.game_events_only = game_events_only
        
        # Estado anterior
        self.prev_state: Dict[str, Any] = {}
        self.prev_in_battle = False
        self.prev_hp_percent = 100.0
        self.prev_level = 0
        self.prev_map_id = 0
        self.prev_badges = 0
        self.prev_position = (0, 0)
        
        # Controle de cooldown por tipo
        self.last_comment_time: Dict[CommentType, datetime] = {}
        
        # Controle de intervalo global
        self.last_any_comment_time = datetime.now() - timedelta(seconds=min_interval_sec)
        self.last_movement_time = datetime.now()
        
        # Fila de comentários pendentes
        self.comment_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        
        # Estado de batalha
        self.current_enemy_name = ""
        self.current_pokemon_level = 0
        
        logger.info(f"GameplayCommentator iniciado (Eventos Reais Only: {game_events_only})")
        
    def reset(self):
        """Reseta o estado interno do comentarista."""
        self.prev_state = {}
        self.prev_in_battle = False
        self.prev_hp_percent = 100.0
        self.prev_level = 0
        self.prev_map_id = 0
        self.prev_badges = 0
        self.prev_position = (0, 0)
        self.last_any_comment_time = datetime.now() - timedelta(seconds=self.min_interval_sec)
        logger.info("GameplayCommentator resetado")
    
    def _can_comment(self, comment_type: CommentType) -> bool:
        """Verifica se pode fazer comentário (cooldown por tipo + global)."""
        now = datetime.now()
        
        # Verifica intervalo GLOBAL mínimo entre qualquer comentário
        global_elapsed = (now - self.last_any_comment_time).total_seconds()
        if global_elapsed < self.min_interval_sec:
            return False
        
        # Verifica cooldown específico do tipo de comentário
        if comment_type in self.last_comment_time:
            type_elapsed = (now - self.last_comment_time[comment_type]).total_seconds()
            if type_elapsed < self.cooldown_sec:
                return False
        
        return True
    
    def _is_game_event(self, comment_type: CommentType) -> bool:
        """Verifica se o tipo de comentário é um evento real do jogo."""
        return comment_type in self.GAME_EVENT_TYPES
    
    def _generate_comment(self, comment_type: CommentType, context: Dict[str, Any]) -> str:
        """Gera um comentário baseado no template."""
        templates = COMMENT_TEMPLATES.get(comment_type, ["Algo aconteceu!"])
        template = random.choice(templates)
        
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Faltando chave no contexto: {e}")
            return template
    
    def _emit_comment(self, comment_type: CommentType, context: Dict[str, Any], priority: int = 1):
        """Emite um comentário se permitido pelo cooldown."""
        # Se game_events_only está ativo, ignora comentários que não são eventos reais
        if self.game_events_only and not self._is_game_event(comment_type):
            return
        
        if not self._can_comment(comment_type):
            return
        
        comment = self._generate_comment(comment_type, context)
        self.last_comment_time[comment_type] = datetime.now()
        self.last_any_comment_time = datetime.now()
        
        logger.info(f"[Comentário] {comment_type.value}: {comment}")
        
        # Adiciona à fila
        try:
            self.comment_queue.put_nowait(CommentRequest(
                comment_type=comment_type,
                context=context,
                priority=priority
            ))
        except asyncio.QueueFull:
            pass
        
        # Callback
        if self.on_comment:
            try:
                self.on_comment(comment, priority)
            except Exception as e:
                logger.error(f"Erro no callback de comentário: {e}")
    
    def process_state(self, game_state: Dict[str, Any]) -> Optional[str]:
        """
        Processa o estado atual do jogo e gera comentários.
        
        Args:
            game_state: Estado do jogo (do PyBoyClient.get_pokemon_state())
            
        Returns:
            Comentário gerado ou None
        """
        comment = None
        
        # Extrai dados do estado
        in_battle = game_state.get("in_battle", False)
        hp_percent = game_state.get("hp_percent", 100)
        level = game_state.get("party_level", 0)
        map_id = game_state.get("map_id", 0)
        badges = game_state.get("badges", 0)
        position = (game_state.get("player_x", 0), game_state.get("player_y", 0))
        
        # Nomes traduzidos
        enemy_id = game_state.get("enemy_species", 0)
        party_id = game_state.get("party_species", 0)
        enemy_name = get_pokemon_name(enemy_id) or "inimigo"
        pokemon_name = get_pokemon_name(party_id) or "nosso Pokémon"
        area_name = get_map_name(map_id)
        
        self.current_enemy_name = enemy_name
        self.current_pokemon_name = pokemon_name
        
        context = {
            "enemy_name": enemy_name,
            "pokemon_name": pokemon_name,
            "enemy_level": game_state.get("enemy_level", 0),
            "level": level,
            "hp_percent": hp_percent,
            "area_name": area_name,
            "badge_count": get_badge_count(badges),
        }
        
        # === Detecção de Eventos ===
        
        # 1. Início de batalha
        if in_battle and not self.prev_in_battle:
            context["enemy_name"] = enemy_name
            self._emit_comment(CommentType.BATTLE_START, context, priority=2)
        
        # 2. Fim de batalha (vitória ou derrota)
        if not in_battle and self.prev_in_battle:
            if hp_percent > 0:
                context["enemy_name"] = self.current_enemy_name
                self._emit_comment(CommentType.BATTLE_WIN, context, priority=2)
            else:
                self._emit_comment(CommentType.BATTLE_LOSE, context, priority=3)
        
        # 3. HP baixo
        if hp_percent <= 20 and self.prev_hp_percent > 20:
            self._emit_comment(CommentType.CRITICAL_HP, context, priority=3)
        elif hp_percent <= 50 and self.prev_hp_percent > 50:
            self._emit_comment(CommentType.LOW_HP, context, priority=2)
        
        # 4. Curou
        if hp_percent >= 80 and self.prev_hp_percent < 50:
            self._emit_comment(CommentType.HEALED, context, priority=1)
        
        # 5. Level up
        if level > self.prev_level and self.prev_level > 0:
            self._emit_comment(CommentType.LEVEL_UP, context, priority=2)
        
        # 6. Nova área
        if map_id != self.prev_map_id and map_id > 0 and self.prev_map_id > 0:
            self._emit_comment(CommentType.NEW_AREA, context, priority=1)
        
        # 7. Nova badge
        if badges > self.prev_badges:
            new_badges = get_badge_names(badges)
            if new_badges:
                context["badge_name"] = new_badges[-1]
            else:
                context["badge_name"] = "nova insígnia"
            self._emit_comment(CommentType.BADGE_GET, context, priority=3)
        
        # 8. Stuck (sem movimento por muito tempo)
        if position == self.prev_position:
            time_stuck = (datetime.now() - self.last_movement_time).total_seconds()
            if time_stuck > 10:  # 10 segundos parado
                self._emit_comment(CommentType.STUCK, context, priority=1)
                self.last_movement_time = datetime.now()  # Reset para evitar spam
        else:
            self.last_movement_time = datetime.now()
        
        # 9. Comentário idle (exploração)
        if not in_battle:
            time_since_comment = (datetime.now() - self.last_any_comment_time).total_seconds()
            if time_since_comment > self.idle_comment_interval:
                self._emit_comment(CommentType.IDLE_EXPLORATION, context, priority=1)
        
        # Atualiza estado anterior
        self.prev_state = game_state.copy()
        self.prev_in_battle = in_battle
        self.prev_hp_percent = hp_percent
        self.prev_level = level
        self.prev_map_id = map_id
        self.prev_badges = badges
        self.prev_position = position
        
        return comment
    
    async def get_next_comment(self) -> Optional[CommentRequest]:
        """Pega próximo comentário da fila (não bloqueante)."""
        try:
            return self.comment_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
    
    def get_all_pending_comments(self) -> List[CommentRequest]:
        """Pega todos os comentários pendentes."""
        comments = []
        while True:
            try:
                comments.append(self.comment_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return comments
    
    def clear_comments(self):
        """Limpa fila de comentários."""
        while not self.comment_queue.empty():
            try:
                self.comment_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
