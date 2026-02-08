"""
Planner que converte GOALs do Brain em ações discretas.
Mapeia objetivos de alto nível para ações de jogo.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class Planner:
    """Converte objetivos em ações de jogo."""
    
    # Mapeamento de palavras-chave para ações
    ACTION_KEYWORDS = {
        "MOVE_LEFT": ["esquerda", "left", "esquerdo", "fugir esquerda", "desviar esquerda"],
        "MOVE_RIGHT": ["direita", "right", "direito", "fugir direita", "desviar direita"],
        "JUMP": ["pular", "jump", "pulo", "saltar", "obstáculo", "obstaculo", "plataforma"],
        "ATTACK": ["atacar", "attack", "golpear", "bater", "inimigo", "enemy"],
        "IDLE": ["parar", "idle", "esperar", "aguardar", "nada"]
    }
    
    def __init__(self):
        """Inicializa o planner."""
        logger.info("Planner inicializado")
    
    def plan(self, goal: str) -> List[str]:
        """
        Converte um GOAL em lista de ações.
        
        Args:
            goal: Objetivo descritivo (ex: "desviar do inimigo", "pular obstáculo")
        
        Returns:
            Lista de ações (ex: ["MOVE_LEFT", "JUMP"])
        """
        if not goal:
            return ["IDLE"]
        
        goal_lower = goal.lower()
        actions = []
        
        # Procura palavras-chave no objetivo
        for action, keywords in self.ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in goal_lower:
                    if action not in actions:
                        actions.append(action)
                    break
        
        # Se não encontrou nenhuma ação, tenta inferência mais complexa
        if not actions:
            actions = self._infer_action(goal_lower)
        
        # Se ainda não encontrou, retorna IDLE
        if not actions:
            logger.warning(f"Não foi possível planejar ação para: {goal}")
            return ["IDLE"]
        
        logger.debug(f"GOAL '{goal}' convertido em ações: {actions}")
        return actions
    
    def _infer_action(self, goal: str) -> List[str]:
        """
        Tenta inferir ação de forma mais inteligente.
        
        Args:
            goal: Objetivo em lowercase
        
        Returns:
            Lista de ações inferidas
        """
        actions = []
        
        # Padrões mais complexos
        if re.search(r"(desviar|fugir|esquivar|evitar)", goal):
            # Se menciona direção específica
            if "esquerda" in goal or "left" in goal:
                actions.append("MOVE_LEFT")
            elif "direita" in goal or "right" in goal:
                actions.append("MOVE_RIGHT")
            else:
                # Desvia aleatoriamente (padrão: esquerda)
                actions.append("MOVE_LEFT")
        
        if re.search(r"(pular|saltar|pulo|jump)", goal):
            actions.append("JUMP")
        
        if re.search(r"(atacar|golpear|bater|attack)", goal):
            actions.append("ATTACK")
        
        return actions
    
    def plan_sequence(self, goal: str, max_actions: int = 3) -> List[str]:
        """
        Planeja uma sequência de ações para um objetivo.
        
        Args:
            goal: Objetivo
            max_actions: Número máximo de ações na sequência
        
        Returns:
            Lista de ações ordenadas
        """
        actions = self.plan(goal)
        
        # Limita número de ações
        if len(actions) > max_actions:
            actions = actions[:max_actions]
        
        return actions

