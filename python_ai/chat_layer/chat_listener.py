"""
Listener do Twitch chat usando SimpleIRCClient.
Escuta mensagens, aplica rate limiting e filtra spam.
"""

import asyncio
import logging
from typing import Callable, Optional
from datetime import datetime
from collections import deque

from .spam_filter import SpamFilter


logger = logging.getLogger(__name__)


class ChatListener:
    """Escuta e processa mensagens do Twitch chat."""
    
    def __init__(
        self,
        token: str,
        channel: str,
        username: str,
        message_callback: Callable[[str, str], None],
        rate_limit_per_sec: float = 5.0,
        spam_filter: Optional[SpamFilter] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        bot_id: Optional[str] = None
    ):
        """
        Args:
            token: OAuth token do Twitch (formato: oauth:...)
            channel: Canal do Twitch para escutar
            username: Nome de usuário do bot
            message_callback: Função chamada quando uma mensagem válida é recebida
                             Recebe (username, message)
            rate_limit_per_sec: Máximo de mensagens por segundo para processar
            spam_filter: Instância do SpamFilter (cria uma padrão se None)
            client_id: Client ID do Twitch (não usado com SimpleIRCClient)
            client_secret: Client Secret do Twitch (não usado com SimpleIRCClient)
            bot_id: Bot ID do Twitch (não usado com SimpleIRCClient)
        """
        self.token = token
        self.channel = channel
        self.username = username
        self.message_callback = message_callback
        self.rate_limit_per_sec = rate_limit_per_sec
        
        self.spam_filter = spam_filter or SpamFilter()
        
        # Rate limiting
        self.message_times = deque()
        self.min_interval = 1.0 / rate_limit_per_sec if rate_limit_per_sec > 0 else 0
        
        # Cliente IRC
        self.irc_client = None
        self.is_connected = False
        
        # Task de reconexão
        self.reconnect_task: Optional[asyncio.Task] = None
        self.should_reconnect = True
    
    async def start(self):
        """Inicia o listener e conecta ao Twitch."""
        logger.info(f"Conectando ao canal Twitch: {self.channel}")
        
        # Garante que o canal esteja em minúsculas
        channel_lower = self.channel.lower()
        
        # Usa cliente IRC simples (mais confiável que twitchio 2.6+)
        from .simple_irc_client import SimpleIRCClient
        
        self.irc_client = SimpleIRCClient(
            token=self.token,
            channel=channel_lower,
            username=self.username,
            message_callback=self._sync_handle_message,
            use_ssl=False
        )
        
        logger.info("Usando SimpleIRCClient para conectar ao Twitch")
        
        try:
            await self.irc_client.start()
            self.is_connected = True
        except Exception as e:
            logger.error(f"Erro ao conectar ao Twitch IRC: {e}")
            self.is_connected = False
            if self.should_reconnect:
                await self._schedule_reconnect()
    
    def _sync_handle_message(self, username: str, message: str):
        """Processa uma mensagem recebida."""
        # Rate limiting
        if not self._check_rate_limit():
            logger.debug(f"Rate limit: ignorando mensagem de {username}")
            return
        
        # Filtro de spam
        is_spam, reason = self.spam_filter.is_spam(username, message)
        if is_spam:
            logger.debug(f"Spam filtrado de {username}: {reason}")
            return
        
        # Mensagem válida - chama callback
        logger.debug(f"Mensagem válida de {username}: {message}")
        try:
            self.message_callback(username, message)
        except Exception as e:
            logger.error(f"Erro no callback de mensagem: {e}")
    
    def _check_rate_limit(self) -> bool:
        """Verifica se pode processar mais uma mensagem (rate limiting)."""
        now = datetime.now()
        
        # Remove timestamps antigos (mais de 1 segundo)
        while self.message_times and (now - self.message_times[0]).total_seconds() > 1.0:
            self.message_times.popleft()
        
        # Verifica se está no limite
        if len(self.message_times) >= self.rate_limit_per_sec:
            return False
        
        # Adiciona timestamp atual
        self.message_times.append(now)
        return True
    
    async def _schedule_reconnect(self, delay: float = 5.0):
        """Agenda reconexão após delay."""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Já tem reconexão agendada
        
        logger.info(f"Agendando reconexão em {delay} segundos...")
        self.reconnect_task = asyncio.create_task(self._reconnect_after_delay(delay))
    
    async def _reconnect_after_delay(self, delay: float):
        """Aguarda delay e reconecta."""
        await asyncio.sleep(delay)
        if self.should_reconnect and not self.is_connected:
            logger.info("Tentando reconectar...")
            await self.start()
    
    async def send_chat_message(self, text: str) -> bool:
        """
        Envia uma mensagem para o chat do Twitch.
        
        Args:
            text: Texto da mensagem a enviar
        
        Returns:
            True se enviou com sucesso, False caso contrário
        """
        if not self.irc_client:
            logger.warning("Cliente IRC não inicializado, não pode enviar mensagem")
            return False
        
        return await self.irc_client.send_message(text)
    
    async def stop(self):
        """Para o listener e desconecta."""
        logger.info("Parando chat listener...")
        self.should_reconnect = False
        
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
        
        # Para o cliente IRC
        if self.irc_client:
            try:
                await self.irc_client.stop()
            except Exception as e:
                logger.warning(f"Erro ao parar cliente IRC: {e}")
        
        self.is_connected = False
        logger.info("Chat listener parado")
