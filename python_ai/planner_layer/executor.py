"""
Executor que executa ações com cooldown e rate limiting.
Evita spam de comandos e gerencia timing.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from .unity_client import UnityClient

logger = logging.getLogger(__name__)


class Executor:
    """Executa ações com controle de timing."""
    
    def __init__(
        self,
        unity_client: UnityClient,
        action_cooldown: float = 0.1,
        max_actions_per_sec: float = 10.0
    ):
        """
        Args:
            unity_client: Cliente Unity
            action_cooldown: Cooldown mínimo entre ações (segundos)
            max_actions_per_sec: Máximo de ações por segundo
        """
        self.unity_client = unity_client
        self.action_cooldown = action_cooldown
        self.max_actions_per_sec = max_actions_per_sec
        self.min_interval = 1.0 / max_actions_per_sec if max_actions_per_sec > 0 else 0
        
        self.last_action_time: Optional[datetime] = None
        self.action_times: List[datetime] = []
        
        logger.info(f"Executor inicializado (cooldown={action_cooldown}s, max={max_actions_per_sec}/s)")
    
    async def execute_actions(self, actions: List[str]):
        """
        Executa uma lista de ações com cooldown.
        
        Args:
            actions: Lista de ações a executar
        """
        if not actions:
            return
        
        logger.debug(f"Executando {len(actions)} ações: {actions}")
        
        for action in actions:
            # Verifica rate limit
            if not self._check_rate_limit():
                logger.debug(f"Rate limit atingido, aguardando...")
                await asyncio.sleep(self.min_interval)
            
            # Executa ação
            await self.unity_client.send_action(action)
            
            # Atualiza timestamps
            now = datetime.now()
            self.last_action_time = now
            self.action_times.append(now)
            
            # Remove timestamps antigos
            cutoff = now - timedelta(seconds=1.0)
            self.action_times = [t for t in self.action_times if t > cutoff]
            
            # Cooldown entre ações
            if self.action_cooldown > 0:
                await asyncio.sleep(self.action_cooldown)
    
    def _check_rate_limit(self) -> bool:
        """Verifica se pode executar mais uma ação."""
        if not self.action_times:
            return True
        
        now = datetime.now()
        recent_count = sum(1 for t in self.action_times if (now - t).total_seconds() <= 1.0)
        
        return recent_count < self.max_actions_per_sec
    
    async def execute_single_action(self, action: str):
        """Executa uma única ação."""
        await self.execute_actions([action])

