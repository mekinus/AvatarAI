# Scripts Unity - Sistema de Streamer IA

## Setup no Unity

### 1. WebSocketServer

1. Crie um GameObject vazio na cena
2. Adicione o componente `WebSocketServer`
3. Configure a porta (padrão: 8765)
4. Marque `Auto Start` se quiser que inicie automaticamente

### 2. GameCommandReceiver

1. Adicione o componente `GameCommandReceiver` ao GameObject do player
2. Configure a referência ao `WebSocketServer` (ou deixe vazio para buscar automaticamente)
3. Configure `Move Speed`, `Jump Force` e `Attack Duration` conforme necessário
4. O player precisa ter um `Rigidbody` para ações de movimento e pulo funcionarem

### 3. AvatarController

1. Adicione o componente `AvatarController` ao GameObject do avatar
2. Configure a referência ao `WebSocketServer`
3. Configure a referência ao `SimpleLipSync` (ou deixe vazio para buscar automaticamente)
4. Configure o `SkinnedMeshRenderer` do rosto do avatar
5. Configure os índices dos blend shapes de emoção:
   - Happy
   - Angry
   - Sad
   - Surprised
   
   Ou deixe em -1 para buscar automaticamente por nome

### 4. SimpleLipSync

1. Adicione o componente `SimpleLipSync` ao GameObject do avatar
2. Configure o `SkinnedMeshRenderer` do rosto
3. Configure os índices dos blend shapes de fonemas:
   - A, E, I, O, U
   
   Ou deixe em -1 para buscar automaticamente por nome
4. Ajuste `Character Duration` e `Blend Shape Intensity` conforme necessário

## Formato de Mensagens

O sistema recebe mensagens JSON no formato:

```json
{"cmd": "ACTION", "value": "JUMP", "timestamp": 1234567890.0}
{"cmd": "SAY", "value": "Olá chat!", "timestamp": 1234567890.0}
{"cmd": "EMOTION", "value": "Happy", "duration": 2.0, "timestamp": 1234567890.0}
```

## Ações Disponíveis

- `MOVE_LEFT` - Move para esquerda
- `MOVE_RIGHT` - Move para direita
- `JUMP` - Pula
- `ATTACK` - Ataca
- `IDLE` - Para movimento

## Emoções Disponíveis

- `Happy` / `Feliz`
- `Angry` / `Bravo` / `Raiva`
- `Sad` / `Triste`
- `Surprised` / `Surprise` / `Surpresa`

