using UnityEngine;

public class SkeletonController : MonoBehaviour
{
    public Animator animator;
    public float walkSpeed = 2.0f;  // Velocidad al caminar
    public float runSpeed = 8.0f;   // Velocidad al correr
    private float currentSpeed;

    void Start()
    {
        if (animator == null)
        {
            animator = GetComponent<Animator>();
        }
    }

    void Update()
    {
        // Detectar si estamos presionando Shift para correr
        bool isRunning = Input.GetKey(KeyCode.LeftShift);
        currentSpeed = isRunning ? runSpeed : walkSpeed;

        // Movimiento con WASD
        float horizontal = Input.GetAxis("Horizontal");  // A y D para moverse en el eje X
        float vertical = Input.GetAxis("Vertical");      // W y S para moverse en el eje Z
        Vector3 movement = new Vector3(horizontal, 0, vertical).normalized * currentSpeed;

        // Establece la velocidad en el Animator
        animator.SetFloat("Speed", movement.magnitude);

        // Mover el personaje
        transform.Translate(movement * Time.deltaTime, Space.World);

        // Rotar el personaje hacia la dirección en la que se mueve
        if (movement != Vector3.zero)
        {
            Quaternion targetRotation = Quaternion.LookRotation(movement);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * 10f);
        }

        // Opciones adicionales para ataques o acciones
        if (Input.GetKeyDown(KeyCode.LeftArrow))
        {
            animator.SetTrigger("LeftAttack");
        }
        if (Input.GetKeyDown(KeyCode.RightArrow))
        {
            animator.SetTrigger("RightAttack");
        }
        if (Input.GetKeyDown(KeyCode.Space))
        {
            animator.SetTrigger("Damage");
        }
        if (Input.GetKeyDown(KeyCode.D))
        {
            animator.SetBool("Death", true);
        }
    }
}
