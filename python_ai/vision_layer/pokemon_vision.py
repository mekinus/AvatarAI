"""
Sistema de visão para Pokémon usando CLIP.
Classifica o estado visual do jogo sem necessidade de treinamento.
"""

import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class GameScreen(Enum):
    """Estados de tela do jogo."""
    UNKNOWN = "unknown"
    OVERWORLD = "overworld"
    BATTLE = "battle"
    MENU = "menu"
    DIALOG = "dialog"
    TITLE = "title"
    VICTORY = "victory"
    FAINTED = "fainted"
    CUTSCENE = "cutscene"
    EVOLUTION = "evolution"
    POKEMON_CENTER = "pokemon_center"


# Prompts para CLIP classificar cada estado
CLIP_PROMPTS = {
    GameScreen.OVERWORLD: [
        "pokemon game overworld map",
        "player walking in pokemon game",
        "top down rpg game world",
    ],
    GameScreen.BATTLE: [
        "pokemon battle screen",
        "pokemon fighting enemy",
        "turn based battle rpg",
    ],
    GameScreen.MENU: [
        "pokemon game menu screen",
        "rpg inventory menu",
        "game pause menu",
    ],
    GameScreen.DIALOG: [
        "game dialog text box",
        "npc talking text",
        "rpg conversation screen",
    ],
    GameScreen.TITLE: [
        "pokemon title screen",
        "game start menu",
        "press start screen",
    ],
    GameScreen.VICTORY: [
        "pokemon victory screen",
        "you won battle screen",
        "enemy fainted text",
    ],
    GameScreen.FAINTED: [
        "pokemon fainted screen",
        "game over screen",
        "all pokemon fainted",
    ],
    GameScreen.EVOLUTION: [
        "pokemon evolution screen",
        "pokemon evolving animation",
    ],
    GameScreen.POKEMON_CENTER: [
        "pokemon center healing",
        "nurse joy pokemon center",
    ],
}


