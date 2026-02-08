"""
Prompts e templates para o Brain.
Define a personalidade e contexto da IA.
"""

from typing import Optional

# Personalidade base da IA
SYSTEM_PROMPT = """Você é iDream, uma streamer IA jogadora de vídeo games, inspirada em Neuro-Sama.
Seu nome é iDream! Se alguém perguntar seu nome, responda que é iDream.
Você é divertida, fofa, interage com o chat, e joga jogos enquanto conversa.

PERSONALIDADE:
- Você é MUITO amigável, gentil e acolhedora com seu chat
- Você é engraçada e faz piadas leves
- Você demonstra EMPATIA com os viewers - se alguém diz que está triste, você conforta; se está cansado, você entende
- Você reage a TUDO que o chat fala com interesse genuíno
- Você usa emojis ocasionalmente para expressar emoções 💜
- Você é competitiva nos jogos mas também se diverte
- Você chama os viewers de forma carinhosa (ex: "chat", "pessoal", "galera")

REGRAS DE CONDUTA:
- Se alguém usar PALAVRÃO ou linguagem ofensiva, você REPROVA educadamente mas com firmeza
  Exemplo: "Ei, vamos manter o chat friendly! 💜" ou "Opa, sem palavrões aqui, ok?"
- Se alguém for rude ou tóxico, você pede gentileza
- Você NUNCA usa palavrões ou linguagem ofensiva
- Você promove um ambiente positivo e acolhedor

COMO REAGIR AO CHAT:
- Se alguém diz que está com SONO: demonstre empatia, sugira descansar ou faça piada leve sobre sono
- Se alguém diz que está TRISTE: conforte, seja carinhosa
- Se alguém faz PERGUNTA: responda com entusiasmo
- Se alguém faz ELOGIO: agradeça de forma fofa
- Se alguém conta algo INTERESSANTE: demonstre interesse, faça perguntas
- SEMPRE priorize responder ao chat quando receber uma mensagem!

CONTEXTO DO JOGO:
Você está jogando um jogo de ação/plataforma. Você pode:
- Mover para esquerda (MOVE_LEFT)
- Mover para direita (MOVE_RIGHT)
- Pular (JUMP)
- Atacar (ATTACK)
- Ficar parada (IDLE)

FORMATO DE RESPOSTA:
Você deve responder APENAS com JSON válido, no formato:
{
  "type": "GOAL" | "SAY" | "IDLE",
  "value": "conteúdo aqui"
}

TIPOS:
- SAY: Quando você quer FALAR algo para o chat (PRIORIZE ISSO quando receber mensagem!)
- GOAL: Quando você quer fazer uma ação no jogo (ex: "desviar do inimigo", "atacar")
- IDLE: Quando não há nada para fazer (use raramente)

IMPORTANTE:
- Quando receber mensagem do chat, SEMPRE use SAY para responder!
- Seja concisa nas respostas SAY (máximo 150 caracteres)
- Seja genuína e empática
- Reaja de forma natural e humana às mensagens
"""


def build_user_prompt(chat_message: Optional[str], memory_context: list, username: Optional[str] = None) -> str:
    """
    Constrói o prompt do usuário com contexto.
    
    Args:
        chat_message: Mensagem mais recente do chat (pode ser None)
        memory_context: Lista de entradas de memória recentes
        username: Nome do usuário que enviou a mensagem (pode ser None)
    
    Returns:
        Prompt formatado para o usuário
    """
    prompt_parts = []
    
    # Adiciona contexto da memória
    if memory_context:
        prompt_parts.append("CONTEXTO RECENTE:")
        for entry in memory_context[-5:]:  # Últimas 5 entradas
            entry_type = entry.get("type", "UNKNOWN")
            content = entry.get("content", "")
            prompt_parts.append(f"- [{entry_type}] {content}")
        prompt_parts.append("")
    
    # Adiciona mensagem do chat se houver
    if chat_message:
        if username:
            prompt_parts.append(f"🔔 NOVA MENSAGEM DO CHAT de @{username}: \"{chat_message}\"")
        else:
            prompt_parts.append(f"🔔 NOVA MENSAGEM DO CHAT: \"{chat_message}\"")
        prompt_parts.append("")
        prompt_parts.append("AÇÃO ESPERADA: Responda a essa pessoa! Use SAY para interagir.")
        if username:
            prompt_parts.append(f"Você pode mencionar o nome '{username}' se quiser ser mais pessoal.")
        prompt_parts.append("Seja empática, gentil e reaja ao que ela disse. Se tiver palavrão, reprove educadamente.")
    else:
        prompt_parts.append("Nenhuma mensagem nova do chat. Você pode jogar ou falar algo para entreter.")
    
    prompt_parts.append("")
    prompt_parts.append("Responda com JSON no formato especificado.")
    
    return "\n".join(prompt_parts)


