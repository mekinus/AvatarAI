using UnityEngine;
using AvatarAI.Avatar;

namespace AvatarAI.OBS
{
    /// <summary>
    /// Script de setup para configurar streaming VTuber.
    /// Cria câmera dedicada para o avatar e configura NDI.
    /// </summary>
    public class StreamingSetup : MonoBehaviour
    {
        [Header("Avatar")]
        [SerializeField] private Transform avatarTransform;
        
        [Header("Camera Settings")]
        [SerializeField] private Vector3 cameraOffset = new Vector3(0, 1.5f, 1.5f);
        [SerializeField] private float cameraFOV = 30f;
        [SerializeField] private int renderWidth = 1920;
        [SerializeField] private int renderHeight = 1080;
        
        [Header("Created Objects")]
        [SerializeField] private Camera streamCamera;
        [SerializeField] private NDIAvatarSender ndiSender;
        [SerializeField] private OBSController obsController;
        
        [ContextMenu("Setup Streaming (Full)")]
        public void SetupStreaming()
        {
            CreateStreamCamera();
            SetupNDI();
            SetupOBSController();
            
            Debug.Log("=== SETUP DE STREAMING COMPLETO ===");
            Debug.Log("Próximos passos:");
            Debug.Log("1. Instale Klak NDI na Unity (Package Manager > Add git URL)");
            Debug.Log("   URL: https://github.com/keijiro/KlakNDI.git#upm");
            Debug.Log("2. Descomente o código em NDIAvatarSender.SetupNDI()");
            Debug.Log("3. No OBS: Sources > Add > NDI Source > Selecione 'Unity Avatar'");
            Debug.Log("4. Configure a posição do avatar como overlay");
        }
        
        [ContextMenu("1. Create Stream Camera")]
        public void CreateStreamCamera()
        {
            // Encontra avatar se não configurado
            if (avatarTransform == null)
            {
                var avatarController = FindObjectOfType<AvatarController>();
                if (avatarController != null)
                {
                    avatarTransform = avatarController.transform;
                }
            }
            
            // Cria câmera de streaming
            var cameraObj = new GameObject("VTuber Stream Camera");
            streamCamera = cameraObj.AddComponent<Camera>();
            
            // Posiciona câmera
            if (avatarTransform != null)
            {
                cameraObj.transform.position = avatarTransform.position + cameraOffset;
                cameraObj.transform.LookAt(avatarTransform.position + Vector3.up * 1.2f);
            }
            else
            {
                cameraObj.transform.position = cameraOffset;
                cameraObj.transform.LookAt(Vector3.up * 1.2f);
            }
            
            // Configura câmera
            streamCamera.fieldOfView = cameraFOV;
            streamCamera.nearClipPlane = 0.1f;
            streamCamera.clearFlags = CameraClearFlags.SolidColor;
            streamCamera.backgroundColor = new Color(0, 0, 0, 0); // Transparente
            streamCamera.depth = 10; // Renderiza por último
            
            // Desativa AudioListener se existir (evita conflito)
            var audioListener = cameraObj.GetComponent<AudioListener>();
            if (audioListener != null)
            {
                DestroyImmediate(audioListener);
            }
            
            Debug.Log("Câmera de streaming criada: VTuber Stream Camera");
        }
        
        [ContextMenu("2. Setup NDI Sender")]
        public void SetupNDI()
        {
            if (streamCamera == null)
            {
                Debug.LogError("Crie a câmera de streaming primeiro!");
                return;
            }
            
            // Adiciona NDI Sender à câmera
            ndiSender = streamCamera.gameObject.GetComponent<NDIAvatarSender>();
            if (ndiSender == null)
            {
                ndiSender = streamCamera.gameObject.AddComponent<NDIAvatarSender>();
            }
            
            Debug.Log("NDI Sender configurado na câmera de streaming");
            Debug.Log("IMPORTANTE: Instale Klak NDI e descomente o código em NDIAvatarSender.cs");
        }
        
        [ContextMenu("3. Setup OBS Controller")]
        public void SetupOBSController()
        {
            // Adiciona OBS Controller
            obsController = GetComponent<OBSController>();
            if (obsController == null)
            {
                obsController = gameObject.AddComponent<OBSController>();
            }
            
            Debug.Log("OBS Controller adicionado");
            Debug.Log("Configure a porta e senha do WebSocket no OBS:");
            Debug.Log("OBS > Tools > WebSocket Server Settings");
        }
        
        [ContextMenu("Test: Start OBS Stream")]
        public async void TestStartStream()
        {
            if (obsController == null)
            {
                Debug.LogError("OBS Controller não configurado!");
                return;
            }
            
            await obsController.Connect();
            await obsController.StartStreaming();
        }
        
        [ContextMenu("Test: Stop OBS Stream")]
        public async void TestStopStream()
        {
            if (obsController == null)
            {
                Debug.LogError("OBS Controller não configurado!");
                return;
            }
            
            await obsController.StopStreaming();
        }
        
        private void OnDrawGizmos()
        {
            // Desenha preview da posição da câmera
            Vector3 camPos = (avatarTransform != null ? avatarTransform.position : Vector3.zero) + cameraOffset;
            
            Gizmos.color = Color.green;
            Gizmos.DrawWireSphere(camPos, 0.3f);
            
            Gizmos.color = Color.yellow;
            Vector3 lookAt = (avatarTransform != null ? avatarTransform.position : Vector3.zero) + Vector3.up * 1.2f;
            Gizmos.DrawLine(camPos, lookAt);
            
            // Desenha frustum aproximado
            Gizmos.color = new Color(0, 1, 0, 0.3f);
            Gizmos.matrix = Matrix4x4.TRS(camPos, Quaternion.LookRotation(lookAt - camPos), Vector3.one);
            Gizmos.DrawFrustum(Vector3.zero, cameraFOV, 3f, 0.1f, (float)renderWidth / renderHeight);
        }
    }
}



