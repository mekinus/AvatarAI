"""
State Machine para gerenciar estados da IA.
Estados: IDLE, TALKING, PLAYING, THINKING
"""

import logging
from enum import Enum
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class State(Enum):
    """Estados possíveis da IA."""
    IDLE = "IDLE"
    TALKING = "TALKING"
    PLAYING = "PLAYING"
    THINKING = "THINKING"


class StateManager:
    """Gerencia transições de estado da IA."""
    
    def __init__(self, initial_state: State = State.IDLE):
        """
        Args:
            initial_state: Estado inicial
        """
        self.current_state = initial_state
        self.state_history: list[tuple[datetime, State, Optional[str]]] = []
        self.state_start_time = datetime.now()
        
        logger.info(f"StateManager inicializado com estado: {initial_state.value}")
    
    def transition_to(self, new_state: State, reason: Optional[str] = None):
        """
        Transiciona para um novo estado.
        
        Args:
            new_state: Novo estado
            reason: Motivo da transição (opcional)
        """
        if new_state == self.current_state:
            return  # Já está no estado
        
        old_state = self.current_state
        duration = (datetime.now() - self.state_start_time).total_seconds()
        
        self.current_state = new_state
        self.state_start_time = datetime.now()
        
        # Registra transição
        self.state_history.append((datetime.now(), new_state, reason))
        
        logger.info(
            f"Transição: {old_state.value} -> {new_state.value} "
            f"(duração anterior: {duration:.2f}s, motivo: {reason or 'N/A'})"
        )
    
    def can_transition_to(self, new_state: State) -> bool:
        """
        Verifica se pode transicionar para um estado.
        Implementa regras para evitar conflitos.
        
        Args:
            new_state: Estado desejado
        
        Returns:
            True se pode transicionar
        """
        # Regras de transição
        if self.current_state == State.PLAYING and new_state == State.TALKING:
            # Pode falar enquanto joga, mas com cuidado
            return True
        
        if self.current_state == State.TALKING and new_state == State.PLAYING:
            # Pode jogar enquanto fala
            return True
        
        if self.current_state == State.THINKING:
            # Pode sair de THINKING para qualquer estado
            return True
        
        # Outras transições são permitidas
        return True
    
    def get_state_duration(self) -> float:
        """Retorna duração do estado atual em segundos."""
        return (datetime.now() - self.state_start_time).total_seconds()
    
    def get_current_state(self) -> State:
        """Retorna o estado atual."""
        return self.current_state
    
    def update_state_from_decision(self, decision_type: str):
        """
        Atualiza estado baseado em decisão do Brain.
        
        Args:
            decision_type: Tipo da decisão (GOAL, SAY, IDLE)
        """
        if decision_type == "GOAL":
            if self.can_transition_to(State.PLAYING):
                self.transition_to(State.PLAYING, "Decisão: GOAL")
        elif decision_type == "SAY":
            if self.can_transition_to(State.TALKING):
                self.transition_to(State.TALKING, "Decisão: SAY")
        elif decision_type == "IDLE":
            if self.can_transition_to(State.IDLE):
                self.transition_to(State.IDLE, "Decisão: IDLE")
    
    def set_thinking(self):
        """Define estado como THINKING."""
        if self.can_transition_to(State.THINKING):
            self.transition_to(State.THINKING, "Processando decisão")
    
    def get_recent_history(self, count: int = 5) -> list:
        """Retorna histórico recente de transições."""
        return self.state_history[-count:] if len(self.state_history) > count else self.state_history

