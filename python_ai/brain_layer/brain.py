"""
Cérebro principal da IA.
Processa mensagens do chat e decide ações usando OpenAI ou DeepSeek.
USA CLIENTES ASSÍNCRONOS para não bloquear o event loop.
"""

import json
import logging
from typing import Optional, Dict, Any

import openai
from openai import AsyncOpenAI

from .memory import Memory
from .prompts import SYSTEM_PROMPT, build_user_prompt, get_decision_prompt, build_event_prompt

logger = logging.getLogger(__name__)


class Brain:
    """Cérebro que processa decisões usando IA (DeepSeek como primário, OpenAI como fallback).
    
    IMPORTANTE: Usa clientes ASSÍNCRONOS para não bloquear o PyBoy.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        memory: Optional[Memory] = None,
        deepseek_config: Optional[dict] = None
    ):
        """
        Args:
            api_key: Chave da API OpenAI
            model: Modelo OpenAI a usar como fallback (gpt-4, gpt-3.5-turbo, etc.)
            temperature: Temperatura para geração (0.0-2.0)
            memory: Instância de Memory (cria uma nova se None)
            deepseek_config: Configuração da DeepSeek (primário) - dict com api_key, model, base_url
        """
        openai.api_key = api_key
        # USA CLIENTE ASSÍNCRONO para não bloquear o event loop
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.memory = memory or Memory()
        
        # Configuração DeepSeek (primário) - TAMBÉM ASSÍNCRONO
        self.deepseek_config = deepseek_config
        self.deepseek_client = None
        if deepseek_config:
            self.deepseek_client = AsyncOpenAI(
                api_key=deepseek_config.get("api_key"),
                base_url=deepseek_config.get("base_url", "https://api.deepseek.com")
            )
            logger.info(f"DeepSeek configurado como API primária (modelo: {deepseek_config.get('model', 'deepseek-chat')})")
        
        logger.info(f"Brain inicializado com clientes ASSÍNCRONOS (fallback: OpenAI {model})")
    
    async def process_chat_message(self, username: str, message: str) -> Dict[str, Any]:
        """
        Processa uma mensagem do chat e retorna decisão.
        
        Args:
            username: Nome do usuário que enviou a mensagem
            message: Conteúdo da mensagem
        
        Returns:
            Dicionário com decisão: {"type": "GOAL"|"SAY"|"IDLE", "value": "..."}
        """
        # Adiciona mensagem à memória
        self.memory.add("CHAT", f"{username}: {message}", {"username": username})
        
        # Constrói prompt com contexto
        memory_context = self.memory.get_context()
        user_prompt = build_user_prompt(message, memory_context, username=username)
        
        # Chama API (DeepSeek primeiro, OpenAI como fallback)
        decision = await self._call_ai_api(user_prompt)
        
        # Adiciona decisão à memória
        if decision:
            value = decision.get("value") or ""
            self.memory.add(decision["type"], value)
        
        return decision or {"type": "IDLE", "value": None}
    
    async def make_decision(self) -> Dict[str, Any]:
        """
        Faz uma decisão sem mensagem do chat (decisão autônoma).
        
        Returns:
            Dicionário com decisão
        """
        memory_context = self.memory.get_context()
        user_prompt = get_decision_prompt()
        
        # Adiciona contexto se houver
        if memory_context:
            context_str = "\n".join([
                f"- [{e.get('type')}] {e.get('content')}"
                for e in memory_context[-3:]
            ])
            user_prompt = f"CONTEXTO RECENTE:\n{context_str}\n\n{user_prompt}"
        
        # Chama API (DeepSeek primeiro, OpenAI como fallback)
        decision = await self._call_ai_api(user_prompt)
        
        # Adiciona decisão à memória
        if decision:
            value = decision.get("value") or ""
            self.memory.add(decision["type"], value)
        
        return decision or {"type": "IDLE", "value": None}
    
    async def process_event(self, event_type: str, username: str, event_data: dict) -> Dict[str, Any]:
        """
        Processa um evento do Twitch (follow, sub, bits, raid, etc).
        
        Args:
            event_type: Tipo do evento (follow, subscribe, cheer, raid, etc)
            username: Nome do usuário que gerou o evento
            event_data: Dados adicionais do evento
        
        Returns:
            Dicionário com decisão: {"type": "SAY", "value": "..."}
        """
        # Adiciona evento à memória
        self.memory.add("EVENT", f"{event_type.upper()}: {username}", {
            "event_type": event_type,
            "username": username,
            "data": event_data
        })
        
        # Constrói prompt específico para o evento
        user_prompt = build_event_prompt(event_type, username, event_data)
        
        logger.info(f"Processando evento {event_type} de {username}")
        
        # Chama API (DeepSeek primeiro, OpenAI como fallback)
        decision = await self._call_ai_api(user_prompt)
        
        # Adiciona decisão à memória
        if decision:
            value = decision.get("value") or ""
            self.memory.add(decision["type"], value)
        
        # Eventos sempre devem gerar uma resposta SAY
        if not decision or decision.get("type") == "IDLE":
            # Fallback: resposta genérica baseada no tipo
            fallback_responses = {
                "follow": f"Obrigada por seguir, {username}! 💜",
                "subscribe": f"MUITO obrigada pela sub, {username}! 💜💜💜",
                "subscription_gift": f"Wow, {username}! Obrigada pelos gifts! 🎁💜",
                "cheer": f"Obrigada pelos bits, {username}! 💎💜",
                "raid": f"Bem-vindos raiders de {username}! 🚀💜"
            }
            return {
                "type": "SAY",
                "value": fallback_responses.get(event_type, f"Obrigada, {username}! 💜")
            }
        
        return decision
    
    async def process_game_event(self, event_type: str, event_data: dict) -> Dict[str, Any]:
        """
        Processa um evento de jogo (Pokémon) e gera reação.
        
        Args:
            event_type: Tipo do evento (battle_start, low_hp, victory, etc)
            event_data: Dados do evento
        
        Returns:
            Dicionário com decisão: {"type": "SAY", "value": "..."}
        """
        # Adiciona evento à memória
        self.memory.add("GAME_EVENT", f"{event_type.upper()}", {
            "event_type": event_type,
            "data": event_data
        })
        
        # Constrói prompt para o evento de jogo
        user_prompt = self._build_game_event_prompt(event_type, event_data)
        
        logger.info(f"Processando evento de jogo: {event_type}")
        
        # Chama API
        decision = await self._call_ai_api(user_prompt)
        
        # Adiciona decisão à memória
        if decision:
            value = decision.get("value") or ""
            self.memory.add(decision["type"], value)
        
        # Eventos de jogo sempre devem gerar SAY
        if not decision or decision.get("type") == "IDLE":
            fallback = self._get_game_event_fallback(event_type, event_data)
            return {"type": "SAY", "value": fallback}
        
        return decision
    
    def _build_game_event_prompt(self, event_type: str, event_data: dict) -> str:
        """Constrói prompt para evento de jogo."""
        prompts = {
            "battle_start": f"Uma batalha Pokémon começou! Inimigo: nível {event_data.get('enemy_level', '?')}. Reaja com empolgação e fale com os espectadores!",
            "battle_end": "A batalha terminou! Comente sobre como foi e interaja com o chat.",
            "victory": "Ganhamos a batalha! Comemore e compartilhe a alegria com os espectadores!",
            "defeat": "Perdemos a batalha... Reaja com frustração mas mantenha o ânimo. Fale com os espectadores sobre tentar novamente.",
            "low_hp": f"HP está em {event_data.get('hp_percent', 0):.0f}%! Mostre preocupação e explique o que está acontecendo.",
            "critical_hp": f"HP CRÍTICO em {event_data.get('hp_percent', 0):.0f}%! Demonstre urgência e explique a situação perigosa!",
            "hp_recovered": f"HP recuperado para {event_data.get('hp_percent', 100):.0f}%! Mostre alívio e continue jogando.",
            "pokemon_leveled_up": f"Nosso Pokémon subiu para nível {event_data.get('new_level', '?')}! Comemore e compartilhe com os espectadores!",
            "evolution": "Nosso Pokémon está evoluindo! Reaja com surpresa e alegria! Compartilhe o momento com o chat!",
            "new_map": "Entramos em uma nova área do jogo. Comente sobre a exploração e o que você espera encontrar.",
            "badge_obtained": f"CONSEGUIMOS UMA INSÍGNIA! Total: {event_data.get('badges', 0)}. Celebre muito e compartilhe a conquista!",
            "pokemon_fainted": "Nosso Pokémon desmaiou! Reaja com tristeza e explique o que aconteceu. É um momento difícil, mas vamos continuar!",
            "stuck": "Parece que estamos presos no jogo. Comente sobre tentar outra direção e continue explorando.",
        }
        
        base_prompt = prompts.get(event_type, f"Algo aconteceu no jogo: {event_type}")
        
        return f"""Você é iDream, uma streamer de Pokémon ao vivo na Twitch.

