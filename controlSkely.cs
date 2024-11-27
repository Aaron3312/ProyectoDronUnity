using UnityEngine;
using System.Net.Sockets;
using System.Text;

public class SkeletonController : MonoBehaviour 
{
    public Animator animator;
    public float walkSpeed = 2.0f;    
    public float runSpeed = 8.0f;     
    private float currentSpeed;
    
    private TcpClient client;
    private NetworkStream stream;
    private string serverIP = "127.0.0.1";
    private int serverPort = 5782;

    void Start()
    {
        if (animator == null)
        {
            animator = GetComponent<Animator>();
        }
        
        ConnectToServer();
    }

    private void ConnectToServer()
    {
        try
        {
            client = new TcpClient(serverIP, serverPort);
            stream = client.GetStream();
            
            // Enviar identificación como cliente Unity
            byte[] identificationMessage = Encoding.UTF8.GetBytes("UNITY_CLIENT\n");
            stream.Write(identificationMessage, 0, identificationMessage.Length);
            
            Debug.Log("Conectado al servidor del dron y enviada identificación");
        }
        catch (SocketException e)
        {
            Debug.LogError($"Error de conexión con servidor del dron: {e.Message}");
        }
    }

    void OnDestroy()
    {
        if (client != null)
        {
            client.Close();
        }
    }

    void Update()
    {
        // Mantener detección de correr con Shift
        bool isRunning = Input.GetKey(KeyCode.LeftShift);
        currentSpeed = isRunning ? runSpeed : walkSpeed;

        // Movimiento WASD original
        float horizontal = Input.GetAxis("Horizontal");
        float vertical = Input.GetAxis("Vertical");
        Vector3 movement = new Vector3(horizontal, 0, vertical).normalized * currentSpeed;

        // Mantener animación de velocidad
        animator.SetFloat("Speed", movement.magnitude);

        // Mover el personaje
        transform.Translate(movement * Time.deltaTime, Space.World);

        // Rotar el personaje hacia la dirección del movimiento
        if (movement != Vector3.zero)
        {
            Quaternion targetRotation = Quaternion.LookRotation(movement);
            transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * 10f);
        }

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
        if (Input.GetKeyDown(KeyCode.K))
        {
            animator.SetBool("Death", true);
        }

        if (Input.GetKeyDown(KeyCode.G))
        {
            SendDroneLandingCommand();
        }
    }

    private void SendDroneLandingCommand()
    {
        if (stream != null)
        {
            try
            {
                // Si la conexión se perdió, intentar reconectar
                if (!client.Connected)
                {
                    Debug.Log("Reconectando al servidor...");
                    ConnectToServer();
                }

                byte[] data = Encoding.UTF8.GetBytes("aterriza dron\n");
                stream.Write(data, 0, data.Length);
                Debug.Log("Comando de aterrizaje enviado al dron desde agente de seguridad");
            }
            catch (SocketException e)
            {
                Debug.LogError($"Error al enviar comando al dron: {e.Message}");
                // Intentar reconectar en caso de error
                ConnectToServer();
            }
        }
        else
        {
            Debug.LogWarning("Stream no disponible, intentando reconectar...");
            ConnectToServer();
        }
    }
}