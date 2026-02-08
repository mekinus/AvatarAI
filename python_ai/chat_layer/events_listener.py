"""
Listener de eventos do Twitch usando EventSub WebSocket.
Escuta follows, subs, bits, raids e outros eventos.
"""

import asyncio
import json
import logging
import websockets
import aiohttp
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Tipos de eventos suportados."""
    FOLLOW = "channel.follow"
    SUBSCRIBE = "channel.subscribe"
    SUBSCRIPTION_GIFT = "channel.subscription.gift"
    CHEER = "channel.cheer"
    RAID = "channel.raid"


@dataclass
class TwitchEvent:
    """Representa um evento do Twitch."""
    event_type: EventType
    username: str
    data: Dict[str, Any]
    
    @property
    def display_name(self) -> str:
        """Retorna o display name do usuário."""
        return self.data.get("user_name", self.username)


class EventsListener:
    """Escuta eventos do Twitch via EventSub WebSocket."""
    
    EVENTSUB_URL = "wss://eventsub.wss.twitch.tv/ws"
    HELIX_URL = "https://api.twitch.tv/helix"
    
    def __init__(
        self,
        client_id: str,
        access_token: str,
        broadcaster_id: str,
        event_callback: Callable[[TwitchEvent], None],
        enabled_events: Optional[list] = None
    ):
        """
        Args:
            client_id: Client ID da aplicação Twitch
            access_token: OAuth token (sem prefixo oauth:)
            broadcaster_id: ID do canal do broadcaster
            event_callback: Função chamada quando um evento é recebido
            enabled_events: Lista de EventType para escutar (None = todos)
        """
        self.client_id = client_id
        self.access_token = access_token.replace("oauth:", "")
        self.broadcaster_id = broadcaster_id
        self.event_callback = event_callback
        self.enabled_events = enabled_events or [e for e in EventType]
        
        self.websocket = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.should_reconnect = True
        self._reconnect_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia a conexão com EventSub."""
        logger.info("Iniciando EventsListener...")
        
        try:
            await self._connect()
        except Exception as e:
            logger.error(f"Erro ao conectar EventSub: {e}")
            if self.should_reconnect:
                await self._schedule_reconnect()
    
    async def _connect(self):
        """Conecta ao WebSocket do EventSub."""
        logger.info(f"Conectando ao EventSub WebSocket: {self.EVENTSUB_URL}")
        
        self.websocket = await websockets.connect(
            self.EVENTSUB_URL,
            ping_interval=None,  # Twitch gerencia keepalive
            ping_timeout=None
        )
        
        # Aguarda mensagem de boas-vindas
        welcome_msg = await self.websocket.recv()
        welcome_data = json.loads(welcome_msg)
        
        if welcome_data.get("metadata", {}).get("message_type") != "session_welcome":
            raise Exception(f"Esperava session_welcome, recebeu: {welcome_data}")
        
        self.session_id = welcome_data["payload"]["session"]["id"]
        keepalive_timeout = welcome_data["payload"]["session"]["keepalive_timeout_seconds"]
        
        logger.info(f"EventSub conectado! Session ID: {self.session_id}")
        
        # Registra subscriptions para os eventos habilitados
        await self._subscribe_to_events()
        
        self.is_connected = True
        
        # Inicia task de escuta
        self._listen_task = asyncio.create_task(self._listen_loop())
    
    async def _subscribe_to_events(self):
        """Registra subscriptions para eventos habilitados."""
        if not self.session_id:
            logger.error("Sem session_id para registrar eventos")
            return
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Client-Id": self.client_id,
                "Content-Type": "application/json"
            }
            
            for event_type in self.enabled_events:
                try:
                    await self._create_subscription(session, headers, event_type)
                except Exception as e:
                    logger.warning(f"Falha ao registrar {event_type.value}: {e}")
    
    async def _create_subscription(
        self,
        session: aiohttp.ClientSession,
        headers: dict,
        event_type: EventType
    ):
        """Cria uma subscription para um tipo de evento."""
        # Monta condição baseada no tipo de evento
        condition = self._get_condition(event_type)
        
        # Versão da subscription
        version = self._get_version(event_type)
        
        payload = {
            "type": event_type.value,
            "version": version,
            "condition": condition,
            "transport": {
                "method": "websocket",
                "session_id": self.session_id
            }
        }
        
        url = f"{self.HELIX_URL}/eventsub/subscriptions"
        
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 202:
                logger.info(f"Subscription criada: {event_type.value}")
            elif resp.status == 409:
                logger.debug(f"Subscription já existe: {event_type.value}")
            else:
                error = await resp.text()
                logger.warning(f"Erro ao criar subscription {event_type.value}: {resp.status} - {error}")
    
    def _get_condition(self, event_type: EventType) -> dict:
        """Retorna a condição para o tipo de evento."""
        if event_type == EventType.FOLLOW:
            return {
                "broadcaster_user_id": self.broadcaster_id,
                "moderator_user_id": self.broadcaster_id
            }
        elif event_type == EventType.RAID:
            return {
                "to_broadcaster_user_id": self.broadcaster_id
            }
        else:
            return {
                "broadcaster_user_id": self.broadcaster_id
            }
    
    def _get_version(self, event_type: EventType) -> str:
        """Retorna a versão da API para o tipo de evento."""
        if event_type == EventType.FOLLOW:
            return "2"  # Follow v2 requer moderator_user_id
        return "1"
    
    async def _listen_loop(self):
        """Loop de escuta de mensagens do WebSocket."""
        logger.info("Iniciando loop de escuta EventSub")
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Conexão EventSub fechada: {e}")
            self.is_connected = False
            if self.should_reconnect:
                await self._schedule_reconnect()
        except Exception as e:
            logger.error(f"Erro no loop EventSub: {e}")
            self.is_connected = False
            if self.should_reconnect:
                await self._schedule_reconnect()
    
    async def _handle_message(self, raw_message: str):
        """Processa uma mensagem do WebSocket."""
        try:
            data = json.loads(raw_message)
            message_type = data.get("metadata", {}).get("message_type")
            
            if message_type == "session_keepalive":
                # Keepalive - não faz nada
                pass
            
            elif message_type == "notification":
                # Evento recebido!
                await self._handle_notification(data)
            
            elif message_type == "session_reconnect":
                # Precisa reconectar
                reconnect_url = data["payload"]["session"]["reconnect_url"]
                logger.info(f"EventSub solicitou reconexão: {reconnect_url}")
                # Fecha conexão atual e reconecta
                await self.websocket.close()
                self.EVENTSUB_URL = reconnect_url
                await self._connect()
            
            elif message_type == "revocation":
                # Subscription revogada
                sub_type = data["payload"]["subscription"]["type"]
                logger.warning(f"Subscription revogada: {sub_type}")
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido do EventSub: {e}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem EventSub: {e}")
    
    async def _handle_notification(self, data: dict):
        """Processa uma notificação de evento."""
        try:
            sub_type = data["payload"]["subscription"]["type"]
            event_data = data["payload"]["event"]
            
            # Mapeia para EventType
            event_type = None
            for et in EventType:
                if et.value == sub_type:
                    event_type = et
                    break
            
            if not event_type:
                logger.warning(f"Tipo de evento desconhecido: {sub_type}")
                return
            
            # Extrai username
            username = self._extract_username(event_type, event_data)
            
            # Cria objeto de evento
            event = TwitchEvent(
                event_type=event_type,
                username=username,
                data=event_data
            )
            
            logger.info(f"Evento recebido: {event_type.value} de {event.display_name}")
            
            # Chama callback
            try:
                self.event_callback(event)
            except Exception as e:
                logger.error(f"Erro no callback de evento: {e}")
                
        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}")
    
    def _extract_username(self, event_type: EventType, event_data: dict) -> str:
        """Extrai o username do evento baseado no tipo."""
        if event_type == EventType.FOLLOW:
            return event_data.get("user_login", "unknown")
        elif event_type == EventType.SUBSCRIBE:
            return event_data.get("user_login", "unknown")
        elif event_type == EventType.SUBSCRIPTION_GIFT:
            return event_data.get("user_login", "anonymous")
        elif event_type == EventType.CHEER:
            return event_data.get("user_login", "anonymous")
        elif event_type == EventType.RAID:
            return event_data.get("from_broadcaster_user_login", "unknown")
        return "unknown"
    
    async def _schedule_reconnect(self, delay: float = 5.0):
        """Agenda reconexão após delay."""
        if self._reconnect_task and not self._reconnect_task.done():
            return
        
        logger.info(f"Agendando reconexão EventSub em {delay}s...")
        self._reconnect_task = asyncio.create_task(self._reconnect_after(delay))
    
    async def _reconnect_after(self, delay: float):
        """Reconecta após delay."""
        await asyncio.sleep(delay)
        if self.should_reconnect and not self.is_connected:
            logger.info("Reconectando EventSub...")
            await self.start()
    
    async def stop(self):
        """Para o listener."""
        logger.info("Parando EventsListener...")
        self.should_reconnect = False
        self.is_connected = False
        
        # Cancela tasks
        for task in [self._listen_task, self._reconnect_task, self._keepalive_task]:
            if task and not task.done():
                task.cancel()
        
        # Fecha WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar WebSocket: {e}")
        
        logger.info("EventsListener parado")

