"""
Dados do Pokémon Red/Blue - nomes, localizações, etc.
Usado para gerar comentários contextuais sobre o jogo.
"""

# Nomes dos Pokémon (índice = número do Pokédex)
# Índice 0 é vazio, índices 1-151 são os Pokémon da Geração 1
POKEMON_NAMES = [
    "",  # 0 - vazio
    "Bulbasaur", "Ivysaur", "Venusaur", "Charmander", "Charmeleon",
    "Charizard", "Squirtle", "Wartortle", "Blastoise", "Caterpie",
    "Metapod", "Butterfree", "Weedle", "Kakuna", "Beedrill",
    "Pidgey", "Pidgeotto", "Pidgeot", "Rattata", "Raticate",
    "Spearow", "Fearow", "Ekans", "Arbok", "Pikachu",
    "Raichu", "Sandshrew", "Sandslash", "Nidoran♀", "Nidorina",
    "Nidoqueen", "Nidoran♂", "Nidorino", "Nidoking", "Clefairy",
    "Clefable", "Vulpix", "Ninetales", "Jigglypuff", "Wigglytuff",
    "Zubat", "Golbat", "Oddish", "Gloom", "Vileplume",
    "Paras", "Parasect", "Venonat", "Venomoth", "Diglett",
    "Dugtrio", "Meowth", "Persian", "Psyduck", "Golduck",
    "Mankey", "Primeape", "Growlithe", "Arcanine", "Poliwag",
    "Poliwhirl", "Poliwrath", "Abra", "Kadabra", "Alakazam",
    "Machop", "Machoke", "Machamp", "Bellsprout", "Weepinbell",
    "Victreebel", "Tentacool", "Tentacruel", "Geodude", "Graveler",
    "Golem", "Ponyta", "Rapidash", "Slowpoke", "Slowbro",
    "Magnemite", "Magneton", "Farfetch'd", "Doduo", "Dodrio",
    "Seel", "Dewgong", "Grimer", "Muk", "Shellder",
    "Cloyster", "Gastly", "Haunter", "Gengar", "Onix",
    "Drowzee", "Hypno", "Krabby", "Kingler", "Voltorb",
    "Electrode", "Exeggcute", "Exeggutor", "Cubone", "Marowak",
    "Hitmonlee", "Hitmonchan", "Lickitung", "Koffing", "Weezing",
    "Rhyhorn", "Rhydon", "Chansey", "Tangela", "Kangaskhan",
    "Horsea", "Seadra", "Goldeen", "Seaking", "Staryu",
    "Starmie", "Mr. Mime", "Scyther", "Jynx", "Electabuzz",
    "Magmar", "Pinsir", "Tauros", "Magikarp", "Gyarados",
    "Lapras", "Ditto", "Eevee", "Vaporeon", "Jolteon",
    "Flareon", "Porygon", "Omanyte", "Omastar", "Kabuto",
    "Kabutops", "Aerodactyl", "Snorlax", "Articuno", "Zapdos",
    "Moltres", "Dratini", "Dragonair", "Dragonite", "Mewtwo",
    "Mew"  # 151
]

