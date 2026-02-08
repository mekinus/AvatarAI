using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Reproduz áudio TTS recebido em base64.
    /// Decodifica, salva temporariamente e reproduz via AudioSource.
    /// </summary>
    [RequireComponent(typeof(AudioSource))]
    public class TTSAudioPlayer : MonoBehaviour
    {
        [Header("Settings")]
        [SerializeField] private float volume = 1f;
        [SerializeField] private bool deleteAfterPlay = true;
        
        [Header("Debug")]
        [SerializeField] private bool logAudio = true;
        
        private AudioSource audioSource;
        private string tempFilePath;
        private bool isPlaying = false;
        
        // Evento disparado quando o áudio termina
        public event Action OnAudioFinished;
        
        // Evento disparado quando o áudio começa
        public event Action<float> OnAudioStarted; // passa a duração
        
        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
            }
            
            audioSource.playOnAwake = false;
            audioSource.volume = volume;
        }
        
        /// <summary>
        /// Reproduz áudio a partir de dados base64.
        /// </summary>
        /// <param name="base64Audio">Áudio codificado em base64</param>
        /// <param name="format">Formato do áudio (mp3, wav)</param>
        public void PlayBase64Audio(string base64Audio, string format = "mp3")
        {
            if (string.IsNullOrEmpty(base64Audio))
            {
                Debug.LogWarning("TTSAudioPlayer: Áudio vazio");
                return;
            }
            
            StartCoroutine(PlayAudioCoroutine(base64Audio, format));
        }
        
        private IEnumerator PlayAudioCoroutine(string base64Audio, string format)
        {
            // Para áudio anterior se estiver tocando
            if (isPlaying)
            {
                audioSource.Stop();
                CleanupTempFile();
            }
            
            isPlaying = true;
            
            // Decodifica base64 para bytes
            byte[] audioBytes;
            try
            {
                audioBytes = Convert.FromBase64String(base64Audio);
                if (logAudio)
                {
                    Debug.Log($"TTSAudioPlayer: Decodificado {audioBytes.Length} bytes de áudio");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"TTSAudioPlayer: Erro ao decodificar base64: {e.Message}");
                isPlaying = false;
                yield break;
            }
            
            // Salva arquivo temporário (Unity precisa de arquivo para carregar MP3)
            string extension = format.ToLower();
            tempFilePath = Path.Combine(Application.temporaryCachePath, $"tts_temp_{Guid.NewGuid()}.{extension}");
            
            try
            {
                File.WriteAllBytes(tempFilePath, audioBytes);
                if (logAudio)
                {
                    Debug.Log($"TTSAudioPlayer: Arquivo temporário salvo: {tempFilePath}");
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"TTSAudioPlayer: Erro ao salvar arquivo: {e.Message}");
                isPlaying = false;
                yield break;
            }
            
            // Carrega áudio usando UnityWebRequest
            AudioType audioType = GetAudioType(format);
            string fileUri = "file://" + tempFilePath;
            
            using (UnityWebRequest www = UnityWebRequestMultimedia.GetAudioClip(fileUri, audioType))
            {
                yield return www.SendWebRequest();
                
                if (www.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"TTSAudioPlayer: Erro ao carregar áudio: {www.error}");
                    CleanupTempFile();
                    isPlaying = false;
                    yield break;
                }
                
                AudioClip clip = DownloadHandlerAudioClip.GetContent(www);
                
                if (clip == null)
                {
                    Debug.LogError("TTSAudioPlayer: AudioClip é null");
                    CleanupTempFile();
                    isPlaying = false;
                    yield break;
                }
                
                // Reproduz o áudio
                audioSource.clip = clip;
                audioSource.Play();
                
                if (logAudio)
                {
                    Debug.Log($"TTSAudioPlayer: Reproduzindo áudio ({clip.length:F2}s)");
                }
                
                // Notifica início do áudio
                OnAudioStarted?.Invoke(clip.length);
                
                // Aguarda o áudio terminar
                yield return new WaitForSeconds(clip.length + 0.1f);
                
                // Limpa recursos
                audioSource.clip = null;
                Destroy(clip);
            }
            
            // Remove arquivo temporário
            if (deleteAfterPlay)
            {
                CleanupTempFile();
            }
            
            isPlaying = false;
            OnAudioFinished?.Invoke();
            
            if (logAudio)
            {
                Debug.Log("TTSAudioPlayer: Áudio finalizado");
            }
        }
        
        private AudioType GetAudioType(string format)
        {
            switch (format.ToLower())
            {
                case "mp3":
                    return AudioType.MPEG;
                case "wav":
                    return AudioType.WAV;
                case "ogg":
                    return AudioType.OGGVORBIS;
                default:
                    return AudioType.MPEG;
            }
        }
        
        private void CleanupTempFile()
        {
            if (!string.IsNullOrEmpty(tempFilePath) && File.Exists(tempFilePath))
            {
                try
                {
                    File.Delete(tempFilePath);
                    if (logAudio)
                    {
                        Debug.Log($"TTSAudioPlayer: Arquivo temporário removido");
                    }
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"TTSAudioPlayer: Erro ao remover arquivo: {e.Message}");
                }
                
                tempFilePath = null;
            }
        }
        
        /// <summary>
        /// Para a reprodução atual.
        /// </summary>
        public void Stop()
        {
            if (audioSource != null && audioSource.isPlaying)
            {
                audioSource.Stop();
            }
            
            StopAllCoroutines();
            CleanupTempFile();
            isPlaying = false;
        }
        
        /// <summary>
        /// Verifica se está reproduzindo áudio.
        /// </summary>
        public bool IsPlaying()
        {
            return isPlaying;
        }
        
        /// <summary>
        /// Define o volume do áudio.
        /// </summary>
        public void SetVolume(float newVolume)
        {
            volume = Mathf.Clamp01(newVolume);
            if (audioSource != null)
            {
                audioSource.volume = volume;
            }
        }
        
        private void OnDestroy()
        {
            Stop();
        }
    }
}

