using UnityEngine;
using UnityEngine.AI;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections;
using Newtonsoft.Json;

// Estructura para los datos de detección recibidos de Python
[System.Serializable]
public class DetectionData
{
    public int camera_id;
    public int track_id;
    public Position position;
    public float confidence;
}

[System.Serializable]
public class Position
{
    public float x;
    public float y;
}

public class SecurityDrone : MonoBehaviour
{
    private NavMeshAgent navAgent;
    private UdpClient udpClient;
    private bool isInvestigating = false;
    public float hoverHeight = 3f;
    public float stoppingDistance = 1.5f;
    
    // Posiciones de las cámaras en el mundo
    private Vector3[] cameraPositions = new Vector3[]
    {
        new Vector3(-2.833347f, 8f, 44.74295f),
        new Vector3(-61f, 10f, 67f),
        new Vector3(52f, 4f, -35.0f),
        new Vector3(28.24f, 4f, -104.0f)
    };

    void Start()
    {
        InitializeAgent();
        StartCoroutine(ListenForDetections());
    }

    void InitializeAgent()
    {
        navAgent = GetComponent<NavMeshAgent>();
        if (navAgent != null)
        {
            navAgent.stoppingDistance = stoppingDistance;
            navAgent.baseOffset = hoverHeight;
            navAgent.speed = 15f;
            navAgent.angularSpeed = 120f;
            navAgent.acceleration = 5f;
        }

        // Deshabilitar la gravedad ya que es un dron
        var rb = GetComponent<Rigidbody>();
        if (rb != null)
        {
            rb.useGravity = false;
            rb.constraints = RigidbodyConstraints.FreezeRotation;
        }
    }

    IEnumerator ListenForDetections()
    {
        udpClient = new UdpClient(5555); // Puerto para recibir detecciones de Python

        while (true)
        {
            try
            {
                IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);
                byte[] data = udpClient.Receive(ref remoteEndPoint);
                string jsonData = Encoding.UTF8.GetString(data);
                DetectionData detection = JsonConvert.DeserializeObject<DetectionData>(jsonData);

                if (detection != null && !isInvestigating)
                {
                    StartCoroutine(InvestigateDetection(detection));
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Error receiving detection: {e.Message}");
            }
            yield return new WaitForSeconds(0.1f);
        }
    }

    IEnumerator InvestigateDetection(DetectionData detection)
    {
        isInvestigating = true;

        // Obtener la posición de la cámara que detectó la persona
        Vector3 cameraPosition = cameraPositions[detection.camera_id];
        
        // Calcular punto de investigación basado en la posición normalizada de la detección
        float detectionRadius = 5f; // Radio de búsqueda alrededor de la cámara
        Vector3 investigationPoint = new Vector3(
            cameraPosition.x + (detection.position.x - 0.5f) * detectionRadius,
            hoverHeight,
            cameraPosition.z + (detection.position.y - 0.5f) * detectionRadius
        );

        // Mover el dron al punto de investigación
        navAgent.SetDestination(investigationPoint);

        // Esperar a que el dron llegue al destino
        while (navAgent.pathStatus == NavMeshPathStatus.PathPartial ||
               navAgent.remainingDistance > navAgent.stoppingDistance)
        {
            yield return new WaitForSeconds(0.5f);
        }

        // Realizar patrulla en el área
        yield return StartCoroutine(PatrolArea(investigationPoint));

        isInvestigating = false;
    }

    IEnumerator PatrolArea(Vector3 center)
    {
        float patrolRadius = 5f;
        int patrolPoints = 4;
        float patrolDuration = 10f;

        float startTime = Time.time;
        while (Time.time - startTime < patrolDuration)
        {
            for (int i = 0; i < patrolPoints; i++)
            {
                float angle = i * (360f / patrolPoints);
                Vector3 patrolPoint = center + Quaternion.Euler(0, angle, 0) * Vector3.forward * patrolRadius;
                patrolPoint.y = hoverHeight;

                navAgent.SetDestination(patrolPoint);
                
                while (navAgent.pathStatus == NavMeshPathStatus.PathPartial ||
                       navAgent.remainingDistance > navAgent.stoppingDistance)
                {
                    yield return new WaitForSeconds(0.5f);
                }
            }
        }
    }

    void OnDestroy()
    {
        if (udpClient != null)
        {
            udpClient.Close();
        }
    }
}

