"""
Serviço de Text-to-Speech com fallback.
Tenta ElevenLabs primeiro, se falhar usa gTTS (gratuito).
USA EXECUTOR para não bloquear o event loop.
"""

import base64
import io
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Executor compartilhado para operações TTS (evita criar threads excessivas)
_tts_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tts")


class TTSService:
    """Serviço de síntese de voz com fallback ElevenLabs -> gTTS.
    
    IMPORTANTE: Todas as chamadas são executadas em threads separadas
    para não bloquear o event loop/PyBoy.
    """
    
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel (voz padrão)
        model: str = "eleven_multilingual_v2"
    ):
        """
        Args:
            api_key: Chave da API ElevenLabs
            voice_id: ID da voz a usar (padrão: Rachel)
            model: Modelo de TTS (eleven_multilingual_v2 suporta PT-BR)
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        
        # ElevenLabs client (pode falhar se sem créditos)
        self.elevenlabs_client = None
        self.elevenlabs_available = True
        
        # Tenta inicializar ElevenLabs
        try:
            from elevenlabs import ElevenLabs
            self.elevenlabs_client = ElevenLabs(api_key=api_key)
            logger.info(f"TTSService inicializado (ElevenLabs: voice={voice_id}, model={model})")
        except Exception as e:
            logger.warning(f"ElevenLabs não disponível: {e}")
            self.elevenlabs_available = False
        
        # gTTS sempre disponível como fallback
        self.gtts_available = False
        try:
            from gtts import gTTS
            self.gtts_available = True
            logger.info("gTTS disponível como fallback")
        except ImportError:
            logger.warning("gTTS não instalado - instale com: pip install gtts")
    
    async def generate_speech(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Gera áudio a partir de texto.
        Tenta ElevenLabs primeiro, fallback para gTTS se falhar.
        
        EXECUTADO EM THREAD SEPARADA para não bloquear o PyBoy.
        
        Args:
            text: Texto para converter em fala
        
        Returns:
            Tupla (audio_base64, format) ou None se falhar
        """
        if not text or not text.strip():
            logger.warning("Texto vazio, não gerando áudio")
            return None
        
        text = text.strip()
        
        # Executa em thread separada para não bloquear
        loop = asyncio.get_event_loop()
        
        # Tenta ElevenLabs primeiro
        if self.elevenlabs_available and self.elevenlabs_client:
            result = await loop.run_in_executor(_tts_executor, self._sync_elevenlabs, text)
            if result:
                return result
            # Se falhou, marca como indisponível para próximas chamadas
            logger.info("ElevenLabs falhou, usando gTTS como fallback")
        
        # Fallback para gTTS
        if self.gtts_available:
            return await loop.run_in_executor(_tts_executor, self._sync_gtts, text)
        
        logger.error("Nenhum serviço TTS disponível")
        return None
    
    def _sync_elevenlabs(self, text: str) -> Optional[Tuple[str, str]]:
        """Gera áudio via ElevenLabs (SÍNCRONO - rodar em executor)."""
        try:
            logger.info(f"[ElevenLabs] Gerando áudio: {text[:50]}...")
            
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id=self.model,
                output_format="mp3_44100_128"
            )
            
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk
            
            if len(audio_bytes) < 100:
                logger.warning("[ElevenLabs] Áudio muito pequeno, pode ter falhado")
                return None
            
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"[ElevenLabs] Áudio gerado: {len(audio_bytes)} bytes")
            return (audio_base64, "mp3")
            
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "exceeded" in error_str or "401" in error_str:
                logger.warning(f"[ElevenLabs] Sem créditos ou não autorizado: {e}")
                self.elevenlabs_available = False  # Desabilita para próximas chamadas
            else:
                logger.error(f"[ElevenLabs] Erro: {e}")
            return None
    
    def _sync_gtts(self, text: str) -> Optional[Tuple[str, str]]:
        """Gera áudio via gTTS (SÍNCRONO - rodar em executor)."""
        try:
            from gtts import gTTS
            
            logger.info(f"[gTTS] Gerando áudio: {text[:50]}...")
            
            # gTTS - Google Text-to-Speech (gratuito)
            tts = gTTS(text=text, lang='pt-br', slow=False)
            
            # Salva em memória
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            audio_bytes = audio_buffer.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            
            logger.info(f"[gTTS] Áudio gerado: {len(audio_bytes)} bytes")
            return (audio_base64, "mp3")
            
        except Exception as e:
            logger.error(f"[gTTS] Erro: {e}")
            return None

    # Métodos async antigos removidos - agora usamos sync + executor
    async def _try_elevenlabs(self, text: str) -> Optional[Tuple[str, str]]:
        """Deprecated: Use generate_speech() que roda em executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_tts_executor, self._sync_elevenlabs, text)
    
    async def _try_gtts(self, text: str) -> Optional[Tuple[str, str]]:
        """Deprecated: Use generate_speech() que roda em executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_tts_executor, self._sync_gtts, text)

