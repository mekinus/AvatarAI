# ROM Directory

Place your Game Boy ROM files here.

Due to copyright restrictions, no ROMs are included in this repository.

### Setup Instructions
1. Obtain a legally owned copy of the game ROM (e.g. `pokemon_red.gb`).
2. Place the file in this directory.
3. Update `python_ai/config/config.json` to point to your ROM file:

```json
"pokemon": {
  "rom_path": "roms/your_rom_name.gb"
}
```

**Note:** The `.gitignore` file is configured to exclude common ROM extensions (.gb, .gbc, .gba) to prevent accidental commits of copyrighted material.
