using UnityEngine;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Script utilitário para configurar um avatar 3D na cena.
    /// Adiciona automaticamente os componentes necessários.
    /// </summary>
    public class AvatarSetup : MonoBehaviour
    {
        [Header("Setup (Execute no Editor)")]
        [SerializeField] private bool setupOnStart = false;
        
        [Header("Prefab Settings")]
        [SerializeField] private Vector3 cameraOffset = new Vector3(0, 1.5f, 2f);
        [SerializeField] private Vector3 lightOffset = new Vector3(1, 2, 1);
        
        [ContextMenu("Setup Avatar Components")]
        public void SetupAvatarComponents()
        {
            Debug.Log("Configurando componentes do Avatar...");
            
            // Adiciona AvatarController se não existir
            var avatarController = GetComponent<AvatarController>();
            if (avatarController == null)
            {
                avatarController = gameObject.AddComponent<AvatarController>();
                Debug.Log("+ AvatarController adicionado");
            }
            
            // Adiciona AvatarAnimationController se não existir
            var animController = GetComponent<AvatarAnimationController>();
            if (animController == null)
            {
                animController = gameObject.AddComponent<AvatarAnimationController>();
                Debug.Log("+ AvatarAnimationController adicionado");
            }
            
            // Adiciona TTSAudioPlayer se não existir
            var ttsPlayer = GetComponent<TTSAudioPlayer>();
            if (ttsPlayer == null)
            {
                ttsPlayer = gameObject.AddComponent<TTSAudioPlayer>();
                Debug.Log("+ TTSAudioPlayer adicionado");
            }
            
            // Adiciona AudioSource se não existir
            var audioSource = GetComponent<AudioSource>();
            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
                audioSource.playOnAwake = false;
                Debug.Log("+ AudioSource adicionado");
            }
            
            Debug.Log("Setup completo! Configure as referências no Inspector.");
        }
        
        [ContextMenu("Create VTuber Camera")]
        public void CreateVTuberCamera()
        {
            // Cria câmera posicionada para VTuber
            var cameraObj = new GameObject("VTuber Camera");
            var cam = cameraObj.AddComponent<Camera>();
            
            // Posiciona câmera
            Vector3 avatarPos = transform.position;
            cameraObj.transform.position = avatarPos + cameraOffset;
            cameraObj.transform.LookAt(avatarPos + Vector3.up * 1.2f); // Olha para o rosto
            
            // Configurações de câmera
            cam.fieldOfView = 30f;
            cam.nearClipPlane = 0.1f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.1f, 0.1f, 0.1f, 1f);
            
            Debug.Log("Câmera VTuber criada!");
        }
        
        [ContextMenu("Create Basic Lighting")]
        public void CreateBasicLighting()
        {
            // Cria luz principal
            var mainLightObj = new GameObject("Main Light");
            var mainLight = mainLightObj.AddComponent<Light>();
            mainLight.type = LightType.Directional;
            mainLight.intensity = 1f;
            mainLight.color = Color.white;
            mainLightObj.transform.position = transform.position + lightOffset;
            mainLightObj.transform.LookAt(transform.position);
            
            // Cria luz de preenchimento (fill light)
            var fillLightObj = new GameObject("Fill Light");
            var fillLight = fillLightObj.AddComponent<Light>();
            fillLight.type = LightType.Point;
            fillLight.intensity = 0.5f;
            fillLight.color = new Color(0.9f, 0.95f, 1f);
            fillLight.range = 10f;
            fillLightObj.transform.position = transform.position + new Vector3(-1, 1, 1);
            
            Debug.Log("Iluminação básica criada!");
        }
        
        [ContextMenu("Full Setup (Components + Camera + Light)")]
        public void FullSetup()
        {
            SetupAvatarComponents();
            CreateVTuberCamera();
            CreateBasicLighting();
            
            Debug.Log("=== Setup completo! ===");
            Debug.Log("Próximos passos:");
            Debug.Log("1. Arraste seu modelo FBX para Assets/Models/");
            Debug.Log("2. Coloque o modelo como filho deste GameObject");
            Debug.Log("3. Configure as referências no Inspector");
        }
        
        private void Start()
        {
            if (setupOnStart)
            {
                SetupAvatarComponents();
            }
        }
        
        private void OnDrawGizmos()
        {
            // Desenha preview da posição da câmera
            Gizmos.color = Color.cyan;
            Vector3 camPos = transform.position + cameraOffset;
            Gizmos.DrawWireSphere(camPos, 0.2f);
            Gizmos.DrawLine(camPos, transform.position + Vector3.up * 1.2f);
        }
    }
}