# Mapa de IDs internos da ROM para índice do Pokédex
# A ROM usa IDs diferentes dos números do Pokédex
INTERNAL_ID_TO_POKEDEX = {
    0x99: 1,   # Bulbasaur
    0x09: 2,   # Ivysaur
    0x9A: 3,   # Venusaur
    0xB0: 4,   # Charmander
    0xB2: 5,   # Charmeleon
    0xB4: 6,   # Charizard
    0xB1: 7,   # Squirtle
    0xB3: 8,   # Wartortle
    0x1C: 9,   # Blastoise
    0x7B: 10,  # Caterpie
    0x7C: 11,  # Metapod
    0x7D: 12,  # Butterfree
    0x70: 13,  # Weedle
    0x71: 14,  # Kakuna
    0x72: 15,  # Beedrill
    0x24: 16,  # Pidgey
    0x96: 17,  # Pidgeotto
    0x97: 18,  # Pidgeot
    0xA5: 19,  # Rattata
    0xA6: 20,  # Raticate
    0x05: 21,  # Spearow
    0x23: 22,  # Fearow
    0x6C: 23,  # Ekans
    0x2D: 24,  # Arbok
    0x54: 25,  # Pikachu
    0x55: 26,  # Raichu
    0x60: 27,  # Sandshrew
    0x61: 28,  # Sandslash
    0x0F: 29,  # Nidoran♀
    0xA8: 30,  # Nidorina
    0x10: 31,  # Nidoqueen
    0x03: 32,  # Nidoran♂
    0xA7: 33,  # Nidorino
    0x07: 34,  # Nidoking
    0x04: 35,  # Clefairy
    0x8E: 36,  # Clefable
    0x52: 37,  # Vulpix
    0x53: 38,  # Ninetales
    0x64: 39,  # Jigglypuff
    0x65: 40,  # Wigglytuff
    0x6B: 41,  # Zubat
    0x82: 42,  # Golbat
    0xB9: 43,  # Oddish
    0xBA: 44,  # Gloom
    0xBB: 45,  # Vileplume
    0x6D: 46,  # Paras
    0x2E: 47,  # Parasect
    0x41: 48,  # Venonat
    0x77: 49,  # Venomoth
    0x3B: 50,  # Diglett
    0x76: 51,  # Dugtrio
    0x4D: 52,  # Meowth
    0x90: 53,  # Persian
    0x2F: 54,  # Psyduck
    0x80: 55,  # Golduck
    0x39: 56,  # Mankey
    0x75: 57,  # Primeape
    0x21: 58,  # Growlithe
    0x14: 59,  # Arcanine
    0x47: 60,  # Poliwag
    0x6E: 61,  # Poliwhirl
    0x6F: 62,  # Poliwrath
    0x94: 63,  # Abra
    0x26: 64,  # Kadabra
    0x95: 65,  # Alakazam
    0x6A: 66,  # Machop
    0x29: 67,  # Machoke
    0x7E: 68,  # Machamp
    0xBC: 69,  # Bellsprout
    0xBD: 70,  # Weepinbell
    0xBE: 71,  # Victreebel
    0x18: 72,  # Tentacool
    0x9B: 73,  # Tentacruel
    0xA9: 74,  # Geodude
    0x27: 75,  # Graveler
    0x31: 76,  # Golem
    0xA3: 77,  # Ponyta
    0xA4: 78,  # Rapidash
    0x25: 79,  # Slowpoke
    0x08: 80,  # Slowbro
    0xAD: 81,  # Magnemite
    0x36: 82,  # Magneton
    0x40: 83,  # Farfetch'd
    0x46: 84,  # Doduo
    0x74: 85,  # Dodrio
    0x3A: 86,  # Seel
    0x78: 87,  # Dewgong
    0x0D: 88,  # Grimer
    0x88: 89,  # Muk
    0x17: 90,  # Shellder
    0x8B: 91,  # Cloyster
    0x19: 92,  # Gastly
    0x93: 93,  # Haunter
    0x0E: 94,  # Gengar
    0x22: 95,  # Onix
    0x30: 96,  # Drowzee
    0x81: 97,  # Hypno
    0x4E: 98,  # Krabby
    0x8A: 99,  # Kingler
    0x06: 100, # Voltorb
    0x8D: 101, # Electrode
    0x0C: 102, # Exeggcute
    0x0A: 103, # Exeggutor
    0x11: 104, # Cubone
    0x91: 105, # Marowak
    0x2B: 106, # Hitmonlee
    0x2C: 107, # Hitmonchan
    0x0B: 108, # Lickitung
    0x37: 109, # Koffing
    0x8F: 110, # Weezing
    0x12: 111, # Rhyhorn
    0x01: 112, # Rhydon
    0x28: 113, # Chansey
    0x1E: 114, # Tangela
    0x02: 115, # Kangaskhan
    0x5C: 116, # Horsea
    0x5D: 117, # Seadra
    0x9D: 118, # Goldeen
    0x9E: 119, # Seaking
    0x1B: 120, # Staryu
    0x98: 121, # Starmie
    0x2A: 122, # Mr. Mime
    0x1A: 123, # Scyther
    0x48: 124, # Jynx
    0x35: 125, # Electabuzz
    0x33: 126, # Magmar
    0x1D: 127, # Pinsir
    0x3C: 128, # Tauros
    0x85: 129, # Magikarp
    0x16: 130, # Gyarados
    0x13: 131, # Lapras
    0x4C: 132, # Ditto
    0x66: 133, # Eevee
    0x69: 134, # Vaporeon
    0x68: 135, # Jolteon
    0x67: 136, # Flareon
    0xAA: 137, # Porygon
    0x62: 138, # Omanyte
    0x63: 139, # Omastar
    0x5A: 140, # Kabuto
    0x5B: 141, # Kabutops
    0xAB: 142, # Aerodactyl
    0x84: 143, # Snorlax
    0x4A: 144, # Articuno
    0x4B: 145, # Zapdos
    0x49: 146, # Moltres
    0x58: 147, # Dratini
    0x59: 148, # Dragonair
    0x42: 149, # Dragonite
    0x83: 150, # Mewtwo
    0x15: 151, # Mew
}