class PokemonVision:
    """Detector de estados visuais usando CLIP."""
    
    def __init__(self, device: str = "auto"):
        """
        Args:
            device: "cuda", "cpu" ou "auto"
        """
        self.device = device
        self.model = None
        self.processor = None
        self.text_features = None
        self.text_features_tensor = None
        self.screen_labels = []
        self._initialized = False
        
        logger.info(f"PokemonVision inicializado (device: {device})")
    
    def initialize(self) -> bool:
        """Carrega o modelo CLIP."""
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel
            
            # Determina device
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Carregando CLIP no device: {self.device}")
            
            # Carrega modelo e processor
            model_name = "openai/clip-vit-base-patch32"
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.model.eval()
            
            # Pré-computa features de texto para cada estado
            self._precompute_text_features()
            
            self._initialized = True
            logger.info("CLIP carregado com sucesso")
            return True
            
        except ImportError as e:
            logger.error(f"Dependências faltando: {e}")
            logger.error("Instale com: pip install transformers torch")
            return False
        except Exception as e:
            logger.error(f"Erro ao carregar CLIP: {e}")
            return False
    
    def _precompute_text_features(self):
        """Pré-computa embeddings de texto para eficiência."""
        import torch
        
        self.text_features_map = {}
        tensor_list = []
        self.screen_labels = []
        
        # Garante ordem determinística
        for screen_type, prompts in CLIP_PROMPTS.items():
            # Processa todos os prompts para este estado
            inputs = self.processor(
                text=prompts,
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                features = self.model.get_text_features(**inputs)
                # Média dos embeddings dos prompts
                embedding = features.mean(dim=0)
                
                # Armazena na lista para criar tensor único
                tensor_list.append(embedding)
                self.screen_labels.append(screen_type)
        
        # Cria tensor único (N, D) para cálculo batched
        if tensor_list:
            self.text_features_tensor = torch.stack(tensor_list)
            logger.info(f"Pré-computados embeddings para {len(self.screen_labels)} estados no device {self.device}")
        else:
            self.text_features_tensor = None
            logger.warning("Nenhum embedding de texto gerado")
    
    def classify_frame(self, frame: np.ndarray) -> Tuple[GameScreen, float]:
        """
        Classifica um frame do jogo.
        
        Args:
            frame: Imagem numpy RGB
        
        Returns:
            (estado_detectado, confiança)
        """
        if not self._initialized:
            logger.warning("Modelo não inicializado")
            return GameScreen.UNKNOWN, 0.0
        
        try:
            import torch
            from PIL import Image
            
            # Converte numpy para PIL
            if isinstance(frame, np.ndarray):
                image = Image.fromarray(frame)
            else:
                image = frame
            
            # Processa imagem
            inputs = self.processor(
                images=image,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            if self.text_features_tensor is None:
                return GameScreen.UNKNOWN, 0.0

            # Similaridade Batched (1 readback vs N readbacks)
            # image_features: (1, D)
            # text_features_tensor: (N, D)
            # Result: (1, N) -> flatten -> (N,)
            similarities = torch.nn.functional.cosine_similarity(
                image_features,
                self.text_features_tensor,
                dim=1
            )
            
            # Único ponto de sincronização GPU->CPU
            scores = similarities.cpu().numpy()
            
            # Encontra melhor match
            best_idx = scores.argmax()
            best_score = float(scores[best_idx])
            best_match = self.screen_labels[best_idx]
            
            # Normaliza score para 0-1
            confidence = (best_score + 1) / 2
            
            return best_match, confidence
            
        except Exception as e:
            logger.error(f"Erro ao classificar frame: {e}")
            return GameScreen.UNKNOWN, 0.0
    
    def detect_low_hp(self, frame: np.ndarray, threshold: float = 0.3) -> bool:
        """
        Detecta se há barra de HP baixo (vermelha) no frame.
        
        Args:
            frame: Imagem numpy RGB
            threshold: Proporção de vermelho para considerar HP baixo
        
        Returns:
            True se HP baixo detectado
        """
        try:
            # Região típica da barra de HP no Pokémon (parte superior)
            hp_region = frame[10:50, 10:80]
            
            # Detecta pixels vermelhos (HP baixo)
            red = hp_region[:, :, 0]
            green = hp_region[:, :, 1]
            blue = hp_region[:, :, 2]
            
            # Vermelho dominante
            red_mask = (red > 150) & (green < 100) & (blue < 100)
            red_ratio = np.sum(red_mask) / red_mask.size
            
            return red_ratio > threshold
            
        except Exception as e:
            logger.error(f"Erro ao detectar HP baixo: {e}")
            return False
    
    def detect_text_box(self, frame: np.ndarray) -> bool:
        """
        Detecta se há caixa de texto na tela.
        
        Args:
            frame: Imagem numpy RGB
        
        Returns:
            True se caixa de texto detectada
        """
        try:
            # Região inferior onde fica texto (Game Boy: 160x144)
            text_region = frame[-48:, :]  # Últimas 48 linhas
            
            # Caixa de texto é majoritariamente branca
            white_mask = np.all(text_region > 200, axis=2)
            white_ratio = np.sum(white_mask) / white_mask.size
            
            # Se >50% branco na região, provavelmente é caixa de texto
            return white_ratio > 0.5
            
        except Exception as e:
            logger.error(f"Erro ao detectar caixa de texto: {e}")
            return False
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """
        Análise completa de um frame.
        
        Args:
            frame: Imagem numpy RGB
        
        Returns:
            Dicionário com análise completa
        """
        screen_type, confidence = self.classify_frame(frame)
        
        return {
            "screen_type": screen_type,
            "confidence": confidence,
            "has_low_hp": self.detect_low_hp(frame),
            "has_text_box": self.detect_text_box(frame),
        }


class SimplePokemonVision:
    """
    Versão simplificada sem CLIP.
    Usa apenas análise de cores/padrões.
    Útil se não tiver GPU ou quiser baixa latência.
    """
    
    def __init__(self):
        self._initialized = True
        logger.info("SimplePokemonVision inicializado (sem CLIP)")
    
    def initialize(self) -> bool:
        return True
    
    def classify_frame(self, frame: np.ndarray) -> Tuple[GameScreen, float]:
        """Classificação básica por análise de cores."""
        try:
            # Analisa cores dominantes
            avg_color = np.mean(frame, axis=(0, 1))
            
            # Tela de batalha tem mais preto (fundo)
            if np.mean(frame) < 100:
                return GameScreen.BATTLE, 0.7
            
            # Tela majoritariamente branca = menu/dialog
            if np.mean(frame) > 200:
                if self._has_text_box(frame):
                    return GameScreen.DIALOG, 0.6
                return GameScreen.MENU, 0.5
            
            # Default: overworld
            return GameScreen.OVERWORLD, 0.5
            
        except Exception:
            return GameScreen.UNKNOWN, 0.0
    
    def _has_text_box(self, frame: np.ndarray) -> bool:
        """Detecta caixa de texto."""
        text_region = frame[-48:, :]
        white_ratio = np.mean(text_region > 200)
        return white_ratio > 0.5
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """Análise básica."""
        screen_type, confidence = self.classify_frame(frame)
        return {
            "screen_type": screen_type,
            "confidence": confidence,
            "has_low_hp": False,  # Não detecta sem CLIP
            "has_text_box": self._has_text_box(frame),
        }

