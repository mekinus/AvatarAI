<p align="center">
  <img src="https://img.shields.io/badge/Unity-2022.3%2B-black?style=for-the-badge&logo=unity" alt="Unity" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Twitch-Integration-9146FF?style=for-the-badge&logo=twitch&logoColor=white" alt="Twitch" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

<h1 align="center">🎮 AvatarAI</h1>

<p align="center">
  <strong>An AI-Powered Virtual Streamer that plays games and interacts with Twitch Chat</strong>
</p>

<p align="center">
  Inspired by Neuro-Sama, AvatarAI is a complete system for creating an AI streamer that plays games (like Pokémon) in real-time while interacting with your Twitch audience through a 3D avatar.
</p>

---

## ✨ Features

- 🧠 **AI Brain** - Powered by OpenAI/DeepSeek for intelligent decision making
- 🎮 **Game Playing** - Plays Game Boy games using PyBoy with Reinforcement Learning
- 💬 **Twitch Integration** - Full chat interaction with spam filtering
- 🎭 **3D Avatar** - Unity-powered animated avatar with lip-sync
- 🗣️ **Text-to-Speech** - ElevenLabs integration for natural voice
- 📺 **Real-time Commentary** - AI comments on gameplay events
- 🎉 **Event Reactions** - Responds to follows, subs, cheers, and raids

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PYTHON BACKEND                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    │
│   │ Chat Layer  │───▶│ Brain Layer │───▶│ Planner Layer   │    │
│   │  (Twitch)   │    │  (OpenAI)   │    │ (Game Actions)  │    │
│   └─────────────┘    └─────────────┘    └────────┬────────┘    │
│                                                   │             │
│   ┌─────────────┐    ┌─────────────┐              │             │
│   │ Vision Layer│    │  RL Layer   │◀─────────────┤             │
│   │ (Detection) │    │  (PyBoy)    │              │             │
│   └─────────────┘    └─────────────┘              │             │
│                                                   │             │
└───────────────────────────────────────────────────┼─────────────┘
                                                    │
                              WebSocket Connection  │
                                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         UNITY FRONTEND                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐    ┌─────────────────┐                   │
│   │ Avatar Controller│    │ WebSocket Server │                   │
│   │   + Lip Sync    │◀───│  (Receives Cmds) │                   │
│   └─────────────────┘    └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.10+**
- **Unity 2022.3 LTS** or newer
- **A Twitch Account** with developer access
- **API Keys** for:
  - OpenAI or DeepSeek (for AI brain)
  - ElevenLabs (for text-to-speech, optional)
  - Twitch OAuth token

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/mekinus/AvatarAI.git
cd AvatarAI
```

### Step 2: Set Up Python Environment

```bash
cd python_ai

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure the Application

1. Copy the example config:
```bash
cp config/config.example.json config/config.json
```

2. Edit `config/config.json` with your credentials:
```json
{
  "twitch": {
    "token": "oauth:YOUR_OAUTH_TOKEN",
    "channel": "your_channel",
    "username": "your_bot_username",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  },
  "openai": {
    "api_key": "sk-YOUR_API_KEY"
  },
  "elevenlabs": {
    "api_key": "sk_YOUR_API_KEY"
  }
}
```

### Step 4: Add Your Game ROM

> ⚠️ **IMPORTANT**: You must provide your own ROM file. We do not distribute or support piracy.

1. Obtain a legal copy of your game ROM (e.g., from cartridges you own)
2. Place it in `python_ai/roms/` folder
3. Update the `rom_path` in `config/config.json`

```json
{
  "pokemon": {
    "rom_path": "roms/your_game.gb"
  }
}
```

### Step 5: Set Up Unity

1. Open the `AvatarAI` folder in Unity Hub
2. Import your 3D avatar model (VRM or FBX format)
3. Configure the components:
   - Add `WebSocketServer` to an empty GameObject
   - Add `GameCommandReceiver` to your player object
   - Add `AvatarController` and `SimpleLipSync` to your avatar
