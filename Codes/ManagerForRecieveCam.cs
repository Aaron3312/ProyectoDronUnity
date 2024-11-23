using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using Newtonsoft.Json;

[Serializable]
public class DetectionData
{
    public int camera_id;
    public int track_id;
    public Position position;
    public float confidence;
}

[Serializable]
public class Position
{
    public float x;
    public float y;
}

public class DetectionReceiver : MonoBehaviour
{
    private UdpClient client;
    private Thread receiveThread;
    private bool isRunning = true;
    private SecurityCameraManager cameraManager;
    
    [SerializeField] private int detectionPort = 5555;
    [SerializeField] private float detectionThreshold = 0.5f;

    private void Start()
    {
        cameraManager = FindObjectOfType<SecurityCameraManager>();
        if (cameraManager == null)
        {
            Debug.LogError("SecurityCameraManager not found in scene!");
            return;
        }

        InitializeUDP();
    }

    private void InitializeUDP()
    {
        try
        {
            client = new UdpClient(detectionPort);
            receiveThread = new Thread(new ThreadStart(ReceiveData));
            receiveThread.IsBackground = true;
            receiveThread.Start();
            Debug.Log($"Started listening for detections on port {detectionPort}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Error initializing UDP: {e.Message}");
        }
    }

    private void ReceiveData()
    {
        IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, 0);

        while (isRunning)
        {
            try
            {
                byte[] data = client.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(data);
                
                DetectionData detection = JsonConvert.DeserializeObject<DetectionData>(json);
                
                if (detection != null && detection.confidence >= detectionThreshold)
                {
                    // Convertir la posición 2D normalizada a una posición 3D en el mundo
                    Vector3 worldPosition = ConvertToWorldPosition(detection);
                    
                    // Notificar al manager de cámaras
                    UnityMainThreadDispatcher.Instance().Enqueue(() => 
                        cameraManager.NotifyPersonDetected(worldPosition, detection.camera_id));
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Error receiving detection data: {e.Message}");
            }
        }
    }

    private Vector3 ConvertToWorldPosition(DetectionData detection)
    {
        // Esta es una implementación básica. Necesitarás adaptarla según tu setup específico
        // Por ejemplo, podrías usar rayos desde la cámara para determinar la posición real en el mundo
        
        Camera camera = cameraManager.GetCamera(detection.camera_id);
        if (camera == null) return Vector3.zero;

        // Convertir coordenadas normalizadas a viewport
        Vector3 viewportPoint = new Vector3(detection.position.x, detection.position.y, 10f);
        return camera.ViewportToWorldPoint(viewportPoint);
    }

    private void OnDestroy()
    {
        isRunning = false;
        if (receiveThread != null)
        {
            receiveThread.Join(1000);
        }
        if (client != null)
        {
            client.Close();
        }
    }
}