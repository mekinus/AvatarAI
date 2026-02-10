"""
Servidor de overlay para OBS Browser Source.
- WebSocket (porta 8767): push de dados em tempo real para o overlay
- HTTP (porta 8768): serve arquivos estáticos (HTML/CSS/JS)
"""

import asyncio
import json
import logging
import os
from typing import Optional, Set
from pathlib import Path

import websockets
from aiohttp import web

logger = logging.getLogger(__name__)


class OverlayServer:
    """Servidor de overlay para OBS Browser Source."""

    def __init__(self, ws_port: int = 8767, http_port: int = 8768):
        """
        Args:
            ws_port: Porta do WebSocket server
            http_port: Porta do HTTP server (arquivos estáticos)
        """
        self.ws_port = ws_port
        self.http_port = http_port
        self._clients: Set[websockets.WebSocketServerProtocol] = set()
        self._ws_server = None
        self._http_runner = None
        self._static_dir = Path(__file__).parent / "static"
        self._running = False

        logger.info(f"OverlayServer inicializado (WS:{ws_port}, HTTP:{http_port})")

    async def start(self):
        """Inicia ambos os servidores (WebSocket + HTTP)."""
        if self._running:
            return

        self._running = True

        # Inicia WebSocket server
        self._ws_server = await websockets.serve(
            self._ws_handler,
            "0.0.0.0",
            self.ws_port,
        )
        logger.info(f"Overlay WebSocket server rodando em ws://localhost:{self.ws_port}")

        # Inicia HTTP server para arquivos estáticos
        app = web.Application()
        app.router.add_get("/", self._serve_index)
        app.router.add_static("/", self._static_dir, show_index=False)

        runner = web.AppRunner(app)
        await runner.setup()
        self._http_runner = runner

        site = web.TCPSite(runner, "0.0.0.0", self.http_port)
        await site.start()
        logger.info(f"Overlay HTTP server rodando em http://localhost:{self.http_port}/overlay.html")

    async def stop(self):
        """Para ambos os servidores."""
        self._running = False

        # Fecha WebSocket
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            logger.info("Overlay WebSocket server parado")

        # Fecha HTTP
        if self._http_runner:
            await self._http_runner.cleanup()
            logger.info("Overlay HTTP server parado")

    # ── WebSocket Handler ──────────────────────────────────────────

    async def _ws_handler(self, websocket, path=None):
        """Handler de conexão WebSocket."""
        self._clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"Overlay client conectado: {client_addr}")

        try:
            # Envia mensagem de boas-vindas
            await websocket.send(json.dumps({
                "type": "connected",
                "message": "Overlay conectado com sucesso!"
            }))

            # Mantém conexão aberta
            async for message in websocket:
                # Cliente pode enviar pings ou configurações
                logger.debug(f"Overlay recebeu de {client_addr}: {message}")

        except websockets.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info(f"Overlay client desconectado: {client_addr}")

    # ── HTTP Handler ───────────────────────────────────────────────

    async def _serve_index(self, request):
        """Redireciona / para overlay.html."""
        raise web.HTTPFound("/overlay.html")

    # ── Broadcast Methods ──────────────────────────────────────────

    async def _broadcast(self, data: dict):
        """Envia dados para todos os clientes conectados."""
        if not self._clients:
            return

        message = json.dumps(data, ensure_ascii=False)
        disconnected = set()

        for client in self._clients:
            try:
                await client.send(message)
            except websockets.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Erro ao enviar para overlay client: {e}")
                disconnected.add(client)

        # Remove clientes desconectados
        self._clients -= disconnected

    async def broadcast_chat(self, username: str, message: str, color: str = ""):
        """
        Envia mensagem do chat para o overlay.

        Args:
            username: Nome do usuário
            message: Texto da mensagem
            color: Cor do usuário (hex, opcional)
        """
        await self._broadcast({
            "type": "chat",
            "username": username,
            "message": message,
            "color": color,
        })

    async def broadcast_avatar_speech(self, text: str):
        """
        Envia texto de fala da avatar para o overlay.

        Args:
            text: Texto que a avatar está falando
        """
        await self._broadcast({
            "type": "avatar_speech",
            "text": text,
        })

    async def broadcast_avatar_speech_end(self):
        """Sinaliza que a avatar parou de falar."""
        await self._broadcast({
            "type": "avatar_speech_end",
        })

    async def broadcast_event(self, event_type: str, data: dict):
        """
        Envia evento do Twitch para o overlay (follow, sub, raid, etc).

        Args:
            event_type: Tipo do evento (follow, sub, bits, raid)
            data: Dados do evento
        """
        await self._broadcast({
            "type": "event",
            "event_type": event_type,
            **data,
        })


# ── Standalone para testes ─────────────────────────────────────────

async def _test_main():
    """Executa overlay server standalone para testes."""
    logging.basicConfig(level=logging.INFO)

    server = OverlayServer()
    await server.start()

    print("\n" + "=" * 60)
    print("  OVERLAY SERVER RODANDO")
    print(f"  Abra no browser: http://localhost:{server.http_port}/overlay.html")
    print(f"  WebSocket: ws://localhost:{server.ws_port}")
    print("=" * 60)
    print("\nComandos de teste:")
    print("  c <user> <msg>  - Simula mensagem de chat")
    print("  s <texto>       - Simula fala da avatar")
    print("  e               - Encerra fala da avatar")
    print("  f <user>        - Simula follow")
    print("  q               - Sair")
    print()

    try:
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            line = line.strip()

            if not line:
                continue
            elif line.lower() == "q":
                break
            elif line.startswith("c "):
                parts = line[2:].split(" ", 1)
                if len(parts) == 2:
                    await server.broadcast_chat(parts[0], parts[1])
                    print(f"  Chat: {parts[0]}: {parts[1]}")
            elif line.startswith("s "):
                text = line[2:]
                await server.broadcast_avatar_speech(text)
                print(f"  Avatar: {text}")
            elif line.lower() == "e":
                await server.broadcast_avatar_speech_end()
                print("  Avatar: (parou de falar)")
            elif line.startswith("f "):
                user = line[2:]
                await server.broadcast_event("follow", {"username": user})
                print(f"  Evento: {user} seguiu!")
            else:
                print("  Comando desconhecido")

    except (KeyboardInterrupt, EOFError):
        pass

    await server.stop()
    print("Servidor encerrado.")


if __name__ == "__main__":
    asyncio.run(_test_main())
