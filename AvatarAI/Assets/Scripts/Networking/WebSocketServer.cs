using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace AvatarAI.Networking
{
    /// <summary>
    /// Servidor WebSocket simples para receber comandos do Python.
    /// Usa TCP raw para simplicidade (pode ser substituído por biblioteca WebSocket completa).
    /// </summary>
    public class WebSocketServer : MonoBehaviour
    {
        [Header("Server Settings")]
        [SerializeField] private int port = 8765;
        [SerializeField] private bool autoStart = true;
        
        [Header("Debug")]
        [SerializeField] private bool verboseLogging = false;
        
        private TcpListener tcpListener;
        private TcpClient connectedClient;
        private NetworkStream clientStream;
        private Thread serverThread;
        private bool isRunning = false;
        
        // Eventos para notificar outros scripts
        public event Action<string> OnMessageReceived;
        public event Action OnClientConnected;
        public event Action OnClientDisconnected;
        
        private void Start()
        {
            if (autoStart)
            {
                StartServer();
            }
        }
        
        public void StartServer()
        {
            if (isRunning)
            {
                Debug.LogWarning("Servidor WebSocket já está rodando");
                return;
            }
            
            try
            {
                // Garante que o dispatcher seja criado na thread principal ANTES de iniciar threads secundárias
                UnityMainThreadDispatcher.Instance();
                
                tcpListener = new TcpListener(IPAddress.Any, port);
                tcpListener.Start();
                isRunning = true;
                
                serverThread = new Thread(ListenForClients);
                serverThread.IsBackground = true;
                serverThread.Start();
                
                Debug.Log($"Servidor WebSocket iniciado na porta {port}");
            }
            catch (Exception e)
            {
                Debug.LogError($"Erro ao iniciar servidor WebSocket: {e.Message}");
                isRunning = false;
            }
        }
        
        private void ListenForClients()
        {
            while (isRunning)
            {
                try
                {
                    if (tcpListener.Pending())
                    {
                        connectedClient = tcpListener.AcceptTcpClient();
                        clientStream = connectedClient.GetStream();
                        
                        // Handshake WebSocket simples (para produção, usar biblioteca completa)
                        HandleWebSocketHandshake();
                        
                        // Notifica na thread principal
                        UnityMainThreadDispatcher.Instance().Enqueue(() =>
                        {
                            Debug.Log("Cliente conectado ao servidor WebSocket");
                            OnClientConnected?.Invoke();
                        });
                        
                        // Lê mensagens do cliente
                        ReadMessages();
                    }
                    else
                    {
                        Thread.Sleep(100);
                    }
                }
                catch (Exception e)
                {
                    if (isRunning)
                    {
                        // Log erro na thread principal para evitar problemas de thread
                        string errorMsg = e.Message;
                        UnityMainThreadDispatcher.Instance().Enqueue(() =>
                        {
                            Debug.LogError($"Erro ao aceitar cliente: {errorMsg}");
                        });
                    }
                }
            }
        }
        
        private void HandleWebSocketHandshake()
        {
            // Implementação simplificada - em produção usar biblioteca WebSocket completa
            // Por enquanto, assume que o cliente já fez handshake ou usa TCP raw
        }
        
        private void ReadMessages()
        {
            // Buffer maior para suportar áudio TTS em base64
            byte[] buffer = new byte[65536]; // 64KB
            string messageBuffer = "";
            
            while (isRunning && connectedClient != null && connectedClient.Connected)
            {
                try
                {
                    int bytesRead = clientStream.Read(buffer, 0, buffer.Length);
                    
                    if (bytesRead > 0)
                    {
                        // Adiciona dados recebidos ao buffer
                        messageBuffer += Encoding.UTF8.GetString(buffer, 0, bytesRead);
                        
                        // Processa mensagens completas (delimitadas por newline)
                        while (messageBuffer.Contains("\n"))
                        {
                            int newlineIndex = messageBuffer.IndexOf("\n");
                            string completeMessage = messageBuffer.Substring(0, newlineIndex).Trim();
                            messageBuffer = messageBuffer.Substring(newlineIndex + 1);
                            
                            if (!string.IsNullOrEmpty(completeMessage))
                            {
                                string finalMessage = completeMessage;
                                UnityMainThreadDispatcher.Instance().Enqueue(() =>
                                {
                                    if (verboseLogging)
                                    {
                                        Debug.Log($"Mensagem recebida: {finalMessage}");
                                    }
                                    
                                    OnMessageReceived?.Invoke(finalMessage);
                                });
                            }
                        }
                    }
                    else
                    {
                        // Cliente desconectou
                        break;
                    }
                }
                catch (Exception e)
                {
                    if (isRunning)
                    {
                        Debug.LogError($"Erro ao ler mensagem: {e.Message}");
                    }
                    break;
                }
            }
            
            // Cliente desconectou
            UnityMainThreadDispatcher.Instance().Enqueue(() =>
            {
                Debug.Log("Cliente desconectado");
                OnClientDisconnected?.Invoke();
            });
            
            CleanupClient();
        }
        
        private void CleanupClient()
        {
            try
            {
                clientStream?.Close();
                connectedClient?.Close();
                clientStream = null;
                connectedClient = null;
            }
            catch (Exception e)
            {
                Debug.LogError($"Erro ao limpar cliente: {e.Message}");
            }
        }
        
        public void StopServer()
        {
            isRunning = false;
            
            CleanupClient();
            
            try
            {
                tcpListener?.Stop();
            }
            catch (Exception e)
            {
                Debug.LogError($"Erro ao parar servidor: {e.Message}");
            }
            
            Debug.Log("Servidor WebSocket parado");
        }
        
        private void OnDestroy()
        {
            StopServer();
        }
        
        private void OnApplicationQuit()
        {
            StopServer();
        }
    }
    
    /// <summary>
    /// Dispatcher para executar código na thread principal do Unity.
    /// </summary>
    public class UnityMainThreadDispatcher : MonoBehaviour
    {
        private static UnityMainThreadDispatcher instance;
        private static readonly Queue<Action> executionQueue = new Queue<Action>();
        private static readonly object lockObject = new object();
        
        public static UnityMainThreadDispatcher Instance()
        {
            if (instance == null)
            {
                // Cria o dispatcher na thread principal
                // Se chamado de thread secundária, retorna null e o código deve lidar com isso
                if (Application.isPlaying)
                {
                    GameObject go = new GameObject("UnityMainThreadDispatcher");
                    instance = go.AddComponent<UnityMainThreadDispatcher>();
                    DontDestroyOnLoad(go);
                }
            }
            return instance;
        }
        
        public void Enqueue(Action action)
        {
            lock (executionQueue)
            {
                executionQueue.Enqueue(action);
            }
        }
        
        private void Update()
        {
            lock (executionQueue)
            {
                while (executionQueue.Count > 0)
                {
                    executionQueue.Dequeue().Invoke();
                }
            }
        }
    }
}