IMPORTANTE: Você está jogando Pokémon Red. Só reaja a eventos RELEVANTES do jogo (batalhas, HP, evoluções, badges, Pokémon fainted). Não fale sobre coisas aleatórias.

EVENTO: {base_prompt}

INSTRUÇÕES:
- Reaja de forma natural e expressiva, como uma streamer reagiria
- Seja breve (1-2 frases)
- Foque no evento específico que aconteceu
- Mantenha o tom apropriado (alegria para vitórias, tristeza para derrotas)
- Interaja com os espectadores quando relevante

FORMATO DE RESPOSTA (JSON):
{{"type": "SAY", "value": "sua reação aqui"}}"""
    
    def _get_game_event_fallback(self, event_type: str, event_data: dict) -> str:
        """Retorna resposta fallback para evento de jogo."""
        fallbacks = {
            "battle_start": "Ooh, uma batalha! Vamos lá!",
            "battle_end": "Ufa, batalha finalizada!",
            "victory": "VENCEMOS! Siiiim!",
            "defeat": "Aah não, perdemos... Mas vamos tentar de novo!",
            "low_hp": "Cuidado, HP baixo!",
            "critical_hp": "SOCORRO, HP CRÍTICO! Preciso curar!",
            "hp_recovered": "Aah, que alívio! HP recuperado!",
            "pokemon_leveled_up": f"LEVEL UP! Agora somos nível {event_data.get('new_level', '?')}!",
            "evolution": "MEU DEUS, EVOLUÇÃO! Que emoção!",
            "new_map": "Nova área! Vamos explorar!",
            "badge_obtained": "CONSEGUIMOS A INSÍGNIA! Woohoo!",
            "pokemon_fainted": "Noossa, nosso Pokémon desmaiou...",
            "stuck": "Hmm, parece que estou presa aqui...",
        }
        return fallbacks.get(event_type, "Hmm, algo aconteceu...")
    
    async def _call_ai_api(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Chama a API de IA (DeepSeek primeiro, OpenAI como fallback).
        
        Args:
            user_prompt: Prompt do usuário
        
        Returns:
            Dicionário com decisão ou None em caso de erro
        """
        # Tenta DeepSeek primeiro se configurado
        if self.deepseek_client and self.deepseek_config:
            try:
                decision = await self._call_deepseek(user_prompt)
                if decision and decision.get("type") != "IDLE":
                    return decision
            except Exception as e:
                logger.warning(f"DeepSeek falhou, tentando OpenAI como fallback: {e}")
        
        # Fallback para OpenAI
        return await self._call_openai(user_prompt)
    
    async def _call_openai(self, user_prompt: str, tried_fallback: bool = False) -> Optional[Dict[str, Any]]:
        """
        Chama a API OpenAI e retorna decisão parseada.
        
        Args:
            user_prompt: Prompt do usuário
            tried_fallback: Flag para evitar recursão infinita no fallback
        
        Returns:
            Dicionário com decisão ou None em caso de erro
        """
        try:
            logger.debug(f"Chamando OpenAI com prompt: {user_prompt[:100]}...")
            # CHAMADA ASSÍNCRONA - não bloqueia o event loop
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Resposta OpenAI: {content}")
            
            # Tenta parsear JSON
            # Remove markdown code blocks se houver
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            decision = json.loads(content)
            
            # Valida formato
            if "type" not in decision:
                logger.warning("Resposta OpenAI sem campo 'type'")
                return {"type": "IDLE", "value": None}
            
            if decision["type"] not in ["GOAL", "SAY", "IDLE"]:
                logger.warning(f"Tipo inválido: {decision['type']}")
                return {"type": "IDLE", "value": None}
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da OpenAI: {e}")
            return {"type": "IDLE", "value": None}
        
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            
            # Tenta fallback: gpt-3.5-turbo se erro for de modelo
            error_str = str(e)
            if not tried_fallback:
                if "model" in error_str.lower() and ("not found" in error_str.lower() or "does not exist" in error_str.lower()):
                    if self.model != "gpt-3.5-turbo":
                        logger.warning(f"Modelo {self.model} não disponível, tentando gpt-3.5-turbo como fallback...")
                        original_model = self.model
                        self.model = "gpt-3.5-turbo"
                        try:
                            return await self._call_openai(user_prompt, tried_fallback=True)
                        except Exception as e2:
                            logger.error(f"Erro também com gpt-3.5-turbo: {e2}")
                            self.model = original_model  # Restaura modelo original
            
            return {"type": "IDLE", "value": None}
    
    async def _call_deepseek(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Chama a API DeepSeek (primária).
        
        Args:
            user_prompt: Prompt do usuário
        
        Returns:
            Dicionário com decisão ou None em caso de erro
        """
        if not self.deepseek_client or not self.deepseek_config:
            return None
        
        try:
            deepseek_model = self.deepseek_config.get("model", "deepseek-chat")
            logger.debug(f"Chamando DeepSeek com modelo {deepseek_model}...")
            # CHAMADA ASSÍNCRONA - não bloqueia o event loop
            response = await self.deepseek_client.chat.completions.create(
                model=deepseek_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"Resposta DeepSeek: {content}")
            
            # Tenta parsear JSON
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
            
            decision = json.loads(content)
            
            # Valida formato
            if "type" not in decision:
                logger.warning("Resposta DeepSeek sem campo 'type'")
                return {"type": "IDLE", "value": None}
            
            if decision["type"] not in ["GOAL", "SAY", "IDLE"]:
                logger.warning(f"Tipo inválido da DeepSeek: {decision['type']}")
                return {"type": "IDLE", "value": None}
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON da DeepSeek: {e}")
            return {"type": "IDLE", "value": None}
        
        except Exception as e:
            logger.error(f"Erro ao chamar DeepSeek: {e}")
            return {"type": "IDLE", "value": None}
    
    def get_memory(self) -> Memory:
        """Retorna a instância de memória."""
        return self.memory
