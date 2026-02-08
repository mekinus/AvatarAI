"""
Sistema de memória curta para o Brain.
Mantém buffer circular das últimas N interações.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Entrada na memória."""
    timestamp: datetime
    type: str  # CHAT, GOAL, SAY, IDLE
    content: str
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Converte para dicionário."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata or {}
        }


class Memory:
    """Memória de curto prazo com buffer circular."""
    
    def __init__(self, max_size: int = 10):
        """
        Args:
            max_size: Número máximo de entradas na memória
        """
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        logger.info(f"Memória inicializada com capacidade de {max_size} entradas")
    
    def add(self, entry_type: str, content: str, metadata: Optional[dict] = None):
        """
        Adiciona uma entrada à memória.
        
        Args:
            entry_type: Tipo da entrada (CHAT, GOAL, SAY, IDLE)
            content: Conteúdo da entrada
            metadata: Metadados opcionais
        """
        # Garante que content é string
        if content is None:
            content = ""
        entry = MemoryEntry(
            timestamp=datetime.now(),
            type=entry_type,
            content=content,
            metadata=metadata
        )
        self.buffer.append(entry)
        logger.debug(f"Memória: adicionada entrada {entry_type}: {content[:50] if content else ''}...")
    
    def get_context(self, max_entries: Optional[int] = None) -> List[dict]:
        """
        Retorna contexto das últimas entradas.
        
        Args:
            max_entries: Número máximo de entradas (None = todas)
        
        Returns:
            Lista de dicionários com as entradas
        """
        entries = list(self.buffer)
        if max_entries:
            entries = entries[-max_entries:]
        
        return [entry.to_dict() for entry in entries]
    
    def get_recent_by_type(self, entry_type: str, limit: int = 5) -> List[dict]:
        """
        Retorna entradas recentes de um tipo específico.
        
        Args:
            entry_type: Tipo de entrada a buscar
            limit: Número máximo de entradas
        
        Returns:
            Lista de entradas do tipo especificado
        """
        entries = [e.to_dict() for e in self.buffer if e.type == entry_type]
        return entries[-limit:] if len(entries) > limit else entries
    
    def clear(self):
        """Limpa a memória."""
        self.buffer.clear()
        logger.info("Memória limpa")
    
    def size(self) -> int:
        """Retorna o número de entradas na memória."""
        return len(self.buffer)
    
    def is_full(self) -> bool:
        """Verifica se a memória está cheia."""
        return len(self.buffer) >= self.max_size