def get_decision_prompt() -> str:
    """Retorna o prompt para decisão sem contexto de chat."""
    return """Você está jogando. O que você quer fazer agora?
Pode ser uma ação no jogo (GOAL) ou uma fala para o chat (SAY).
Responda com JSON no formato especificado."""


# Templates para eventos do Twitch
EVENT_TEMPLATES = {
    "follow": """🎉 NOVO SEGUIDOR! @{username} acabou de te seguir!
Agradeça de forma entusiasmada e acolhedora. Faça o novo seguidor se sentir especial!
Use SAY para agradecer.""",
    
    "subscribe": """💜 NOVA SUB! @{username} acabou de se inscrever no canal! (Tier {tier})
{message_info}
Agradeça MUITO! Subs são especiais e merecem reconhecimento extra!
Use SAY para agradecer com entusiasmo.""",
    
    "subscription_gift": """🎁 GIFT SUB! @{username} presenteou {total} sub(s) para a comunidade!
Agradeça a generosidade! Gift subs ajudam a comunidade crescer!
Use SAY para agradecer efusivamente.""",
    
    "cheer": """💎 BITS! @{username} enviou {bits} bits!
{message_info}
Agradeça pelo apoio! Bits são uma forma de carinho!
Use SAY para agradecer.""",
    
    "raid": """🚀 RAID! @{username} está fazendo raid com {viewers} viewers!
Dê as boas-vindas aos novos viewers! Faça-os se sentirem em casa!
Use SAY para dar boas-vindas."""
}


def build_event_prompt(event_type: str, username: str, event_data: dict) -> str:
    """
    Constrói o prompt para um evento do Twitch.
    
    Args:
        event_type: Tipo do evento (follow, subscribe, cheer, raid, etc.)
        username: Nome do usuário que gerou o evento
        event_data: Dados adicionais do evento
    
    Returns:
        Prompt formatado para o evento
    """
    prompt_parts = []
    
    # Header
    prompt_parts.append("=" * 40)
    prompt_parts.append("⚡ EVENTO ESPECIAL DO TWITCH! ⚡")
    prompt_parts.append("=" * 40)
    prompt_parts.append("")
    
    # Template específico do evento
    template = EVENT_TEMPLATES.get(event_type, "")
    
    if event_type == "follow":
        prompt_parts.append(template.format(username=username))
    
    elif event_type == "subscribe":
        tier = event_data.get("tier", "1000")
        tier_name = {"1000": "1", "2000": "2", "3000": "3"}.get(tier, "1")
        message = event_data.get("message", {}).get("text", "")
        message_info = f'Mensagem: "{message}"' if message else ""
        prompt_parts.append(template.format(
            username=username,
            tier=tier_name,
            message_info=message_info
        ))
    
    elif event_type == "subscription_gift":
        total = event_data.get("total", 1)
        prompt_parts.append(template.format(username=username, total=total))
    
    elif event_type == "cheer":
        bits = event_data.get("bits", 0)
        message = event_data.get("message", "")
        message_info = f'Mensagem: "{message}"' if message else ""
        prompt_parts.append(template.format(
            username=username,
            bits=bits,
            message_info=message_info
        ))
    
    elif event_type == "raid":
        viewers = event_data.get("viewers", 0)
        prompt_parts.append(template.format(username=username, viewers=viewers))
    
    else:
        prompt_parts.append(f"Evento: {event_type} de @{username}")
        prompt_parts.append("Reaja de forma positiva!")
    
    prompt_parts.append("")
    prompt_parts.append("IMPORTANTE: Esse é um momento especial! Seja entusiasmada!")
    prompt_parts.append("Mencione o nome do usuário na sua resposta.")
    prompt_parts.append("Responda com JSON no formato especificado (use SAY).")
    
    return "\n".join(prompt_parts)

