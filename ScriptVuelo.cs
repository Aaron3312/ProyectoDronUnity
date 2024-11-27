using UnityEngine;

public class ScriptVuelo : MonoBehaviour
{
    public Animator heliceAnimator;    // Referencia al componente Animator
    public string parameterName = "Volando";    // Nombre del parámetro bool en el Animator
    public float rotationSpeed = 5f;   // Velocidad de rotación de la hélice
    
    private void Update()
    {
        // Verifica si la tecla W está presionada
        if (Input.GetKey(KeyCode.W))
        {
            // Activa la animación
            heliceAnimator.SetBool(parameterName, true);
            
        }
        else
        {
            // Desactiva la animación cuando se suelta la tecla
            heliceAnimator.SetBool(parameterName, false);
        }
    }
}