# Nomes das localizações (Map IDs para Pokémon Red/Blue)
MAP_NAMES = {
    0: "Título/Menu",
    1: "Pallet Town",
    2: "Viridian City",
    3: "Pewter City",
    4: "Cerulean City",
    5: "Lavender Town",
    6: "Vermilion City",
    7: "Celadon City",
    8: "Fuchsia City",
    9: "Cinnabar Island",
    10: "Indigo Plateau",
    11: "Saffron City",
    12: "Route 1",
    13: "Route 2",
    14: "Route 3",
    15: "Route 4",
    16: "Route 5",
    17: "Route 6",
    18: "Route 7",
    19: "Route 8",
    20: "Route 9",
    21: "Route 10",
    22: "Route 11",
    23: "Route 12",
    24: "Route 13",
    25: "Route 14",
    26: "Route 15",
    27: "Route 16",
    28: "Route 17",
    29: "Route 18",
    30: "Route 19",
    31: "Route 20",
    32: "Route 21",
    33: "Route 22",
    34: "Route 23",
    35: "Route 24",
    36: "Route 25",
    37: "Player's House 1F",
    38: "Player's House 2F",
    39: "Rival's House",
    40: "Oak's Lab",
    41: "Pokémon Center (Viridian)",
    42: "PokéMart (Viridian)",
    43: "School (Viridian)",
    44: "Trainer's House (Viridian)",
    45: "Gym (Viridian)",
    46: "Digglet's Cave",
    47: "Viridian Forest",
    48: "Mt. Moon 1F",
    49: "Mt. Moon 2F",
    50: "Mt. Moon 3F",
    51: "Cerulean Cave 1F",
    52: "Cerulean Cave 2F",
    53: "Cerulean Cave 3F",
    54: "Pokémon Center (Pewter)",
    55: "Gym (Pewter)",
    56: "Pokémon Center (Cerulean)",
    57: "Gym (Cerulean)",
    58: "Silph Co. 1F",
    # ... mais locais podem ser adicionados
}

# Nomes dos badges
BADGE_NAMES = [
    "Boulder Badge",    # Brock
    "Cascade Badge",    # Misty
    "Thunder Badge",    # Lt. Surge
    "Rainbow Badge",    # Erika
    "Soul Badge",       # Koga
    "Marsh Badge",      # Sabrina
    "Volcano Badge",    # Blaine
    "Earth Badge",      # Giovanni
]


def get_pokemon_name(internal_id: int) -> str:
    """Retorna o nome do Pokémon baseado no ID interno da ROM."""
    if internal_id == 0:
        return ""
    
    pokedex_id = INTERNAL_ID_TO_POKEDEX.get(internal_id, 0)
    if 1 <= pokedex_id <= 151:
        return POKEMON_NAMES[pokedex_id]
    
    # Se não encontrou no mapeamento, tenta usar como índice direto
    if 1 <= internal_id <= 151:
        return POKEMON_NAMES[internal_id]
    
    return f"Pokémon #{internal_id}"


def get_map_name(map_id: int) -> str:
    """Retorna o nome da localização baseado no Map ID."""
    return MAP_NAMES.get(map_id, f"Local #{map_id}")


def get_badge_names(badge_byte: int) -> list:
    """Retorna lista de badges obtidas baseado no byte de badges."""
    badges = []
    for i in range(8):
        if badge_byte & (1 << i):
            badges.append(BADGE_NAMES[i])
    return badges


def get_badge_count(badge_byte: int) -> int:
    """Conta o número de badges."""
    return bin(badge_byte).count('1')
