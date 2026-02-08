using System;
using UnityEngine;

namespace AvatarAI.Game
{
    /// <summary>
    /// Recebe comandos do WebSocket e executa ações no jogo.
    /// Mapeia comandos ACTION para funções do jogo.
    /// </summary>
    public class GameCommandReceiver : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Networking.WebSocketServer webSocketServer;
        
        [Header("Game Actions")]
        [SerializeField] private float moveSpeed = 5f;
        [SerializeField] private float jumpForce = 10f;
        [SerializeField] private float attackDuration = 0.5f;
        
        [Header("Debug")]
        [SerializeField] private bool logCommands = true;
        
        // Referência ao objeto do jogador (pode ser configurado no Inspector)
        private Transform playerTransform;
        private Rigidbody playerRigidbody;
        private bool isAttacking = false;
        
        // Interface para desacoplamento
        public interface IGameController
        {
            void MoveLeft();
            void MoveRight();
            void Jump();
            void Attack();
            void Idle();
        }
        
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
            
            // Busca player (assume que está no mesmo GameObject ou filho)
            playerTransform = transform;
            playerRigidbody = GetComponent<Rigidbody>();
            
            if (playerRigidbody == null)
            {
                Debug.LogWarning("Rigidbody não encontrado no player. Algumas ações podem não funcionar.");
            }
        }
        
        private void HandleMessage(string message)
        {
            try
            {
                // Parse JSON usando JsonUtility
                GameCommand command = JsonUtility.FromJson<GameCommand>(message);
                
                if (command == null || string.IsNullOrEmpty(command.cmd))
                {
                    Debug.LogWarning($"Comando inválido: {message}");
                    return;
                }
                
                if (logCommands)
                {
                    Debug.Log($"Comando recebido: {command.cmd} = {command.value}");
                }
                
                // Roteia comando
                switch (command.cmd.ToUpper())
                {
                    case "ACTION":
                        HandleAction(command.value);
                        break;
                    
                    case "SAY":
                        // SAY é tratado pelo AvatarController
                        break;
                    
                    case "EMOTION":
                        // EMOTION é tratado pelo AvatarController
                        break;
                    
                    default:
                        Debug.LogWarning($"Comando desconhecido: {command.cmd}");
                        break;
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Erro ao processar mensagem: {e.Message}");
            }
        }
        
        private void HandleAction(string action)
        {
            switch (action.ToUpper())
            {
                case "MOVE_LEFT":
                    MoveLeft();
                    break;
                
                case "MOVE_RIGHT":
                    MoveRight();
                    break;
                
                case "JUMP":
                    Jump();
                    break;
                
                case "ATTACK":
                    Attack();
                    break;
                
                case "IDLE":
                    Idle();
                    break;
                
                default:
                    Debug.LogWarning($"Ação desconhecida: {action}");
                    break;
            }
        }
        
        // Funções públicas de ação do jogo
        public void MoveLeft()
        {
            if (playerRigidbody != null)
            {
                playerRigidbody.linearVelocity = new Vector3(-moveSpeed, playerRigidbody.linearVelocity.y, 0);
            }
            else if (playerTransform != null)
            {
                playerTransform.Translate(Vector3.left * moveSpeed * Time.deltaTime);
            }
            
            Debug.Log("Ação: MoveLeft");
        }
        
        public void MoveRight()
        {
            if (playerRigidbody != null)
            {
                playerRigidbody.linearVelocity = new Vector3(moveSpeed, playerRigidbody.linearVelocity.y, 0);
            }
            else if (playerTransform != null)
            {
                playerTransform.Translate(Vector3.right * moveSpeed * Time.deltaTime);
            }
            
            Debug.Log("Ação: MoveRight");
        }
        
        public void Jump()
        {
            if (playerRigidbody != null)
            {
                // Verifica se está no chão (simplificado - em produção usar raycast)
                if (Mathf.Abs(playerRigidbody.linearVelocity.y) < 0.1f)
                {
                    playerRigidbody.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);
                    Debug.Log("Ação: Jump");
                }
            }
            else
            {
                Debug.LogWarning("Jump chamado mas Rigidbody não encontrado");
            }
        }
        
        public void Attack()
        {
            if (isAttacking)
            {
                return; // Já está atacando
            }
            
            StartCoroutine(AttackCoroutine());
            Debug.Log("Ação: Attack");
        }
        
        private System.Collections.IEnumerator AttackCoroutine()
        {
            isAttacking = true;
            
            // Aqui você pode adicionar animação, colisão, etc.
            // Por enquanto, apenas espera a duração
            
            yield return new WaitForSeconds(attackDuration);
            
            isAttacking = false;
        }
        
        public void Idle()
        {
            if (playerRigidbody != null)
            {
                // Para movimento horizontal, mantém vertical (gravidade)
                playerRigidbody.linearVelocity = new Vector3(0, playerRigidbody.linearVelocity.y, 0);
            }
            
            Debug.Log("Ação: Idle");
        }
        
        private void OnDestroy()
        {
            if (webSocketServer != null)
            {
                webSocketServer.OnMessageReceived -= HandleMessage;
            }
        }
    }
    
    /// <summary>
    /// Estrutura para deserializar comandos JSON.
    /// </summary>
    [Serializable]
    public class GameCommand
    {
        public string cmd;
        public string value;
        public float? duration;
        public double? timestamp;
    }
}

