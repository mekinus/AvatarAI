using System;
using UnityEngine;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Controla o avatar: emoções, fala e animações.
    /// Recebe comandos SAY e EMOTION do WebSocket.
    /// </summary>
    public class AvatarController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Networking.WebSocketServer webSocketServer;
        [SerializeField] private SimpleLipSync lipSync;
        [SerializeField] private TTSAudioPlayer ttsAudioPlayer;
        [SerializeField] private AvatarAnimationController animationController;
        
        [Header("Blend Shapes")]
        [SerializeField] private SkinnedMeshRenderer faceMeshRenderer;
        
        // Índices dos blend shapes (configurar no Inspector ou buscar por nome)
        [Header("Emotion Blend Shapes")]
        [SerializeField] private int happyBlendShapeIndex = -1;
        [SerializeField] private int angryBlendShapeIndex = -1;
        [SerializeField] private int sadBlendShapeIndex = -1;
        [SerializeField] private int surprisedBlendShapeIndex = -1;
        
        [Header("Settings")]
        [SerializeField] private float defaultEmotionDuration = 2f;
        [SerializeField] private float emotionTransitionSpeed = 5f;
        
        [Header("Debug")]
        [SerializeField] private bool logCommands = true;
        
        private float currentEmotionValue = 0f;
        private int currentEmotionIndex = -1;
        private float emotionEndTime = 0f;
        
        private void Start()
        {
            // Busca referências se não foram configuradas
            if (webSocketServer == null)
            {
                webSocketServer = FindObjectOfType<Networking.WebSocketServer>();
            }
            
            if (webSocketServer != null)
            {
                webSocketServer.OnMessageReceived += HandleMessage;
            }
            else
            {
                Debug.LogError("WebSocketServer não encontrado!");
            }
            
            if (lipSync == null)
            {
                lipSync = GetComponent<SimpleLipSync>();
            }
            
            // Busca ou cria TTSAudioPlayer
            if (ttsAudioPlayer == null)
            {
                ttsAudioPlayer = GetComponent<TTSAudioPlayer>();
                if (ttsAudioPlayer == null)
                {
                    ttsAudioPlayer = gameObject.AddComponent<TTSAudioPlayer>();
                }
            }
            
            // Busca ou cria AvatarAnimationController
            if (animationController == null)
            {
                animationController = GetComponent<AvatarAnimationController>();
            }
            
            // Conecta eventos do TTS para sincronizar animação
            if (ttsAudioPlayer != null)
            {
                ttsAudioPlayer.OnAudioStarted += OnTTSAudioStarted;
                ttsAudioPlayer.OnAudioFinished += OnTTSAudioFinished;
            }
            
            // Busca face mesh se não foi configurado
            if (faceMeshRenderer == null)
            {
                faceMeshRenderer = GetComponentInChildren<SkinnedMeshRenderer>();
            }
            
            // Tenta encontrar blend shapes por nome se índices não foram configurados
            if (faceMeshRenderer != null)
            {
                FindBlendShapesByName();
            }
        }
        
        private void FindBlendShapesByName()
        {
            if (faceMeshRenderer == null || faceMeshRenderer.sharedMesh == null)
            {
                return;
            }
            
            var mesh = faceMeshRenderer.sharedMesh;
            
            // Busca blend shapes por nome comum
            for (int i = 0; i < mesh.blendShapeCount; i++)
            {
                string name = mesh.GetBlendShapeName(i).ToLower();
                
                if (happyBlendShapeIndex == -1 && (name.Contains("happy") || name.Contains("smile") || name.Contains("feliz")))
                {
                    happyBlendShapeIndex = i;
                }
                if (angryBlendShapeIndex == -1 && (name.Contains("angry") || name.Contains("bravo") || name.Contains("raiva")))
                {
                    angryBlendShapeIndex = i;
                }
                if (sadBlendShapeIndex == -1 && (name.Contains("sad") || name.Contains("triste")))
                {
                    sadBlendShapeIndex = i;
                }
                if (surprisedBlendShapeIndex == -1 && (name.Contains("surprised") || name.Contains("surpresa") || name.Contains("surprise")))
                {
                    surprisedBlendShapeIndex = i;
                }
            }
        }
        
        private void HandleMessage(string message)
        {
            try
            {
                GameCommand command = JsonUtility.FromJson<GameCommand>(message);
                
                if (command == null || string.IsNullOrEmpty(command.cmd))
                {
                    return;
                }
                
                if (logCommands)
                {
                    Debug.Log($"Avatar recebeu: {command.cmd} = {command.value}");
                }
                
                switch (command.cmd.ToUpper())
                {
                    case "SAY":
                        HandleSay(command.value, command.audio_data, command.audio_format);
                        break;
                    
                    case "EMOTION":
                        float duration = command.duration ?? defaultEmotionDuration;
                        HandleEmotion(command.value, duration);
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Erro ao processar mensagem do avatar: {e.Message}");
            }
        }
        
        private void HandleSay(string text, string audioData = null, string audioFormat = "mp3")
        {
            // Reproduz áudio TTS se disponível
            if (!string.IsNullOrEmpty(audioData) && ttsAudioPlayer != null)
            {
                Debug.Log($"Avatar diz (com áudio TTS): {text}");
                
                // Reproduz o áudio (animação será iniciada pelo evento OnAudioStarted)
                ttsAudioPlayer.PlayBase64Audio(audioData, audioFormat ?? "mp3");
            }
            else
            {
                // Sem áudio, usa lip sync visual ou animation controller
                Debug.Log($"Avatar diz: {text}");
                
                if (animationController != null)
                {
                    animationController.StartTalkingFromText(text);
                }
                else if (lipSync != null)
                {
                    lipSync.Speak(text);
                }
            }
        }
        
        private void OnTTSAudioStarted(float duration)
        {
            // Inicia animação de fala sincronizada com o áudio
            if (animationController != null)
            {
                animationController.StartTalking(duration);
            }
            else if (lipSync != null)
            {
                // Fallback para lip sync simples
                // (não tem duração, então só inicia)
            }
        }
        
        private void OnTTSAudioFinished()
        {
            // Para animação de fala
            if (animationController != null)
            {
                animationController.StopTalking();
            }
        }
        
        private void HandleEmotion(string emotion, float duration)
        {
            // Usa AvatarAnimationController se disponível
            if (animationController != null)
            {
                animationController.SetEmotion(emotion);
                Debug.Log($"Emoção (via AnimationController): {emotion} por {duration}s");
                return;
            }
            
            // Fallback para blend shapes diretos
            int blendShapeIndex = GetEmotionBlendShapeIndex(emotion);
            
            if (blendShapeIndex == -1)
            {
                Debug.LogWarning($"Emoção desconhecida ou blend shape não encontrado: {emotion}");
                return;
            }
            
            currentEmotionIndex = blendShapeIndex;
            emotionEndTime = Time.time + duration;
            currentEmotionValue = 100f; // Inicia em 100%
            
            Debug.Log($"Emoção: {emotion} por {duration}s");
        }
        
        private int GetEmotionBlendShapeIndex(string emotion)
        {
            switch (emotion.ToUpper())
            {
                case "HAPPY":
                case "FELIZ":
                    return happyBlendShapeIndex;
                
                case "ANGRY":
                case "BRAVO":
                case "RAIVA":
                    return angryBlendShapeIndex;
                
                case "SAD":
                case "TRISTE":
                    return sadBlendShapeIndex;
                
                case "SURPRISED":
                case "SURPRISE":
                case "SURPRESA":
                    return surprisedBlendShapeIndex;
                
                default:
                    return -1;
            }
        }
        
        private void Update()
        {
            // Atualiza blend shapes de emoção
            if (faceMeshRenderer != null && currentEmotionIndex != -1)
            {
                // Verifica se emoção expirou
                if (Time.time >= emotionEndTime)
                {
                    // Fade out da emoção
                    currentEmotionValue = Mathf.MoveTowards(currentEmotionValue, 0f, emotionTransitionSpeed * Time.deltaTime * 100f);
                    
                    if (currentEmotionValue <= 0.1f)
                    {
                        currentEmotionValue = 0f;
                        currentEmotionIndex = -1;
                    }
                }
                
                // Aplica blend shape
                faceMeshRenderer.SetBlendShapeWeight(currentEmotionIndex, currentEmotionValue);
            }
        }
        
        private void OnDestroy()
        {
            if (webSocketServer != null)
            {
                webSocketServer.OnMessageReceived -= HandleMessage;
            }
            
            if (ttsAudioPlayer != null)
            {
                ttsAudioPlayer.OnAudioStarted -= OnTTSAudioStarted;
                ttsAudioPlayer.OnAudioFinished -= OnTTSAudioFinished;
            }
        }
    }
    
    /// <summary>
    /// Estrutura para deserializar comandos JSON (mesma do GameCommandReceiver).
    /// </summary>
    [Serializable]
    public class GameCommand
    {
        public string cmd;
        public string value;
        public float? duration;
        public double? timestamp;
        public string audio_data;    // Áudio TTS em base64
        public string audio_format;  // Formato do áudio (mp3, wav)
    }
}

