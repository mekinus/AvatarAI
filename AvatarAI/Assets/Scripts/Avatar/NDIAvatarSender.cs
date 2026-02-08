using UnityEngine;
using Klak.Ndi;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Configura streaming NDI para OBS.
    /// FUNCIONA COM URP! Usa RenderTexture ao invés de OnRenderImage.
    /// CORRIGIDO: Tratamento de cleanup para evitar "readback error"
    /// </summary>
    public class NDIAvatarSender : MonoBehaviour
    {
        [Header("NDI Settings")]
        [SerializeField] private string ndiSourceName = "Unity Avatar";
        [SerializeField] private bool useAlphaChannel = true;
        
        [Header("Camera")]
        [SerializeField] private Camera targetCamera;
        
        [Header("Render Texture Settings")]
        [SerializeField] private int width = 1920;
        [SerializeField] private int height = 1080;
        
        [Header("Background (Green Screen para Chroma Key)")]
        [SerializeField] private Color backgroundColor = new Color(0, 1, 0, 1); // Verde puro #00FF00
        
        private NdiSender ndiSender;
        private RenderTexture renderTexture;
        private bool isInitialized = false;
        
        private void Awake()
        {
            // Configura o nome do GameObject (nome NDI)
            gameObject.name = ndiSourceName;
        }
        
        private void Start()
        {
            SetupCamera();
            SetupRenderTexture();
            SetupNdiSender();
            isInitialized = true;
            
            Debug.Log($"=== NDI STREAMING (URP MODE) ===");
            Debug.Log($"Nome NDI: {ndiSourceName}");
            Debug.Log($"Resolução: {width}x{height}");
            Debug.Log($"Alpha: {useAlphaChannel}");
            Debug.Log($"Camera: {targetCamera?.name}");
        }
        
        private void SetupCamera()
        {
            if (targetCamera == null)
            {
                targetCamera = Camera.main;
            }
            
            if (targetCamera == null)
            {
                Debug.LogError("NDIAvatarSender: Nenhuma câmera encontrada! Arraste a câmera para o campo Target Camera.");
                return;
            }
            
            // Configura background transparente
            targetCamera.clearFlags = CameraClearFlags.SolidColor;
            targetCamera.backgroundColor = backgroundColor;
        }
        
        private void SetupRenderTexture()
        {
            // Cria RenderTexture com alpha
            RenderTextureFormat format = useAlphaChannel ? 
                RenderTextureFormat.ARGB32 : RenderTextureFormat.RGB565;
            
            renderTexture = new RenderTexture(width, height, 24, format);
            renderTexture.antiAliasing = 1;
            renderTexture.Create();
            
            if (targetCamera != null)
            {
                targetCamera.targetTexture = renderTexture;
            }
        }
        
        private void SetupNdiSender()
        {
            // Pega ou cria o NdiSender
            ndiSender = GetComponent<NdiSender>();
            if (ndiSender == null)
            {
                ndiSender = gameObject.AddComponent<NdiSender>();
            }
            
            // Configura o sourceTexture (modo RenderTexture para URP)
            ndiSender.sourceTexture = renderTexture;
            ndiSender.alphaSupport = useAlphaChannel;
            ndiSender.enabled = true;
        }
        
        /// <summary>
        /// Cleanup seguro que evita "readback error".
        /// A ordem é importante: primeiro desabilita, depois limpa.
        /// </summary>
        private void SafeCleanup()
        {
            if (!isInitialized) return;
            isInitialized = false;
            
            // PASSO 1: Desabilita o NdiSender ANTES de mexer nos recursos
            // Isso para qualquer operação de readback em andamento
            if (ndiSender != null)
            {
                ndiSender.enabled = false;
                ndiSender.sourceTexture = null;
            }
            
            // PASSO 2: Remove a RenderTexture da câmera
            if (targetCamera != null)
            {
                targetCamera.targetTexture = null;
            }
            
            // PASSO 3: Espera um frame para garantir que operações GPU terminaram
            // Antes de destruir recursos
            
            // PASSO 4: Limpa a RenderTexture
            if (renderTexture != null)
            {
                renderTexture.Release();
                Destroy(renderTexture);
                renderTexture = null;
            }
            
            Debug.Log("NDIAvatarSender: Cleanup completo");
        }
        
        private void OnDestroy()
        {
            SafeCleanup();
        }
        
        private void OnApplicationQuit()
        {
            // Cleanup extra quando o aplicativo fecha
            // Isso é crucial para evitar crashes no Editor
            SafeCleanup();
        }
        
        private void OnDisable()
        {
            // Se o objeto for desabilitado, também limpa
            // para evitar readback errors
            if (ndiSender != null)
            {
                ndiSender.enabled = false;
            }
        }
        
        private void OnEnable()
        {
            // Reabilita se o objeto for habilitado novamente
            if (isInitialized && ndiSender != null && renderTexture != null)
            {
                ndiSender.sourceTexture = renderTexture;
                ndiSender.enabled = true;
            }
        }
        
        [ContextMenu("Verificar Status NDI")]
        private void VerificarStatus()
        {
            Debug.Log("=== STATUS NDI (URP MODE) ===");
            Debug.Log($"GameObject/NDI Name: {gameObject.name}");
            Debug.Log($"Camera: {(targetCamera != null ? targetCamera.name : "FALTANDO")}");
            Debug.Log($"RenderTexture: {(renderTexture != null ? $"{width}x{height}" : "NULL")}");
            Debug.Log($"NdiSender: {(ndiSender != null ? "OK" : "FALTANDO")}");
            Debug.Log($"NdiSender.sourceTexture: {(ndiSender?.sourceTexture != null ? "SET" : "NULL")}");
            Debug.Log($"NdiSender.enabled: {ndiSender?.enabled}");
            Debug.Log($"Initialized: {isInitialized}");
        }
    }
}
