"""
Cliente TCP para comunicação com Unity.
Envia comandos de ação, fala e emoção para o Unity via TCP raw.
USA FILA NÃO-BLOQUEANTE para não interferir no PyBoy.
"""

import json
import logging
import asyncio
import socket
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UnityClient:
    """Cliente TCP para Unity com envio não-bloqueante."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Args:
            host: Endereço do servidor Unity
            port: Porta do servidor Unity
        """
        self.host = host
        self.port = port
        
        self.socket: Optional[socket.socket] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.is_connected = False
        self.reconnect_delay = 2.0
        self.should_reconnect = True
        
        # Fila de mensagens (não-bloqueante)
        self._send_queue: asyncio.Queue = asyncio.Queue()
        self._sender_task: Optional[asyncio.Task] = None
        
        logger.info(f"UnityClient inicializado para {host}:{port}")
    
    async def connect(self):
        """Conecta ao servidor Unity e inicia sender task."""
        if self.is_connected:
            return
        
        try:
            logger.info(f"Conectando ao Unity em {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.is_connected = True
            logger.info("Conectado ao Unity")
            
            # Inicia task de envio em background
            if self._sender_task is None or self._sender_task.done():
                self._sender_task = asyncio.create_task(self._sender_loop())
                
        except Exception as e:
            logger.error(f"Erro ao conectar ao Unity: {e}")
            self.is_connected = False
            if self.should_reconnect:
                asyncio.create_task(self._schedule_reconnect())
    
    async def _sender_loop(self):
        """Loop de envio em background - processa fila de mensagens."""
        logger.info("Unity sender loop iniciado")
        while self.should_reconnect or self.is_connected:
            try:
                # Espera mensagem da fila (com timeout para checar conexão)
                try:
                    message = await asyncio.wait_for(self._send_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Envia mensagem
                if self.is_connected and self.writer:
                    try:
                        data = self._prepare_message_data(message)
                        self.writer.write(data)
                        await self.writer.drain()
                        logger.debug(f"Enviado para Unity: {message.get('cmd')}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar mensagem para Unity: {e}")
                        self.is_connected = False
                        await self._cleanup()
                        if self.should_reconnect:
                            asyncio.create_task(self._schedule_reconnect())
                else:
                    # Re-enfileira se desconectado
                    await self._send_queue.put(message)
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no sender loop: {e}")
                await asyncio.sleep(0.5)
        
        logger.info("Unity sender loop encerrado")
    
    async def send_action(self, action: str):
        """
        Envia comando de ação para o Unity (NÃO-BLOQUEANTE).
        
        Args:
            action: Ação a executar (MOVE_LEFT, MOVE_RIGHT, JUMP, ATTACK, IDLE)
        """
        message = {
            "cmd": "ACTION",
            "value": action,
            "timestamp": datetime.now().timestamp()
        }
        await self._queue_message(message)
    
    async def send_say(self, text: str, audio_data: Optional[str] = None, audio_format: str = "mp3"):
        """
        Envia comando de fala para o Unity (NÃO-BLOQUEANTE).
        
        Args:
            text: Texto a ser falado
            audio_data: Áudio em base64 (opcional, para TTS)
            audio_format: Formato do áudio (mp3, wav)
        """
        message = {
            "cmd": "SAY",
            "value": text,
            "timestamp": datetime.now().timestamp()
        }
        
        # Adiciona áudio se fornecido
        if audio_data:
            message["audio_data"] = audio_data
            message["audio_format"] = audio_format
        
        await self._queue_message(message)
    
    async def send_emotion(self, emotion: str, duration: float = 2.0):
        """
        Envia comando de emoção para o Unity (NÃO-BLOQUEANTE).
        
        Args:
            emotion: Emoção (Happy, Angry, Sad, Surprised)
            duration: Duração da emoção em segundos
        """
        message = {
            "cmd": "EMOTION",
            "value": emotion,
            "duration": duration,
            "timestamp": datetime.now().timestamp()
        }
        await self._queue_message(message)
    
    async def _queue_message(self, message: dict):
        """Adiciona mensagem à fila (retorna imediatamente)."""
        try:
            # put_nowait para não bloquear nunca
            self._send_queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("Fila de envio cheia, descartando mensagem antiga")
            # Remove mensagem mais antiga e adiciona nova
            try:
                self._send_queue.get_nowait()
                self._send_queue.put_nowait(message)
            except:
                pass

    def _prepare_message_data(self, message: dict) -> bytes:
        """Serializa mensagem para bytes."""
        json_message = json.dumps(message) + "\n"
        return json_message.encode('utf-8')
    
    async def _cleanup(self):
        """Limpa recursos de conexão."""
        try:
            if self.writer:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except Exception:
                    pass
        except Exception:
            pass
        
        self.writer = None
        self.reader = None
        self.socket = None
    
    async def _schedule_reconnect(self):
        """Agenda reconexão."""
        await asyncio.sleep(self.reconnect_delay)
        if self.should_reconnect and not self.is_connected:
            await self.connect()
    
    async def disconnect(self):
        """Desconecta do Unity."""
        logger.info("Desconectando do Unity...")
        self.should_reconnect = False
        
        # Cancela sender task
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
        
        await self._cleanup()
        self.is_connected = False
        logger.info("Desconectado do Unity")
    
    async def ping(self):
        """Verifica se a conexão está ativa."""
        if self.is_connected and self.writer:
            try:
                # Tenta enviar um ping (mensagem vazia ou teste)
                test_message = {"cmd": "PING", "timestamp": datetime.now().timestamp()}
                await self._queue_message(test_message)
                return True
            except Exception:
                self.is_connected = False
                return False
        return False

