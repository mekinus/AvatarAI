using System.Collections;
using UnityEngine;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Controlador de animações do avatar 3D.
    /// Funciona com ou sem blend shapes, usando Animator como fallback.
    /// </summary>
    public class AvatarAnimationController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Animator animator;
        [SerializeField] private SkinnedMeshRenderer faceMesh;
        
        [Header("Animator Parameters")]
        [SerializeField] private string isTalkingParam = "IsTalking";
        [SerializeField] private string emotionParam = "Emotion";
        [SerializeField] private string triggerTalkParam = "Talk";
        
        [Header("Bone Animation (se não tiver blend shapes)")]
        [SerializeField] private Transform jawBone;
        [SerializeField] private float jawOpenAngle = 15f;
        [SerializeField] private float jawAnimSpeed = 10f;
        
        [Header("Settings")]
        [SerializeField] private bool useBlendShapes = true;
        [SerializeField] private bool useBoneAnimation = false;
        [SerializeField] private bool useAnimator = true;
        
        [Header("Blend Shape Indices (se disponível)")]
        [SerializeField] private int mouthOpenIndex = -1;
        [SerializeField] private int happyIndex = -1;
        [SerializeField] private int sadIndex = -1;
        [SerializeField] private int angryIndex = -1;
        [SerializeField] private int surprisedIndex = -1;
        
        [Header("Debug")]
        [SerializeField] private bool logAnimations = true;
        
        // Estado
        private bool isTalking = false;
        private Coroutine talkCoroutine;
        private Quaternion jawClosedRotation;
        private Quaternion jawOpenRotation;
        
        // Enum para emoções
        public enum Emotion
        {
            Neutral = 0,
            Happy = 1,
            Sad = 2,
            Angry = 3,
            Surprised = 4
        }
        
        private void Start()
        {
            // Busca componentes se não configurados
            if (animator == null)
            {
                animator = GetComponent<Animator>();
                if (animator == null)
                {
                    animator = GetComponentInChildren<Animator>();
                }
            }
            
            if (faceMesh == null)
            {
                faceMesh = GetComponentInChildren<SkinnedMeshRenderer>();
            }
            
            // Detecta automaticamente blend shapes
            DetectBlendShapes();
            
            // Configura jaw bone se disponível
            if (jawBone != null)
            {
                jawClosedRotation = jawBone.localRotation;
                jawOpenRotation = jawClosedRotation * Quaternion.Euler(jawOpenAngle, 0, 0);
            }
            
            // Auto-detecta modo de animação
            AutoDetectAnimationMode();
            
            if (logAnimations)
            {
                Debug.Log($"AvatarAnimationController: BlendShapes={useBlendShapes}, Bones={useBoneAnimation}, Animator={useAnimator}");
            }
        }
        
        private void DetectBlendShapes()
        {
            if (faceMesh == null || faceMesh.sharedMesh == null)
            {
                useBlendShapes = false;
                return;
            }
            
            var mesh = faceMesh.sharedMesh;
            
            for (int i = 0; i < mesh.blendShapeCount; i++)
            {
                string name = mesh.GetBlendShapeName(i).ToLower();
                
                // Detecta blend shapes de boca
                if (mouthOpenIndex == -1 && (name.Contains("mouth") && name.Contains("open") || 
                    name.Contains("a") || name.Contains("aa") || name.Contains("jaw")))
                {
                    mouthOpenIndex = i;
                }
                
                // Detecta emoções
                if (happyIndex == -1 && (name.Contains("happy") || name.Contains("smile") || name.Contains("joy")))
                {
                    happyIndex = i;
                }
                if (sadIndex == -1 && (name.Contains("sad") || name.Contains("frown")))
                {
                    sadIndex = i;
                }
                if (angryIndex == -1 && (name.Contains("angry") || name.Contains("anger")))
                {
                    angryIndex = i;
                }
                if (surprisedIndex == -1 && (name.Contains("surprise") || name.Contains("shock")))
                {
                    surprisedIndex = i;
                }
            }
            
            // Se encontrou pelo menos um blend shape relevante, usa blend shapes
            useBlendShapes = (mouthOpenIndex != -1 || happyIndex != -1 || sadIndex != -1);
            
            if (logAnimations)
            {
                Debug.Log($"Blend shapes detectados: mouth={mouthOpenIndex}, happy={happyIndex}, sad={sadIndex}, angry={angryIndex}");
            }
        }
        
        private void AutoDetectAnimationMode()
        {
            // Se não tem blend shapes, tenta usar bones
            if (!useBlendShapes)
            {
                // Tenta encontrar jaw bone automaticamente
                if (jawBone == null)
                {
                    jawBone = FindBoneByName("jaw", "chin", "mouth", "mandible");
                    if (jawBone != null)
                    {
                        useBoneAnimation = true;
                        jawClosedRotation = jawBone.localRotation;
                        jawOpenRotation = jawClosedRotation * Quaternion.Euler(jawOpenAngle, 0, 0);
                        Debug.Log($"Jaw bone encontrado: {jawBone.name}");
                    }
                }
            }
            
            // Se não tem nada, usa apenas Animator
            if (!useBlendShapes && !useBoneAnimation)
            {
                useAnimator = true;
                Debug.Log("Usando apenas Animator para animações");
            }
        }
        
        private Transform FindBoneByName(params string[] possibleNames)
        {
            var allTransforms = GetComponentsInChildren<Transform>();
            foreach (var t in allTransforms)
            {
                string tName = t.name.ToLower();
                foreach (string name in possibleNames)
                {
                    if (tName.Contains(name.ToLower()))
                    {
                        return t;
                    }
                }
            }
            return null;
        }
        
        /// <summary>
        /// Inicia animação de fala.
        /// </summary>
        /// <param name="duration">Duração da fala em segundos</param>
        public void StartTalking(float duration)
        {
            if (talkCoroutine != null)
            {
                StopCoroutine(talkCoroutine);
            }
            
            talkCoroutine = StartCoroutine(TalkCoroutine(duration));
        }
        
        /// <summary>
        /// Inicia animação de fala baseada em texto (estima duração).
        /// </summary>
        public void StartTalkingFromText(string text)
        {
            // Estima duração: ~0.08s por caractere (fala normal)
            float duration = text.Length * 0.08f;
            duration = Mathf.Clamp(duration, 1f, 30f);
            
            StartTalking(duration);
        }
        
        private IEnumerator TalkCoroutine(float duration)
        {
            isTalking = true;
            
            // Notifica Animator
            if (useAnimator && animator != null)
            {
                animator.SetBool(isTalkingParam, true);
                animator.SetTrigger(triggerTalkParam);
            }
            
            if (logAnimations)
            {
                Debug.Log($"Iniciando fala por {duration:F1}s");
            }
            
            float elapsed = 0f;
            float mouthValue = 0f;
            float targetMouthValue = 0f;
            float changeInterval = 0.1f;
            float lastChangeTime = 0f;
            
            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                
                // Muda alvo da boca periodicamente para simular fala
                if (elapsed - lastChangeTime > changeInterval)
                {
                    targetMouthValue = Random.Range(0.3f, 1f);
                    changeInterval = Random.Range(0.05f, 0.15f);
                    lastChangeTime = elapsed;
                }
                
                // Suaviza movimento
                mouthValue = Mathf.Lerp(mouthValue, targetMouthValue, Time.deltaTime * jawAnimSpeed);
                
                // Aplica animação
                ApplyMouthAnimation(mouthValue);
                
                yield return null;
            }
            
            // Fecha boca suavemente
            float closeTime = 0.2f;
            float closeElapsed = 0f;
            float startValue = mouthValue;
            
            while (closeElapsed < closeTime)
            {
                closeElapsed += Time.deltaTime;
                mouthValue = Mathf.Lerp(startValue, 0f, closeElapsed / closeTime);
                ApplyMouthAnimation(mouthValue);
                yield return null;
            }
            
            ApplyMouthAnimation(0f);
            
            // Notifica Animator
            if (useAnimator && animator != null)
            {
                animator.SetBool(isTalkingParam, false);
            }
            
            isTalking = false;
            
            if (logAnimations)
            {
                Debug.Log("Fala finalizada");
            }
        }
        
        private void ApplyMouthAnimation(float value)
        {
            // Blend Shapes
            if (useBlendShapes && faceMesh != null && mouthOpenIndex != -1)
            {
                faceMesh.SetBlendShapeWeight(mouthOpenIndex, value * 100f);
            }
            
            // Bone Animation
            if (useBoneAnimation && jawBone != null)
            {
                jawBone.localRotation = Quaternion.Lerp(jawClosedRotation, jawOpenRotation, value);
            }
        }
        
        /// <summary>
        /// Para animação de fala imediatamente.
        /// </summary>
        public void StopTalking()
        {
            if (talkCoroutine != null)
            {
                StopCoroutine(talkCoroutine);
                talkCoroutine = null;
            }
            
            ApplyMouthAnimation(0f);
            isTalking = false;
            
            if (useAnimator && animator != null)
            {
                animator.SetBool(isTalkingParam, false);
            }
        }
        
        /// <summary>
        /// Define a emoção do avatar.
        /// </summary>
        public void SetEmotion(Emotion emotion, float intensity = 1f)
        {
            // Reset todas as emoções primeiro
            ResetEmotions();
            
            // Aplica emoção via blend shapes
            if (useBlendShapes && faceMesh != null)
            {
                int index = GetEmotionBlendShapeIndex(emotion);
                if (index != -1)
                {
                    faceMesh.SetBlendShapeWeight(index, intensity * 100f);
                }
            }
            
            // Notifica Animator
            if (useAnimator && animator != null)
            {
                animator.SetInteger(emotionParam, (int)emotion);
            }
            
            if (logAnimations)
            {
                Debug.Log($"Emoção: {emotion} (intensidade: {intensity:F1})");
            }
        }
        
        /// <summary>
        /// Define emoção por string (compatível com comandos).
        /// </summary>
        public void SetEmotion(string emotionName, float intensity = 1f)
        {
            Emotion emotion = ParseEmotion(emotionName);
            SetEmotion(emotion, intensity);
        }
        
        private Emotion ParseEmotion(string name)
        {
            switch (name.ToUpper())
            {
                case "HAPPY":
                case "FELIZ":
                case "JOY":
                    return Emotion.Happy;
                
                case "SAD":
                case "TRISTE":
                    return Emotion.Sad;
                
                case "ANGRY":
                case "BRAVO":
                case "RAIVA":
                    return Emotion.Angry;
                
                case "SURPRISED":
                case "SURPRISE":
                case "SURPRESA":
                    return Emotion.Surprised;
                
                default:
                    return Emotion.Neutral;
            }
        }
        
        private int GetEmotionBlendShapeIndex(Emotion emotion)
        {
            switch (emotion)
            {
                case Emotion.Happy: return happyIndex;
                case Emotion.Sad: return sadIndex;
                case Emotion.Angry: return angryIndex;
                case Emotion.Surprised: return surprisedIndex;
                default: return -1;
            }
        }
        
        private void ResetEmotions()
        {
            if (faceMesh == null) return;
            
            if (happyIndex != -1) faceMesh.SetBlendShapeWeight(happyIndex, 0);
            if (sadIndex != -1) faceMesh.SetBlendShapeWeight(sadIndex, 0);
            if (angryIndex != -1) faceMesh.SetBlendShapeWeight(angryIndex, 0);
            if (surprisedIndex != -1) faceMesh.SetBlendShapeWeight(surprisedIndex, 0);
        }
        
        /// <summary>
        /// Reseta para estado neutro.
        /// </summary>
        public void ResetToNeutral()
        {
            StopTalking();
            SetEmotion(Emotion.Neutral);
        }
        
        public bool IsTalking()
        {
            return isTalking;
        }
    }
}


