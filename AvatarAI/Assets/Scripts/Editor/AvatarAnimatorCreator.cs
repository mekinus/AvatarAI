#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEditor.Animations;

namespace AvatarAI.Editor
{
    /// <summary>
    /// Editor script para criar Animator Controller do avatar.
    /// </summary>
    public class AvatarAnimatorCreator : EditorWindow
    {
        [MenuItem("AvatarAI/Create Avatar Animator Controller")]
        public static void CreateAnimatorController()
        {
            // Cria pasta se não existir
            if (!AssetDatabase.IsValidFolder("Assets/Animations"))
            {
                AssetDatabase.CreateFolder("Assets", "Animations");
            }
            
            // Cria Animator Controller
            var controller = AnimatorController.CreateAnimatorControllerAtPath("Assets/Animations/AvatarAnimator.controller");
            
            // Adiciona parâmetros
            controller.AddParameter("IsTalking", AnimatorControllerParameterType.Bool);
            controller.AddParameter("Emotion", AnimatorControllerParameterType.Int);
            controller.AddParameter("Talk", AnimatorControllerParameterType.Trigger);
            controller.AddParameter("Speed", AnimatorControllerParameterType.Float);
            
            // Pega a layer base
            var rootStateMachine = controller.layers[0].stateMachine;
            
            // Cria estados
            var idleState = rootStateMachine.AddState("Idle", new Vector3(200, 0, 0));
            var talkingState = rootStateMachine.AddState("Talking", new Vector3(400, 0, 0));
            var happyState = rootStateMachine.AddState("Happy", new Vector3(300, -100, 0));
            var sadState = rootStateMachine.AddState("Sad", new Vector3(300, -200, 0));
            var angryState = rootStateMachine.AddState("Angry", new Vector3(300, 100, 0));
            var surprisedState = rootStateMachine.AddState("Surprised", new Vector3(300, 200, 0));
            
            // Define Idle como estado default
            rootStateMachine.defaultState = idleState;
            
            // Cria transições
            // Idle -> Talking
            var idleToTalking = idleState.AddTransition(talkingState);
            idleToTalking.AddCondition(AnimatorConditionMode.If, 0, "IsTalking");
            idleToTalking.duration = 0.1f;
            idleToTalking.hasExitTime = false;
            
            // Talking -> Idle
            var talkingToIdle = talkingState.AddTransition(idleState);
            talkingToIdle.AddCondition(AnimatorConditionMode.IfNot, 0, "IsTalking");
            talkingToIdle.duration = 0.1f;
            talkingToIdle.hasExitTime = false;
            
            // Idle -> Emoções (baseado em Emotion int)
            // 0 = Neutral, 1 = Happy, 2 = Sad, 3 = Angry, 4 = Surprised
            
            // Idle -> Happy
            var toHappy = idleState.AddTransition(happyState);
            toHappy.AddCondition(AnimatorConditionMode.Equals, 1, "Emotion");
            toHappy.duration = 0.2f;
            toHappy.hasExitTime = false;
            
            // Happy -> Idle
            var happyToIdle = happyState.AddTransition(idleState);
            happyToIdle.AddCondition(AnimatorConditionMode.Equals, 0, "Emotion");
            happyToIdle.duration = 0.2f;
            happyToIdle.hasExitTime = false;
            
            // Idle -> Sad
            var toSad = idleState.AddTransition(sadState);
            toSad.AddCondition(AnimatorConditionMode.Equals, 2, "Emotion");
            toSad.duration = 0.2f;
            toSad.hasExitTime = false;
            
            // Sad -> Idle
            var sadToIdle = sadState.AddTransition(idleState);
            sadToIdle.AddCondition(AnimatorConditionMode.Equals, 0, "Emotion");
            sadToIdle.duration = 0.2f;
            sadToIdle.hasExitTime = false;
            
            // Idle -> Angry
            var toAngry = idleState.AddTransition(angryState);
            toAngry.AddCondition(AnimatorConditionMode.Equals, 3, "Emotion");
            toAngry.duration = 0.2f;
            toAngry.hasExitTime = false;
            
            // Angry -> Idle
            var angryToIdle = angryState.AddTransition(idleState);
            angryToIdle.AddCondition(AnimatorConditionMode.Equals, 0, "Emotion");
            angryToIdle.duration = 0.2f;
            angryToIdle.hasExitTime = false;
            
            // Idle -> Surprised
            var toSurprised = idleState.AddTransition(surprisedState);
            toSurprised.AddCondition(AnimatorConditionMode.Equals, 4, "Emotion");
            toSurprised.duration = 0.15f;
            toSurprised.hasExitTime = false;
            
            // Surprised -> Idle
            var surprisedToIdle = surprisedState.AddTransition(idleState);
            surprisedToIdle.AddCondition(AnimatorConditionMode.Equals, 0, "Emotion");
            surprisedToIdle.duration = 0.2f;
            surprisedToIdle.hasExitTime = false;
            
            // Salva asset
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            
            // Seleciona no Project
            Selection.activeObject = controller;
            
            Debug.Log("✅ Animator Controller criado em: Assets/Animations/AvatarAnimator.controller");
            Debug.Log("Próximo passo: Arraste este controller para o componente Animator do seu modelo 3D");
            
            EditorUtility.DisplayDialog(
                "Avatar Animator Criado!",
                "Animator Controller criado em:\nAssets/Animations/AvatarAnimator.controller\n\n" +
                "Próximos passos:\n" +
                "1. Arraste para o Animator do seu modelo\n" +
                "2. Adicione Animation Clips para cada estado\n" +
                "3. Configure as animações no Inspector",
                "OK"
            );
        }
        
        [MenuItem("AvatarAI/Setup Selected Model as Avatar")]
        public static void SetupSelectedModel()
        {
            var selected = Selection.activeGameObject;
            if (selected == null)
            {
                EditorUtility.DisplayDialog("Erro", "Selecione um modelo 3D na cena primeiro!", "OK");
                return;
            }
            
            // Adiciona componentes necessários
            if (selected.GetComponent<Avatar.AvatarController>() == null)
            {
                selected.AddComponent<Avatar.AvatarController>();
            }
            
            if (selected.GetComponent<Avatar.AvatarAnimationController>() == null)
            {
                selected.AddComponent<Avatar.AvatarAnimationController>();
            }
            
            if (selected.GetComponent<Avatar.TTSAudioPlayer>() == null)
            {
                selected.AddComponent<Avatar.TTSAudioPlayer>();
            }
            
            if (selected.GetComponent<AudioSource>() == null)
            {
                var audioSource = selected.AddComponent<AudioSource>();
                audioSource.playOnAwake = false;
            }
            
            // Marca como dirty para salvar
            EditorUtility.SetDirty(selected);
            
            Debug.Log($"✅ Componentes de Avatar adicionados a: {selected.name}");
            
            EditorUtility.DisplayDialog(
                "Setup Completo!",
                $"Componentes adicionados a {selected.name}:\n" +
                "- AvatarController\n" +
                "- AvatarAnimationController\n" +
                "- TTSAudioPlayer\n" +
                "- AudioSource\n\n" +
                "Configure as referências no Inspector.",
                "OK"
            );
        }
    }
}
#endif


