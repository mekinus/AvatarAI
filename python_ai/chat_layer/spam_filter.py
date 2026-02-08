"""
Filtro de spam para mensagens do Twitch chat.
Detecta mensagens repetitivas, comandos de bot e palavras/usuários bloqueados.
"""

import re
from collections import deque
from typing import Optional, Set
from datetime import datetime, timedelta


class SpamFilter:
    """Filtra spam e mensagens indesejadas do chat."""
    
    def __init__(
        self,
        min_length: int = 3,
        max_length: int = 500,
        repeat_threshold: int = 3,
        repeat_window_seconds: int = 30,
        blocked_words: Optional[Set[str]] = None,
        blocked_users: Optional[Set[str]] = None
    ):
        """
        Args:
            min_length: Tamanho mínimo da mensagem
            max_length: Tamanho máximo da mensagem
            repeat_threshold: Número de repetições para considerar spam
            repeat_window_seconds: Janela de tempo para detectar repetições
            blocked_words: Conjunto de palavras bloqueadas
            blocked_users: Conjunto de usuários bloqueados
        """
        self.min_length = min_length
        self.max_length = max_length
        self.repeat_threshold = repeat_threshold
        self.repeat_window_seconds = repeat_window_seconds
        
        self.blocked_words = blocked_words or set()
        self.blocked_users = blocked_users or set()
        
        # Histórico de mensagens recentes para detectar repetições
        self.recent_messages = deque(maxlen=100)
        
        # Comandos comuns de bot para filtrar (removido ! genérico para permitir comandos personalizados)
        self.bot_commands = {
            '!sr', '!songrequest', '!commands',
            '!help', '!discord', '!socials', '!followage'
        }
        
        # Comandos permitidos que nunca são considerados spam
        self.allowed_commands = {
            '!manual', '!ai', '!auto', '!takeover', '!control', '!me', '!toggle', '!switch',
            '!save', '!load'
        }
    
    def is_spam(self, username: str, message: str) -> tuple[bool, Optional[str]]:
        """
        Verifica se uma mensagem é spam.
        
        Returns:
            (is_spam, reason) - True se for spam e motivo
        """
        # Verifica comandos permitidos
        message_lower = message.lower().strip()
        if message_lower in self.allowed_commands:
            return False, None
            
        # Verifica usuário bloqueado
        if username.lower() in {u.lower() for u in self.blocked_users}:
            return True, "Usuário bloqueado"
        
        # Verifica tamanho
        if len(message) < self.min_length:
            return True, "Mensagem muito curta"
        
        if len(message) > self.max_length:
            return True, "Mensagem muito longa"
        
        # Verifica palavras bloqueadas
        message_lower = message.lower()
        for word in self.blocked_words:
            if word.lower() in message_lower:
                return True, f"Palavra bloqueada: {word}"
        
        # Verifica comandos de bot
        message_stripped = message.strip()
        if message_stripped.startswith(tuple(self.bot_commands)):
            return True, "Comando de bot"
        
        # Verifica repetições
        now = datetime.now()
        message_normalized = self._normalize_message(message)
        
        # Conta repetições recentes
        recent_count = 0
        for msg_time, msg_user, msg_text in self.recent_messages:
            if (now - msg_time).total_seconds() <= self.repeat_window_seconds:
                if msg_text == message_normalized:
                    recent_count += 1
                    if recent_count >= self.repeat_threshold:
                        return True, "Mensagem repetitiva"
        
        # Adiciona à lista de mensagens recentes
        self.recent_messages.append((now, username, message_normalized))
        
        return False, None
    
    def _normalize_message(self, message: str) -> str:
        """Normaliza mensagem para comparação (remove espaços extras, lowercase)."""
        # Remove espaços extras e converte para lowercase
        normalized = re.sub(r'\s+', ' ', message.strip().lower())
        # Remove caracteres especiais comuns de spam
        normalized = re.sub(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>?]', '', normalized)
        return normalized
    
    def add_blocked_word(self, word: str):
        """Adiciona palavra à lista de bloqueio."""
        self.blocked_words.add(word.lower())
    
    def add_blocked_user(self, username: str):
        """Adiciona usuário à lista de bloqueio."""
        self.blocked_users.add(username.lower())
    
    def remove_blocked_word(self, word: str):
        """Remove palavra da lista de bloqueio."""
        self.blocked_words.discard(word.lower())
    
    def remove_blocked_user(self, username: str):
        """Remove usuário da lista de bloqueio."""
        self.blocked_users.discard(username.lower())

