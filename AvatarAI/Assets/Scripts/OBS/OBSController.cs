using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace AvatarAI.OBS
{
    /// <summary>
    /// Controla o OBS remotamente via obs-websocket.
    /// Permite iniciar/parar stream, trocar cenas, etc.
    /// 
    /// Requer obs-websocket plugin no OBS:
    /// OBS 28+ já vem com websocket integrado (Tools > WebSocket Server Settings)
    /// </summary>
    public class OBSController : MonoBehaviour
    {
        [Header("Connection")]
        [SerializeField] private string obsHost = "localhost";
        [SerializeField] private int obsPort = 4455;
        [SerializeField] private string obsPassword = "";
        [SerializeField] private bool autoConnect = false; // Desativado por padrão
        
        [Header("Status")]
        [SerializeField] private bool isConnected = false;
        [SerializeField] private bool isStreaming = false;
        [SerializeField] private string currentScene = "";
        
        [Header("Debug")]
        [SerializeField] private bool logMessages = true;
        
        private ClientWebSocket webSocket;
        private CancellationTokenSource cancellationToken;
        private int messageId = 0;
        
        // Eventos
        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<bool> OnStreamingStateChanged;
        public event Action<string> OnSceneChanged;
        
        private async void Start()
        {
            if (autoConnect)
            {
                await Connect();
            }
        }
        
        /// <summary>
        /// Conecta ao OBS WebSocket.
        /// </summary>
        public async Task<bool> Connect()
        {
            if (isConnected)
            {
                Log("Já conectado ao OBS");
                return true;
            }
            
            try
            {
                webSocket = new ClientWebSocket();
                cancellationToken = new CancellationTokenSource();
                
                string uri = $"ws://{obsHost}:{obsPort}";
                Log($"Conectando ao OBS: {uri}");
                
                await webSocket.ConnectAsync(new Uri(uri), cancellationToken.Token);
                
                isConnected = true;
                Log("Conectado ao OBS!");
                
                // Inicia recepção de mensagens
                _ = ReceiveMessages();
                
                // Autentica se necessário
                if (!string.IsNullOrEmpty(obsPassword))
                {
                    await Authenticate();
                }
                
                OnConnected?.Invoke();
                return true;
            }
            catch (Exception e)
            {
                Debug.LogError($"OBSController: Erro ao conectar: {e.Message}");
                isConnected = false;
                return false;
            }
        }
        
        /// <summary>
        /// Desconecta do OBS.
        /// </summary>
        public async Task Disconnect()
        {
            if (!isConnected) return;
            
            try
            {
                cancellationToken?.Cancel();
                
                if (webSocket != null && webSocket.State == WebSocketState.Open)
                {
                    await webSocket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", CancellationToken.None);
                }
            }
            catch (Exception e)
            {
                Debug.LogWarning($"OBSController: Erro ao desconectar: {e.Message}");
            }
            finally
            {
                webSocket?.Dispose();
                webSocket = null;
                isConnected = false;
                OnDisconnected?.Invoke();
                Log("Desconectado do OBS");
            }
        }
        
        private async Task Authenticate()
        {
            // OBS WebSocket 5.x usa autenticação baseada em challenge
            // Simplificado aqui - implementação completa requer parsing do Hello message
            Log("Autenticação necessária - configure a senha no OBS WebSocket Settings");
        }
        
        private async Task ReceiveMessages()
        {
            var buffer = new byte[4096];
            
            try
            {
                while (webSocket != null && webSocket.State == WebSocketState.Open)
                {
                    var result = await webSocket.ReceiveAsync(
                        new ArraySegment<byte>(buffer), 
                        cancellationToken.Token
                    );
                    
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        break;
                    }
                    
                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    HandleMessage(message);
                }
            }
            catch (OperationCanceledException)
            {
                // Normal durante desconexão
            }
            catch (Exception e)
            {
                Debug.LogError($"OBSController: Erro ao receber mensagem: {e.Message}");
            }
        }
        
        private void HandleMessage(string message)
        {
            if (logMessages)
            {
                Log($"OBS: {message}");
            }
            
            // Parse básico de eventos do OBS
            // Implementação completa requer JSON parsing
            if (message.Contains("StreamStateChanged"))
            {
                isStreaming = message.Contains("\"outputActive\":true");
                OnStreamingStateChanged?.Invoke(isStreaming);
            }
            else if (message.Contains("CurrentProgramSceneChanged"))
            {
                // Extrair nome da cena do JSON
                OnSceneChanged?.Invoke(currentScene);
            }
        }
        
        /// <summary>
        /// Inicia streaming.
        /// </summary>
        public async Task StartStreaming()
        {
            await SendRequest("StartStream");
            Log("Comando enviado: Iniciar Stream");
        }
        
        /// <summary>
        /// Para streaming.
        /// </summary>
        public async Task StopStreaming()
        {
            await SendRequest("StopStream");
            Log("Comando enviado: Parar Stream");
        }
        
        /// <summary>
        /// Alterna streaming (liga/desliga).
        /// </summary>
        public async Task ToggleStreaming()
        {
            await SendRequest("ToggleStream");
            Log("Comando enviado: Toggle Stream");
        }
        
        /// <summary>
        /// Troca para uma cena específica.
        /// </summary>
        public async Task SetScene(string sceneName)
        {
            string request = $@"{{
                ""op"": 6,
                ""d"": {{
                    ""requestType"": ""SetCurrentProgramScene"",
                    ""requestId"": ""{messageId++}"",
                    ""requestData"": {{
                        ""sceneName"": ""{sceneName}""
                    }}
                }}
            }}";
            
            await SendRaw(request);
            Log($"Comando enviado: Trocar para cena '{sceneName}'");
        }
        
        /// <summary>
        /// Obtém lista de cenas disponíveis.
        /// </summary>
        public async Task GetScenes()
        {
            await SendRequest("GetSceneList");
        }
        
        private async Task SendRequest(string requestType, string requestData = null)
        {
            string data = string.IsNullOrEmpty(requestData) ? "{}" : requestData;
            
            string request = $@"{{
                ""op"": 6,
                ""d"": {{
                    ""requestType"": ""{requestType}"",
                    ""requestId"": ""{messageId++}"",
                    ""requestData"": {data}
                }}
            }}";
            
            await SendRaw(request);
        }
        
        private async Task SendRaw(string message)
        {
            if (!isConnected || webSocket == null)
            {
                Debug.LogWarning("OBSController: Não conectado ao OBS");
                return;
            }
            
            try
            {
                byte[] bytes = Encoding.UTF8.GetBytes(message);
                await webSocket.SendAsync(
                    new ArraySegment<byte>(bytes),
                    WebSocketMessageType.Text,
                    true,
                    cancellationToken.Token
                );
            }
            catch (Exception e)
            {
                Debug.LogError($"OBSController: Erro ao enviar: {e.Message}");
            }
        }
        
        private void Log(string message)
        {
            if (logMessages)
            {
                Debug.Log($"OBSController: {message}");
            }
        }
        
        private async void OnDestroy()
        {
            await Disconnect();
        }
        
        // ============ Context Menu para testes ============
        
        [ContextMenu("Connect to OBS")]
        private void MenuConnect()
        {
            _ = Connect();
        }
        
        [ContextMenu("Start Streaming")]
        private void MenuStartStream()
        {
            _ = StartStreaming();
        }
        
        [ContextMenu("Stop Streaming")]
        private void MenuStopStream()
        {
            _ = StopStreaming();
        }
        
        [ContextMenu("Toggle Streaming")]
        private void MenuToggleStream()
        {
            _ = ToggleStreaming();
        }
    }
}



