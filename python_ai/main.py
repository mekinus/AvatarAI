"""
Loop principal do sistema de streamer IA.
Integra todas as camadas: Chat → Brain → Planner → Unity
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

# Imports das camadas
from chat_layer.chat_listener import ChatListener
from chat_layer.spam_filter import SpamFilter
from chat_layer.events_listener import EventsListener, TwitchEvent, EventType
from brain_layer.brain import Brain
from brain_layer.memory import Memory
from planner_layer.planner import Planner
from planner_layer.executor import Executor
from planner_layer.unity_client import UnityClient
from state_machine.state_manager import StateManager, State
from tts_layer.tts_service import TTSService
from overlay_layer.overlay_server import OverlayServer

# Imports para Pokémon (opcionais)
try:
    from game_layer.pyboy_client import PyBoyClient, GameBoyButton
    from game_layer.gameplay_commentator import GameplayCommentator
    from game_layer.manual_controller import ManualController, ControlMode
    from vision_layer.pokemon_vision import PokemonVision, SimplePokemonVision
    from vision_layer.event_detector import EventDetector, GameEvent, get_event_prompt
    from rl_layer.pokemon_agent import PokemonRLAgent, PokemonEnvironment, SimpleAgent
    POKEMON_AVAILABLE = True
except ImportError as e:
    POKEMON_AVAILABLE = False
    logging.warning(f"Módulos de Pokémon não disponíveis: {e}")


# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('avatar_ai.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class AvatarAISystem:
    """Sistema principal que integra todas as camadas."""
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config = self._load_config(config_path)
        self.running = False
        
        # Inicializa componentes
        self.spam_filter = SpamFilter()
        self.memory = Memory(max_size=10)
        # Configuração DeepSeek (opcional)
        deepseek_config = None
        if "deepseek" in self.config and self.config["deepseek"].get("api_key"):
            deepseek_config = self.config["deepseek"]
        
        self.brain = Brain(
            api_key=self.config["openai"]["api_key"],
            model=self.config["openai"]["model"],
            temperature=self.config["openai"]["temperature"],
            memory=self.memory,
            deepseek_config=deepseek_config
        )
        self.planner = Planner()
        self.unity_client = UnityClient(
            host=self.config["unity"]["host"],
            port=self.config["unity"]["port"]
        )
        self.executor = Executor(
            unity_client=self.unity_client,
            action_cooldown=0.1,
            max_actions_per_sec=self.config["rate_limits"]["actions_per_sec"]
        )
        self.state_manager = StateManager(initial_state=State.IDLE)
        
        # Inicializa TTS (opcional - se configurado)
        self.tts_service: Optional[TTSService] = None
        if "elevenlabs" in self.config and self.config["elevenlabs"].get("api_key"):
            elevenlabs_config = self.config["elevenlabs"]
            # Só inicializa se a API key não for o placeholder
            if elevenlabs_config["api_key"] != "SUA_API_KEY_ELEVENLABS":
                self.tts_service = TTSService(
                    api_key=elevenlabs_config["api_key"],
                    voice_id=elevenlabs_config.get("voice_id", "21m00Tcm4TlvDq8ikWAM"),
                    model=elevenlabs_config.get("model", "eleven_multilingual_v2")
                )
                logger.info("TTS ElevenLabs habilitado")
            else:
                logger.warning("TTS desabilitado: configure a API key do ElevenLabs no config.json")
        
        # Chat listener será criado no start()
        self.chat_listener: Optional[ChatListener] = None
        
        # Events listener para EventSub
        self.events_listener: Optional[EventsListener] = None
        
        # Fila de mensagens do chat
        self.chat_queue = asyncio.Queue()
        
        # Fila de eventos do Twitch (follows, subs, bits, raids)
        self.events_queue = asyncio.Queue()
        
        # Rate limiting para decisões do Brain
        self.last_brain_decision_time = 0.0
        self.brain_decision_interval = 1.0 / self.config["rate_limits"]["brain_decisions_per_sec"]
        
        # Componentes de Pokémon (inicializados em start() se habilitado)
        self.pyboy_client = None
        self.pokemon_vision = None
        self.event_detector = None
        self.gameplay_commentator = None  # Comentários contextuais da streamer
        self.manual_controller = None  # Controle manual do PyBoy
        self.rl_agent = None
        self.game_events_queue = asyncio.Queue()
        self.pokemon_enabled = False
        
        # Thread Pool reutilizável para visão
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.rl_executor = ThreadPoolExecutor(max_workers=1)
        
        # Overlay server para OBS Browser Source
        overlay_config = self.config.get("overlay", {})
        if overlay_config.get("enabled", True):
            self.overlay_server = OverlayServer(
                ws_port=overlay_config.get("ws_port", 8767),
                http_port=overlay_config.get("http_port", 8768)
            )
        else:
            self.overlay_server = None
        
        logger.info("Sistema AvatarAI inicializado")
    
    def _load_config(self, config_path: str) -> dict:
        """Carrega configuração do arquivo JSON."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Configuração carregada de {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Arquivo de configuração não encontrado: {config_path}")
            logger.info("Usando configuração padrão (será necessário configurar manualmente)")
            return self._default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON de configuração: {e}")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Retorna configuração padrão."""
        return {
            "twitch": {
                "token": "oauth:SEU_TOKEN_AQUI",
                "channel": "seu_canal",
                "username": "seu_bot"
            },
            "openai": {
                "api_key": "sk-...",
                "model": "gpt-4",
                "temperature": 0.7
            },
            "unity": {
                "host": "localhost",
                "port": 8765
            },
            "rate_limits": {
                "chat_messages_per_sec": 5,
                "brain_decisions_per_sec": 2,
                "actions_per_sec": 10
            }
        }
    
    async def start(self):
        """Inicia o sistema."""
        logger.info("Iniciando sistema AvatarAI...")
        self.running = True
        
        # Conecta ao Unity
        await self.unity_client.connect()
        
        # Inicia overlay server
        if self.overlay_server:
            await self.overlay_server.start()
        
        # Cria chat listener
        twitch_config = self.config.get("twitch", {})
        self.chat_listener = ChatListener(
            token=twitch_config["token"],
            channel=twitch_config["channel"],
            username=twitch_config["username"],
            message_callback=self._on_chat_message,
            rate_limit_per_sec=self.config["rate_limits"]["chat_messages_per_sec"],
            spam_filter=self.spam_filter,
            client_id=twitch_config.get("client_id"),
            client_secret=twitch_config.get("client_secret"),
            bot_id=twitch_config.get("bot_id")
        )
        
        # Inicia chat listener em background
        chat_task = asyncio.create_task(self.chat_listener.start())
        
        # Cria events listener (EventSub) se habilitado
        eventsub_config = self.config.get("eventsub", {})
        if eventsub_config.get("enabled", False):
            await self._start_events_listener(twitch_config, eventsub_config)
        
        # Inicializa sistema Pokémon se habilitado
        pokemon_config = self.config.get("pokemon", {})
        if pokemon_config.get("enabled", False) and POKEMON_AVAILABLE:
            await self._start_pokemon_system(pokemon_config)
        
        # Loop principal
        try:
            await self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrupção recebida (Ctrl+C)")
        finally:
            await self.stop()
    
    async def _start_events_listener(self, twitch_config: dict, eventsub_config: dict):
        """Inicia o EventsListener para eventos do Twitch."""
        client_id = twitch_config.get("client_id")
        access_token = twitch_config.get("token", "").replace("oauth:", "")
        broadcaster_id = twitch_config.get("bot_id")  # Usa bot_id como broadcaster_id
        
        if not all([client_id, access_token, broadcaster_id]):
            logger.warning("EventSub desabilitado: falta client_id, token ou bot_id no config")
            return
        
        # Mapeia eventos habilitados
        enabled_events = []
        event_mapping = {
            "follow": EventType.FOLLOW,
            "subscribe": EventType.SUBSCRIBE,
            "subscription_gift": EventType.SUBSCRIPTION_GIFT,
            "cheer": EventType.CHEER,
            "raid": EventType.RAID
        }
        
        for event_name in eventsub_config.get("events", []):
            if event_name in event_mapping:
                enabled_events.append(event_mapping[event_name])
        
        if not enabled_events:
            logger.warning("EventSub: nenhum evento habilitado")
            return
        
        logger.info(f"EventSub: habilitando eventos {[e.value for e in enabled_events]}")
        
        self.events_listener = EventsListener(
            client_id=client_id,
            access_token=access_token,
            broadcaster_id=broadcaster_id,
            event_callback=self._on_twitch_event,
            enabled_events=enabled_events
        )
        
        # Inicia em background
        asyncio.create_task(self.events_listener.start())
    
    async def _start_pokemon_system(self, pokemon_config: dict):
        """Inicializa o sistema de Pokémon (PyBoy + Vision + RL)."""
        if not POKEMON_AVAILABLE:
            logger.error("Módulos de Pokémon não disponíveis")
            return
        
        rom_path = pokemon_config.get("rom_path", "roms/pokemon_red.gb")
        
        # Inicializa PyBoy
        logger.info(f"Iniciando PyBoy com ROM: {rom_path}")
        self.pyboy_client = PyBoyClient(
            rom_path=rom_path,
            headless=pokemon_config.get("headless", False),
            speed=pokemon_config.get("speed", 1),
            sound=pokemon_config.get("sound", False)
        )
        
        if not self.pyboy_client.start():
            logger.error("Falha ao iniciar PyBoy")
            return
        
        # Carrega save state se existir (RL foi treinado a partir deste ponto)
        state_path = rom_path + ".state"
        import os
        if os.path.exists(state_path):
            logger.info(f"Carregando save state: {state_path}")
            self.pyboy_client.load_state(state_path)
        
        # Inicializa Vision
        if pokemon_config.get("vision_enabled", True):
            device = pokemon_config.get("vision_device", "auto")
            
            # Tenta CLIP primeiro, fallback para versão simples
            try:
                self.pokemon_vision = PokemonVision(device=device)
                if not self.pokemon_vision.initialize():
                    logger.warning("CLIP não disponível, usando SimplePokemonVision")
                    self.pokemon_vision = SimplePokemonVision()
            except Exception as e:
                logger.warning(f"Erro ao inicializar CLIP: {e}, usando SimplePokemonVision")
                self.pokemon_vision = SimplePokemonVision()
            
            self.pokemon_vision.initialize()
        
        # Inicializa Event Detector
        self.event_detector = EventDetector(
            callback=self._on_game_event,
            cooldown_sec=3.0
        )
        
        # Inicializa Gameplay Commentator (comentários contextuais da streamer)
        # Lê configurações do config.json
        comments_config = self.config.get("gameplay_comments", {})
        comments_enabled = comments_config.get("enabled", True)
        
        if comments_enabled:
            self.gameplay_commentator = GameplayCommentator(
                on_comment=self._on_gameplay_comment,
                cooldown_sec=comments_config.get("cooldown_per_type_seconds", 15.0),
                min_interval_sec=comments_config.get("min_interval_seconds", 30.0),
                idle_comment_interval=60.0,  # Usado apenas se game_events_only=False
                game_events_only=comments_config.get("game_events_only", True)
            )
            logger.info(f"GameplayCommentator habilitado (intervalo={comments_config.get('min_interval_seconds', 30)}s)")
        else:
            self.gameplay_commentator = None
            logger.info("GameplayCommentator desabilitado no config")
        
        # Inicializa RL Agent ou Simple Agent
        if pokemon_config.get("use_simple_agent", False):
            logger.info("Usando SimpleAgent (sem RL)")
            self.rl_agent = SimpleAgent(self.pyboy_client, vision_analyzer=self.pokemon_vision)
        elif pokemon_config.get("rl_enabled", True):
            logger.info("Inicializando RL Agent")
            env = PokemonEnvironment(
                pyboy_client=self.pyboy_client,
                frame_skip=4,
                use_screen=False
            )
            self.rl_agent = PokemonRLAgent(
                env=env,
                model_path=pokemon_config.get("rl_model_path", "models/pokemon_ppo.zip"),
                device=pokemon_config.get("vision_device", "auto")
            )
            init_result = self.rl_agent.initialize()
            logger.info(f"RL Agent inicializado: {init_result}")
        
        # Inicializa ManualController para controle via teclado
        self.manual_controller = ManualController(
            pyboy_client=self.pyboy_client,
            state_path=state_path,
            on_mode_change=self._on_control_mode_change,
            on_message=self._on_manual_control_message
        )
        # Inicia listener de teclado para F1 toggle e WASD
        self.manual_controller.start_keyboard_listener()
        
        self.pokemon_enabled = True
        self.capture_interval_ms = pokemon_config.get("capture_interval_ms", 100)
        
        # Inicia game loop em background
        asyncio.create_task(self._pokemon_game_loop())
        
        logger.info("Sistema Pokémon inicializado com sucesso!")
        logger.info("=== CONTROLE MANUAL ===")
        logger.info("F1 = Alternar AI/Manual | F5 = Save | F9 = Load")
        logger.info("WASD = Movimento  |  J = A  |  K = B  |  U = Start  |  I = Select")
        logger.info("Chat: !manual / !ai / !save / !load")
    
    async def _pokemon_game_loop(self):
        """Loop principal do jogo Pokémon - OTIMIZADO PARA 60 FPS."""
        logger.info("Game loop Pokémon iniciado (otimizado)")
        
        import time as time_module
        
        # Configurações de timing
        target_fps = 60
        frame_time = 1.0 / target_fps
        action_interval_frames = 12  # Decide ação a cada 12 frames (~200ms at 60fps)
        
        # Contadores
        frame_count = 0
        last_action_frame = 0
        
        # Cache de visão (atualizado raramente)
        pending_action_future = None
        cached_vision_analysis = {}
        vision_update_interval = 120  # Atualiza visão a cada 120 frames (~2s)
        last_vision_frame = 0
        
        # Estado do botão atual (para não bloquear)
        current_button = None
        button_frames_remaining = 0
        
        while self.running and self.pokemon_enabled:
            try:
                loop_start = time_module.perf_counter()
                
                # === EMULAÇÃO (SEMPRE RODA) ===
                # Tick 1 frame do emulador
                self.pyboy_client.tick(1)
                frame_count += 1
                
                # Gerencia botão pressionado (non-blocking)
                if button_frames_remaining > 0:
                    if current_button:
                        # Mantém pressionado neste frame
                        self.pyboy_client.pyboy.button(current_button.name.lower())
                    
                    button_frames_remaining -= 1
                    if button_frames_remaining == 0 and current_button is not None:
                        # Solta o botão
                        self.pyboy_client.pyboy.button_release(current_button.name.lower())
                        current_button = None
                
                # === VISÃO (RARA - a cada 2s) ===
                if frame_count - last_vision_frame >= vision_update_interval:
                    last_vision_frame = frame_count
                    # Dispara análise em background (não bloqueia)
                    asyncio.create_task(self._analyze_vision_async(cached_vision_analysis))
                
                # === VERIFICA MODO DE CONTROLE ===
                is_manual_mode = self.manual_controller and self.manual_controller.is_manual()
                
                # === DECISÃO DE AÇÃO (ASSÍNCRONA) - SÓ SE MODO AI ===
                if not is_manual_mode:
                    # Verifica se há decisão pendente
                    if pending_action_future and pending_action_future.done():
                        try:
                            action = pending_action_future.result()
                            pending_action_future = None
                            
                            # Executa ação
                            if action > 0:
                                button_map = {
                                    1: GameBoyButton.A,
                                    2: GameBoyButton.B,
                                    3: GameBoyButton.START,
                                    4: GameBoyButton.SELECT,
                                    5: GameBoyButton.UP,
                                    6: GameBoyButton.DOWN,
                                    7: GameBoyButton.LEFT,
                                    8: GameBoyButton.RIGHT,
                                }
                                if action in button_map:
                                    current_button = button_map[action]
                                    button_frames_remaining = 8  # Mantém pressionado por 8 frames
                                    self.pyboy_client.pyboy.button(current_button.name.lower())
                        except Exception as e:
                            logger.error(f"Erro na predição RL: {e}")
                            pending_action_future = None

                # Inicia nova decisão se necessário (e não houver uma pendente) - SÓ SE MODO AI
                if not is_manual_mode and not pending_action_future and frame_count - last_action_frame >= action_interval_frames:
                    last_action_frame = frame_count
                    
                    if self.rl_agent and button_frames_remaining == 0:
                        loop = asyncio.get_event_loop()
                        if hasattr(self.rl_agent, 'env'):
                            # RL Agent: Roda em executor para não bloquear
                            obs = self.rl_agent.env._get_observation()
                            pending_action_future = loop.run_in_executor(
                                self.rl_executor,
                                self.rl_agent.predict,
                                obs,
                                False
                            )
                        else:
                            # Simple Agent: Pode rodar direto (é rápido) ou no executor
                            # Como é muito rápido, rodamos direto para evitar overhead
                            # Mas mantemos a estrutura consistente se quiser mudar depois
                            try:
                                action = self.rl_agent.predict(vision_analysis=cached_vision_analysis)
                                # Simula um future concluído
                                f = asyncio.Future()
                                f.set_result(action)
                                pending_action_future = f
                            except Exception as e:
                                logger.error(f"Erro no SimpleAgent: {e}")
                
                # === FRAME TIMING (mantém 60 FPS) ===
                elapsed = time_module.perf_counter() - loop_start
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Erro no game loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)
        
        logger.info("Game loop Pokémon encerrado")
    
    async def _analyze_vision_async(self, cache_dict: dict):
        """Análise de visão assíncrona (não bloqueia o loop principal)."""
        try:
            # Pega estado da RAM
            game_state = self.pyboy_client.get_pokemon_state()
            
            # Pega frame e analisa com visão (PESADO - só a cada 2s)
            vision_analysis = {}
            if self.pokemon_vision:
                try:
                    frame = self.pyboy_client.get_frame()
                    if frame is not None:
                        # Executa análise em thread separada para não bloquear
                        loop = asyncio.get_event_loop()
                        # Usa o executor reutilizável
                        vision_analysis = await loop.run_in_executor(
                            self.executor,
                            self.pokemon_vision.analyze_frame,
                            frame
                        )
                except Exception as e:
                    logger.warning(f"Erro na análise de visão: {e}")
            
            # Atualiza cache
            cache_dict.clear()
            cache_dict.update(vision_analysis)
            
            # Detecta eventos com análise completa
            if self.event_detector:
                self.event_detector.process_state(game_state, vision_analysis)
            
            # Gera comentários contextuais da streamer
            if self.gameplay_commentator:
                self.gameplay_commentator.process_state(game_state)
                
        except Exception as e:
            logger.error(f"Erro na análise assíncrona: {e}")
    
    def _on_game_event(self, event):
        """Callback chamado quando um evento de jogo é detectado."""
        asyncio.create_task(self.game_events_queue.put(event))
    
    def _on_control_mode_change(self, mode: ControlMode):
        """Callback chamado quando o modo de controle muda."""
        if mode == ControlMode.MANUAL:
            message = "🎮 Modo MANUAL ativado! O streamer assumiu o controle."
            logger.info("=== MODO MANUAL ATIVADO ===")
        else:
            message = "🤖 Modo AI ativado! O bot voltou a jogar."
            logger.info("=== MODO AI ATIVADO ===")
        
        # Envia notificação para Unity (opcional)
        asyncio.create_task(self._send_control_mode_notification(message))
    
    async def _send_control_mode_notification(self, message: str):
        """Envia notificação de mudança de modo para Unity."""
        try:
            await self.unity_client.send_say(message)
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de modo: {e}")

    def _on_manual_control_message(self, message: str):
        """Callback chamado quando ManualController tem uma mensagem de feedback."""
        # Se carregou jogo, reseta o comentarista para evitar confusão de estado
        if "carregado com sucesso" in message and self.gameplay_commentator:
            self.gameplay_commentator.reset()
            
        # Envia para Unity
        asyncio.create_task(self.unity_client.send_say(message))
        # Envia para Twitch
        if self.chat_listener:
            asyncio.create_task(self.chat_listener.send_chat_message(message))
    
    def _on_gameplay_comment(self, comment: str, priority: int):
        """Callback chamado quando o GameplayCommentator gera um comentário."""
        # Cria task para enviar comentário para Unity (com TTS)
        asyncio.create_task(self._send_gameplay_comment(comment, priority))
    
    async def _send_gameplay_comment(self, comment: str, priority: int):
        """Envia comentário de gameplay para Unity (com TTS se disponível)."""
        try:
            logger.info(f"[Gameplay] Streamer diz: {comment}")
            
            # Gera áudio TTS se disponível
            audio_data = None
            audio_format = "mp3"
            if self.tts_service and comment:
                result = await self.tts_service.generate_speech(comment)
                if result:
                    audio_data, audio_format = result
            
            # Envia para Unity
            await self.unity_client.send_say(comment, audio_data=audio_data, audio_format=audio_format)
            
            # Envia para overlay (fala da avatar)
            if self.overlay_server:
                await self.overlay_server.broadcast_avatar_speech(comment)
            
            # Envia para chat do Twitch se configurado
            comments_config = self.config.get("gameplay_comments", {})
            send_to_chat = comments_config.get("send_to_chat", False)
            priority_threshold = comments_config.get("priority_threshold_for_chat", 3)
            
            if send_to_chat and priority >= priority_threshold and self.chat_listener:
                await self.chat_listener.send_chat_message(comment)
                
        except Exception as e:
            logger.error(f"Erro ao enviar comentário de gameplay: {e}")
    
    def _on_chat_message(self, username: str, message: str):
        """Callback chamado quando uma mensagem do chat é recebida."""
        # Envia para overlay (todas as mensagens, sem rate limit)
        if self.overlay_server:
            asyncio.create_task(self.overlay_server.broadcast_chat(username, message))
        
        # Adiciona à fila para processamento assíncrono
        asyncio.create_task(self.chat_queue.put((username, message)))
    
    def _on_twitch_event(self, event: TwitchEvent):
        """Callback chamado quando um evento do Twitch é recebido."""
        # Adiciona à fila para processamento assíncrono
        asyncio.create_task(self.events_queue.put(event))
    
    async def _main_loop(self):
        """Loop principal do sistema."""
        logger.info("Loop principal iniciado")
        
        last_autonomous_decision = 0.0
        autonomous_decision_interval = 5.0  # Decisão autônoma a cada 5 segundos
        
        while self.running:
            try:
                # PRIORIDADE 1: Processa eventos do Twitch (follows, subs, bits, raids)
                try:
                    event = await asyncio.wait_for(
                        self.events_queue.get(),
                        timeout=0.05
                    )
                    await self._process_twitch_event(event)
                    continue  # Processa próximo evento antes de chat
                except asyncio.TimeoutError:
                    pass  # Nenhum evento
                
                # PRIORIDADE 1.5: Processa eventos de jogo (Pokémon)
                try:
                    game_event = await asyncio.wait_for(
                        self.game_events_queue.get(),
                        timeout=0.05
                    )
                    await self._process_game_event(game_event)
                    continue  # Processa próximo evento
                except asyncio.TimeoutError:
                    pass  # Nenhum evento de jogo
                
                # PRIORIDADE 2: Processa mensagens do chat
                try:
                    username, message = await asyncio.wait_for(
                        self.chat_queue.get(),
                        timeout=0.05
                    )
                    await self._process_chat_message(username, message)
                except asyncio.TimeoutError:
                    pass  # Nenhuma mensagem no timeout
                
                # Decisão autônoma periódica (se não houver mensagens recentes)
                current_time = asyncio.get_event_loop().time()
                if current_time - last_autonomous_decision >= autonomous_decision_interval:
                    if self.chat_queue.empty() and self.events_queue.empty():
                        await self._make_autonomous_decision()
                    last_autonomous_decision = current_time
                
                # Pequeno delay para não sobrecarregar CPU
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}", exc_info=True)
                await asyncio.sleep(1.0)
    
    async def _process_game_event(self, game_event):
        """Processa um evento de jogo (Pokémon)."""
        logger.info(f"Processando evento de jogo: {game_event.event_type.value}")
        
        # Se disable_brain_while_gaming está ativo, não processa eventos pelo Brain
        # Os comentários são gerados pelo GameplayCommentator
        comments_config = self.config.get("gameplay_comments", {})
        if comments_config.get("disable_brain_while_gaming", True):
            logger.debug("Evento de jogo ignorado pelo Brain (disable_brain_while_gaming=true)")
            return
        
        # Atualiza estado para THINKING
        self.state_manager.set_thinking()
        
        # Brain processa evento de jogo
        decision = await self.brain.process_game_event(
            event_type=game_event.event_type.value,
            event_data=game_event.data
        )
        
        # Atualiza estado baseado na decisão
        self.state_manager.update_state_from_decision(decision["type"])
        
        # Executa decisão
        await self._execute_decision(decision)
    
    async def _process_twitch_event(self, event: TwitchEvent):
        """Processa um evento do Twitch (follow, sub, bits, raid)."""
        # Eventos sempre são processados (sem rate limit)
        logger.info(f"Processando evento {event.event_type.value} de {event.display_name}")
        
        # Atualiza estado para THINKING
        self.state_manager.set_thinking()
        
        # Mapeia EventType para string
        event_type_map = {
            EventType.FOLLOW: "follow",
            EventType.SUBSCRIBE: "subscribe",
            EventType.SUBSCRIPTION_GIFT: "subscription_gift",
            EventType.CHEER: "cheer",
            EventType.RAID: "raid"
        }
        event_type_str = event_type_map.get(event.event_type, "unknown")
        
        # Envia para overlay
        if self.overlay_server:
            await self.overlay_server.broadcast_event(event_type_str, {
                "username": event.display_name,
                **event.data
            })
        
        # Brain processa evento
        decision = await self.brain.process_event(
            event_type=event_type_str,
            username=event.display_name,
            event_data=event.data
        )
        
        # Atualiza estado baseado na decisão
        self.state_manager.update_state_from_decision(decision["type"])
        
        # Executa decisão
        await self._execute_decision(decision)
    
    async def _process_chat_message(self, username: str, message: str):
        """Processa uma mensagem do chat."""
        
        # Verifica se é um comando de controle manual
        if self.manual_controller and self.manual_controller.process_chat_command(message):
            # Foi um comando de controle, envia status
            status = self.manual_controller.get_status_message()
            await self.unity_client.send_say(status)
            if self.chat_listener:
                await self.chat_listener.send_chat_message(status)
            return
        
        if not self._can_make_brain_decision():
            logger.debug("Rate limit do Brain, ignorando mensagem")
            return
        
        logger.info(f"Processando mensagem de {username}: {message}")
        
        # Atualiza estado para THINKING
        self.state_manager.set_thinking()
        
        # Brain processa mensagem
        decision = await self.brain.process_chat_message(username, message)
        
        # Atualiza estado baseado na decisão
        self.state_manager.update_state_from_decision(decision["type"])
        
        # Executa decisão
        await self._execute_decision(decision)
    
    async def _make_autonomous_decision(self):
        """Faz uma decisão autônoma (sem mensagem do chat)."""
        # Verifica se deve desabilitar Brain enquanto joga
        comments_config = self.config.get("gameplay_comments", {})
        if self.pokemon_enabled and comments_config.get("disable_brain_while_gaming", True):
            # Não faz decisões autônomas do Brain enquanto joga Pokémon
            # Os comentários vêm do GameplayCommentator
            return
        
        if not self._can_make_brain_decision():
            return
        
        logger.debug("Fazendo decisão autônoma")
        
        # Atualiza estado para THINKING
        self.state_manager.set_thinking()
        
        # Brain faz decisão
        decision = await self.brain.make_decision()
        
        # Atualiza estado
        self.state_manager.update_state_from_decision(decision["type"])
        
        # Executa decisão
        await self._execute_decision(decision)
    
    async def _execute_decision(self, decision: dict):
        """Executa uma decisão do Brain."""
        decision_type = decision.get("type")
        decision_value = decision.get("value")
        
        if decision_type == "GOAL":
            # Converte GOAL em ações
            actions = self.planner.plan(decision_value)
            logger.info(f"Executando ações para GOAL '{decision_value}': {actions}")
            await self.executor.execute_actions(actions)
        
        elif decision_type == "SAY":
            logger.info(f"Avatar diz: {decision_value}")
            
            # Gera áudio TTS se disponível
            audio_data = None
            audio_format = "mp3"
            if self.tts_service and decision_value:
                result = await self.tts_service.generate_speech(decision_value)
                if result:
                    audio_data, audio_format = result
                    logger.info(f"Áudio TTS gerado ({audio_format})")
            
            # Envia fala para Unity (com áudio se disponível)
            await self.unity_client.send_say(decision_value, audio_data=audio_data, audio_format=audio_format)
            
            # Envia fala para overlay
            if self.overlay_server and decision_value:
                await self.overlay_server.broadcast_avatar_speech(decision_value)
            
            # Envia fala para o chat do Twitch
            if self.chat_listener and decision_value:
                await self.chat_listener.send_chat_message(decision_value)
        
        elif decision_type == "IDLE":
            # Não faz nada
            logger.debug("Decisão: IDLE")
    
    def _can_make_brain_decision(self) -> bool:
        """Verifica se pode fazer uma decisão do Brain (rate limiting)."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self.last_brain_decision_time
        
        if time_since_last >= self.brain_decision_interval:
            self.last_brain_decision_time = current_time
            return True
        
        return False
    
    async def stop(self):
        """Para o sistema."""
        logger.info("Parando sistema AvatarAI...")
        self.running = False
        self.pokemon_enabled = False
        
        if self.chat_listener:
            await self.chat_listener.stop()
        
        if self.events_listener:
            await self.events_listener.stop()
        
        # Para overlay server
        if self.overlay_server:
            await self.overlay_server.stop()
            logger.info("Overlay server parado")
        
        # Para ManualController
        if self.manual_controller:
            self.manual_controller.stop()
            logger.info("ManualController parado")
        
        # Para PyBoy
        if self.pyboy_client:
            self.pyboy_client.stop()
            logger.info("PyBoy parado")
        
        await self.unity_client.disconnect()
        
        logger.info("Sistema parado")


async def main():
    """Função principal."""
    # Configura handlers de sinal para shutdown graceful
    def signal_handler(sig, frame):
        logger.info("Sinal de interrupção recebido")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Cria e inicia sistema
    system = AvatarAISystem()
    await system.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Programa encerrado pelo usuário")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)

