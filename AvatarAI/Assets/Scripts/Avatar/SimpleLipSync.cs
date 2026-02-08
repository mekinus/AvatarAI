using System.Collections;
using UnityEngine;

namespace AvatarAI.Avatar
{
    /// <summary>
    /// Sistema simples de lip sync usando blend shapes.
    /// Mapeia caracteres para fonemas (A, E, I, O, U).
    /// </summary>
    public class SimpleLipSync : MonoBehaviour
    {
        [Header("Blend Shapes")]
        [SerializeField] private SkinnedMeshRenderer faceMeshRenderer;
        
        [Header("Blend Shape Indices")]
        [SerializeField] private int blendShapeA = -1;
        [SerializeField] private int blendShapeE = -1;
        [SerializeField] private int blendShapeI = -1;
        [SerializeField] private int blendShapeO = -1;
        [SerializeField] private int blendShapeU = -1;
        
        [Header("Settings")]
        [SerializeField] private float characterDuration = 0.1f; // Duração por caractere
        [SerializeField] private float blendShapeIntensity = 50f;
        [SerializeField] private float transitionSpeed = 10f;
        
        [Header("Debug")]
        [SerializeField] private bool logSpeech = false;
        
        private bool isSpeaking = false;
        private Coroutine currentSpeechCoroutine;
        
        private void Start()
        {
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
                
                if (blendShapeA == -1 && (name.Contains("a") || name.Contains("ah") || name.Contains("aa")))
                {
                    blendShapeA = i;
                }
                if (blendShapeE == -1 && (name.Contains("e") || name.Contains("eh") || name.Contains("ee")))
                {
                    blendShapeE = i;
                }
                if (blendShapeI == -1 && (name.Contains("i") || name.Contains("ih") || name.Contains("ii")))
                {
                    blendShapeI = i;
                }
                if (blendShapeO == -1 && (name.Contains("o") || name.Contains("oh") || name.Contains("oo")))
                {
                    blendShapeO = i;
                }
                if (blendShapeU == -1 && (name.Contains("u") || name.Contains("uh") || name.Contains("uu")))
                {
                    blendShapeU = i;
                }
            }
        }
        
        /// <summary>
        /// Inicia a fala do avatar.
        /// </summary>
        public void Speak(string text)
        {
            if (isSpeaking && currentSpeechCoroutine != null)
            {
                StopCoroutine(currentSpeechCoroutine);
            }
            
            if (logSpeech)
            {
                Debug.Log($"LipSync: Falando '{text}'");
            }
            
            currentSpeechCoroutine = StartCoroutine(SpeakCoroutine(text));
        }
        
        private IEnumerator SpeakCoroutine(string text)
        {
            isSpeaking = true;
            
            // Estima duração total baseada no número de caracteres
            float totalDuration = text.Length * characterDuration;
            
            // Anima cada caractere
            for (int i = 0; i < text.Length; i++)
            {
                char c = char.ToLower(text[i]);
                int blendShapeIndex = GetBlendShapeForCharacter(c);
                
                if (blendShapeIndex != -1)
                {
                    // Ativa blend shape
                    SetBlendShape(blendShapeIndex, blendShapeIntensity);
                    
                    // Aguarda duração do caractere
                    yield return new WaitForSeconds(characterDuration);
                    
                    // Desativa blend shape
                    SetBlendShape(blendShapeIndex, 0f);
                }
                else
                {
                    // Para caracteres sem fonema, apenas espera
                    yield return new WaitForSeconds(characterDuration * 0.5f);
                }
            }
            
            // Aguarda um pouco no final
            yield return new WaitForSeconds(0.2f);
            
            // Garante que todos os blend shapes estão desativados
            ResetAllBlendShapes();
            
            isSpeaking = false;
        }
        
        private int GetBlendShapeForCharacter(char c)
        {
            // Mapeia caracteres para fonemas
            switch (c)
            {
                case 'a':
                case 'á':
                case 'à':
                case 'â':
                case 'ã':
                    return blendShapeA;
                
                case 'e':
                case 'é':
                case 'ê':
                    return blendShapeE;
                
                case 'i':
                case 'í':
                    return blendShapeI;
                
                case 'o':
                case 'ó':
                case 'ô':
                case 'õ':
                    return blendShapeO;
                
                case 'u':
                case 'ú':
                    return blendShapeU;
                
                default:
                    return -1; // Sem fonema correspondente
            }
        }
        
        private void SetBlendShape(int index, float value)
        {
            if (faceMeshRenderer != null && index != -1)
            {
                faceMeshRenderer.SetBlendShapeWeight(index, value);
            }
        }
        
        private void ResetAllBlendShapes()
        {
            if (faceMeshRenderer == null)
            {
                return;
            }
            
            if (blendShapeA != -1) SetBlendShape(blendShapeA, 0f);
            if (blendShapeE != -1) SetBlendShape(blendShapeE, 0f);
            if (blendShapeI != -1) SetBlendShape(blendShapeI, 0f);
            if (blendShapeO != -1) SetBlendShape(blendShapeO, 0f);
            if (blendShapeU != -1) SetBlendShape(blendShapeU, 0f);
        }
        
        public bool IsSpeaking()
        {
            return isSpeaking;
        }
    }
}

