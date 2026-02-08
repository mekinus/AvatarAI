"""
Cliente IRC simples para Twitch chat.
Implementação direta sem dependências complexas.
"""

import asyncio
import logging
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SimpleIRCClient:
    """Cliente IRC simples para conectar ao Twitch chat."""
    
    TWITCH_IRC_HOST = "irc.chat.twitch.tv"
    TWITCH_IRC_PORT = 6667
    TWITCH_IRC_SSL_PORT = 6697
    
    def __init__(
        self,
        token: str,
        channel: str,
        username: str,
        message_callback: Callable[[str, str], None],
        use_ssl: bool = False
    ):
        """
        Args:
            token: OAuth token do Twitch (formato: oauth:...)
            channel: Canal do Twitch para escutar (sem #)
            username: Nome de usuário do bot
            message_callback: Função chamada quando uma mensagem é recebida
            use_ssl: Se deve usar SSL (porta 6697)
        """
        self.token = token if token.startswith("oauth:") else f"oauth:{token}"
        self.channel = channel.lower().lstrip("#")
        self.username = username.lower()
        self.message_callback = message_callback
        self.use_ssl = use_ssl
        
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False
        self.should_run = True
        
        # Regex para parsear mensagens PRIVMSG (com suporte a tags IRC do Twitch)
        # Formato: @tags :username!user@user.tmi.twitch.tv PRIVMSG #channel :message
        self.privmsg_pattern = re.compile(
            r"(?:@\S+ )?:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #(\w+) :(.+)"
        )
    
    async def connect(self):
        """Conecta ao servidor IRC do Twitch."""
        host = self.TWITCH_IRC_HOST
        port = self.TWITCH_IRC_SSL_PORT if self.use_ssl else self.TWITCH_IRC_PORT
        
        # Valida o token
        if not self.token.startswith("oauth:"):
            logger.warning("Token não começa com 'oauth:' - isso pode causar falha de autenticação")
        
        logger.info(f"Conectando ao Twitch IRC: {host}:{port}")
        
        try:
            if self.use_ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                self.reader, self.writer = await asyncio.open_connection(
                    host, port, ssl=ssl_context
                )
            else:
                self.reader, self.writer = await asyncio.open_connection(host, port)
            
            logger.info("Conexão TCP estabelecida")
            
            # Envia autenticação
            await self._send(f"PASS {self.token}")
            await self._send(f"NICK {self.username}")
            
            # Aguarda resposta
            await asyncio.sleep(1)
            
            # Solicita capabilities
            await self._send("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands")
            
            # Entra no canal
            await self._send(f"JOIN #{self.channel}")
            
            logger.info(f"Enviado JOIN para #{self.channel}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao Twitch IRC: {e}")
            return False
    
    async def _send(self, message: str):
        """Envia uma mensagem IRC."""
        if self.writer:
            self.writer.write(f"{message}\r\n".encode("utf-8"))
            await self.writer.drain()
            logger.debug(f"IRC > {message[:50]}...")
    
    async def _handle_message(self, line: str):
        """Processa uma linha recebida do IRC."""
        line = line.strip()
        if not line:
            return
        
        # Log de mensagens de erro ou NOTICE (para diagnóstico)
        if "NOTICE" in line or "Error" in line or "error" in line or "failed" in line.lower():
            logger.warning(f"IRC NOTICE/ERROR: {line}")
        
        # Responde a PING
        if line.startswith("PING"):
            pong = line.replace("PING", "PONG")
            await self._send(pong)
            return
        
        # Verifica se é uma mensagem PRIVMSG
        match = self.privmsg_pattern.match(line)
        if match:
            username = match.group(1)
            channel = match.group(2)
            message = match.group(3)
            
            logger.info(f"[{channel}] {username}: {message}")
            
            # Ignora mensagens do próprio bot
            if username.lower() != self.username.lower():
                try:
                    self.message_callback(username, message)
                except Exception as e:
                    logger.error(f"Erro no callback de mensagem: {e}")
        
        # Log de mensagens JOIN
        elif "JOIN" in line and self.channel in line.lower():
            logger.info(f"Confirmado: entrou no canal #{self.channel}")
    
    async def listen(self):
        """Loop principal para escutar mensagens."""
        if not self.reader:
            logger.error("Não conectado ao IRC")
            return
        
        logger.info("Iniciando loop de escuta IRC")
        
        try:
            while self.should_run:
                try:
                    line = await asyncio.wait_for(
                        self.reader.readline(),
                        timeout=300  # 5 minutos de timeout
                    )
                    if not line:
                        logger.warning("Conexão IRC fechada pelo servidor")
                        break
                    
                    decoded = line.decode("utf-8", errors="ignore")
                    await self._handle_message(decoded)
                    
                except asyncio.TimeoutError:
                    # Envia PING para manter conexão
                    await self._send("PING :keepalive")
                    
        except Exception as e:
            logger.error(f"Erro no loop de escuta IRC: {e}")
        
        self.is_connected = False
    
    async def send_message(self, text: str):
        """
        Envia uma mensagem para o chat do canal.
        
        Args:
            text: Texto da mensagem a enviar
        """
        if not self.is_connected or not self.writer:
            logger.warning("Não conectado ao IRC, não pode enviar mensagem")
            return False
        
        try:
            # Limita tamanho da mensagem (Twitch limita a 500 chars)
            if len(text) > 500:
                text = text[:497] + "..."
            
            await self._send(f"PRIVMSG #{self.channel} :{text}")
            logger.info(f"Mensagem enviada para #{self.channel}: {text[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False
    
    async def start(self):
        """Conecta e inicia a escuta."""
        if await self.connect():
            await self.listen()
    
    async def stop(self):
        """Para o cliente IRC."""
        self.should_run = False
        if self.writer:
            await self._send(f"PART #{self.channel}")
            await self._send("QUIT")
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass
        self.is_connected = False
        logger.info("Cliente IRC parado")
