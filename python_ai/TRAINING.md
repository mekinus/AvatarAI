# 🧠 Guia de Treinamento da IA (Reinforcement Learning)

Este documento explica como treinar o agente de Reinforcement Learning (RL) para jogar Pokémon Red e os desafios conhecidos.

## 🚀 Como Treinar

O sistema usa **Proximal Policy Optimization (PPO)** através da biblioteca `stable-baselines3` em conjunto com o emulador `PyBoy`.

### Comando de Treinamento

Para iniciar o treinamento, certifique-se de que a configuração `rl_enabled` está `true` em `config.json` e execute:

```bash
python main.py --train
```
*(Nota: O argumento `--train` precisa ser implementado se ainda não existir, ou configure o script para modo de treinamento dedicadado)*

### Configuração de Hiperparâmetros

Os hiperparâmetros do modelo PPO podem ser ajustados em `python_ai/rl_layer/agent.py` (ou onde o modelo é instanciado):

- **learning_rate**: Taxa de aprendizado (padrão: `0.0003`)
- **n_steps**: Passos por atualização (padrão: `2048`)
- **batch_size**: Tamanho do lote (padrão: `64`)
- **gamma**: Fator de desconto (padrão: `0.99`)

## ⚠️ Problemas Conhecidos (Known Issues)

Durante o treinamento e inferência, o agente pode apresentar os seguintes comportamentos:

### 1. 🔄 Ficar preso em cantos ou loops
**Sintoma:** O personagem anda em círculos ou fica batendo na parede repetidamente.
**Causa:** O agente encontrou um máximo local de recompensa ou não sabe como proceder para a próxima área.
**Solução:**
- **Intervenção Manual:** Tome o controle do jogo temporariamente para mover o personagem para uma nova área.
- **Ajuste de Recompensa:** Incentive a exploração (exploration bonus) no código de recompensa.

### 2. 🛑 Menus e Diálogos Infinitos
**Sintoma:** O agente fica preso em menus de batalha ou diálogos de texto.
**Causa:** O estado visual de menus é complexo e o agente pode não ter aprendido a sequência correta de botões (A/B) para sair.
**Solução:** Pressione 'A' ou 'B' manualmente para avançar o texto.

### 3. 📉 Estagnação do Aprendizado
**Sintoma:** A recompensa média não sobe após milhões de passos.
**Causa:** O ambiente de Pokémon é vasto e com recompensas esparsas (sparse rewards).
**Solução:** Carregar `save states` de pontos mais avançados do jogo para treinar o agente em cenários variados, em vez de sempre começar do início (Pallet Town).

## 🎮 Intervenção Manual

A qualquer momento, você pode assumir o controle se o agente estiver travado.

1. Foque na janela do emulador/jogo.
2. Use as teclas configuradas (padrão: Setas + Z/X para A/B).
3. Após desbloquear o personagem, solte os controles para a IA retomar.

## 📦 Dependências Externas Proprietárias

Este projeto pode utilizar plugins Unity de terceiros, como **KlakNDI**, para captura de vídeo e streaming.
- Se você não tiver acesso a esse pacote, funcionalidades de vídeo NDI não funcionarão.
- Certifique-se de ter os direitos de uso de qualquer plugin proprietário adicionado ao projeto.