4. Configure blend shapes in the Inspector

---

## 🎮 Usage

### Running the System

1. **Start Unity** - Press Play in the Unity Editor (or build the project)

2. **Start the Python Backend**:
```bash
cd python_ai
python main.py
```

3. **Watch the magic happen!** The AI will:
   - Connect to your Twitch chat
   - Start playing the game
   - Respond to chat messages
   - Comment on gameplay events

### Manual Control

While the AI is running, you can:
- Type in the terminal to manually control the game
- Use chat commands to interact with the AI
- Toggle between AI and manual control

---

## ⚙️ Configuration Options

### Twitch Settings

| Key | Description |
|-----|-------------|
| `token` | OAuth token (get from [twitchtokengenerator.com](https://twitchtokengenerator.com)) |
| `channel` | Your Twitch channel name |
| `username` | Bot's Twitch username |
| `client_id` | Twitch Developer Application Client ID |
| `client_secret` | Twitch Developer Application Client Secret |

### Game Settings

| Key | Description | Default |
|-----|-------------|---------|
| `rom_path` | Path to your game ROM | `roms/pokemon_red.gb` |
| `headless` | Run without display | `false` |
| `speed` | Emulation speed multiplier | `1` |
| `rl_enabled` | Use reinforcement learning | `true` |
| `vision_enabled` | Use computer vision | `false` |

### Gameplay Commentary

| Key | Description | Default |
|-----|-------------|---------|
| `enabled` | Enable gameplay comments | `true` |
| `game_events_only` | Only comment on game events | `true` |
| `min_interval_seconds` | Minimum time between comments | `30` |
| `send_to_chat` | Send comments to Twitch chat | `false` |

---

## 📁 Project Structure

```
AvatarAI/
├── 📁 AvatarAI/              # Unity Project
│   ├── Assets/               # Unity assets & scripts
│   ├── Packages/             # Unity packages
│   └── ProjectSettings/      # Unity settings
│
├── 📁 python_ai/             # Python Backend
│   ├── brain_layer/          # AI decision making (OpenAI)
│   ├── chat_layer/           # Twitch chat integration
│   ├── config/               # Configuration files
│   ├── game_layer/           # Game control & commentary
│   ├── planner_layer/        # Action planning & Unity client
│   ├── rl_layer/             # Reinforcement learning
│   ├── roms/                 # ⚠️ Your game ROMs (not included)
│   ├── state_machine/        # AI state management
│   ├── tts_layer/            # Text-to-speech
│   ├── vision_layer/         # Computer vision
│   └── main.py               # Main entry point
│
└── 📄 README.md              # This file
```

---

## 🔑 Getting API Keys

### Twitch

1. Go to [dev.twitch.tv](https://dev.twitch.tv)
2. Create a new application
3. Get your Client ID and Client Secret
4. Generate an OAuth token at [twitchtokengenerator.com](https://twitchtokengenerator.com)

### OpenAI

1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account and add billing
3. Generate an API key

### ElevenLabs (Optional)

1. Go to [elevenlabs.io](https://elevenlabs.io)
2. Create a free account
3. Get your API key from settings

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⚠️ Legal Disclaimer

- **ROMs**: This project does NOT include any game ROMs. You must provide your own legally obtained ROM files.
- **Trademarks**: Pokémon and Game Boy are trademarks of Nintendo. This project is not affiliated with or endorsed by Nintendo.
- **API Usage**: Ensure you comply with the Terms of Service of all third-party APIs (Twitch, OpenAI, ElevenLabs).

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by [Neuro-Sama](https://www.twitch.tv/vedal987)
- Built with [PyBoy](https://github.com/Baekalfen/PyBoy) for Game Boy emulation
- Uses [Stable-Baselines3](https://github.com/DLR-RM/stable-baselines3) for RL

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/mekinus">@mekinus</a>
</p>
