# Sistema de Streamer IA Jogadora

Sistema completo de streamer IA inspirado em Neuro-Sama, com arquitetura desacoplada em 4 camadas.

## Arquitetura

```
Chat Layer (Python) → Brain Layer (Python) → Planner Layer (Python) → Unity (C#)
                                                      ↓
                                              Avatar Layer (Unity)
```

## Instalação

1. Instale as dependências Python:
```bash
pip install -r requirements.txt
```

2. Configure o arquivo `config/config.json`:
   - Adicione seu token do Twitch (OAuth)
   - Configure canal e username do bot
   - Adicione sua chave da API OpenAI
   - Ajuste configurações do Unity (host e porta)

3. No Unity:
   - Adicione os scripts C# nas pastas apropriadas
   - Configure os componentes no GameObject:
     - `WebSocketServer` em um GameObject vazio
     - `GameCommandReceiver` no player
     - `AvatarController` e `SimpleLipSync` no avatar
   - Configure os blend shapes no Inspector

## Uso

Execute o sistema Python:
```bash
python main.py
```

O sistema irá:
1. Conectar ao Twitch chat
2. Conectar ao Unity via WebSocket
3. Processar mensagens do chat
4. Fazer decisões usando OpenAI
5. Executar ações no jogo

## Estrutura

- `chat_layer/` - Escuta e filtra mensagens do Twitch
- `brain_layer/` - Processa decisões usando OpenAI
- `planner_layer/` - Converte objetivos em ações
- `state_machine/` - Gerencia estados da IA
- `config/` - Arquivos de configuração
- `main.py` - Loop principal

## Configuração

Edite `config/config.json` para ajustar:
- Credenciais do Twitch
- Chave da API OpenAI
- Modelo de IA (gpt-4, gpt-3.5-turbo, etc.)
- Rate limits
- Configurações do Unity

## Logs

Logs são salvos em `avatar_ai.log` e também exibidos no console.

