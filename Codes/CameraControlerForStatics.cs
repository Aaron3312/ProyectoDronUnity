using UnityEngine;
using System;
using System.Net.Sockets;
using System.Threading;
using System.Collections;
using System.Collections.Concurrent;

public class StaticSecurityCamera : MonoBehaviour
{
    [SerializeField] private int captureWidth = 640;
    [SerializeField] private int captureHeight = 480;
    [SerializeField] private int streamPort = 5124;
    [SerializeField] private int quality = 75;
    [SerializeField] private float captureInterval = 0.033f;
    [SerializeField] private float rotationSpeed = 30f; // Velocidad de rotación en grados por segundo
    [SerializeField] private float maxRotationAngle = 45f; // Ángulo máximo de rotación a cada lado

    private Camera securityCamera;
    private RenderTexture renderTexture;
    private Texture2D screenShot;
    private int cameraId;
    private bool isCapturing = true;
    private UdpClient udpClient;
    private Thread streamThread;
    private bool isStreaming = true;
    private ConcurrentQueue<byte[]> frameQueue = new ConcurrentQueue<byte[]>();

    // Variables para el control de movimiento
    private bool isRotatingRight = true;
    private bool personDetected = false;
    private Vector3 targetRotation;
    private bool isTrackingPerson = false;

    public void Initialize(int id)
    {
        cameraId = id;
        InitializeCamera();
        InitializeStreaming();
        StartCoroutine(CaptureFrames());
    }

    void InitializeCamera()
    {
        securityCamera = GetComponent<Camera>();
        if (securityCamera == null)
        {
            securityCamera = gameObject.AddComponent<Camera>();
        }

        securityCamera.fieldOfView = 60;
        securityCamera.nearClipPlane = 0.1f;
        securityCamera.farClipPlane = 80f;

        renderTexture = new RenderTexture(captureWidth, captureHeight, 24);
        screenShot = new Texture2D(captureWidth, captureHeight, TextureFormat.RGB24, false);
        securityCamera.targetTexture = renderTexture;

        Debug.Log($"Security Camera {cameraId} initialized");
    }

    void InitializeStreaming()
    {
        try
        {
            udpClient = new UdpClient();
            streamThread = new Thread(StreamFrames);
            streamThread.Start();
            Debug.Log($"Camera {cameraId}: Started UDP streaming on port {streamPort + cameraId}");
        }
        catch (Exception e)
        {
            Debug.LogError($"Camera {cameraId}: Failed to initialize streaming: {e.Message}");
        }
    }

    void Update()
    {
        // if (!isTrackingPerson)
        // {
        //     // Movimiento normal de vigilancia
        //     PerformSurveillanceMovement();
        // }
        // else
        // {
        //     // Seguimiento de persona detectada
        //     TrackPerson();
        // }
    }

    public void OnPersonDetected(Vector3 personPosition)
    {
        isTrackingPerson = true;
        targetRotation = Quaternion.LookRotation(personPosition - transform.position).eulerAngles;
    }

    private void PerformSurveillanceMovement()
    {
        float currentYRotation = transform.eulerAngles.y;
        float normalizedRotation = NormalizeAngle(currentYRotation);

        if (isRotatingRight && normalizedRotation >= maxRotationAngle)
        {
            isRotatingRight = false;
        }
        else if (!isRotatingRight && normalizedRotation <= -maxRotationAngle)
        {
            isRotatingRight = true;
        }

        float rotationDirection = isRotatingRight ? 1 : -1;
        transform.Rotate(Vector3.up, rotationSpeed * rotationDirection * Time.deltaTime);
    }

    private void TrackPerson()
    {
        // Rotación suave hacia el objetivo
        Vector3 currentRotation = transform.eulerAngles;
        currentRotation.y = Mathf.LerpAngle(currentRotation.y, targetRotation.y, Time.deltaTime * 2f);
        transform.eulerAngles = currentRotation;
    }

    private float NormalizeAngle(float angle)
    {
        while (angle > 180) angle -= 360;
        while (angle < -180) angle += 360;
        return angle;
    }

    IEnumerator CaptureFrames()
    {
        WaitForSeconds waitInterval = new WaitForSeconds(captureInterval);
        while (isStreaming)
        {
            if (isCapturing)
            {
                RenderTexture.active = renderTexture;
                securityCamera.Render();
                screenShot.ReadPixels(new Rect(0, 0, captureWidth, captureHeight), 0, 0);
                screenShot.Apply();
                RenderTexture.active = null;

                byte[] frameData = screenShot.EncodeToJPG(quality);
                byte[] header = BitConverter.GetBytes(cameraId);
                byte[] packetData = new byte[header.Length + frameData.Length];
                header.CopyTo(packetData, 0);
                frameData.CopyTo(packetData, header.Length);

                frameQueue.Enqueue(packetData);
            }
            yield return waitInterval;
        }
    }

    void StreamFrames()
    {
        while (isStreaming)
        {
            try
            {
                if (frameQueue.TryDequeue(out byte[] frameData))
                {
                    udpClient.Send(frameData, frameData.Length, "127.0.0.1", streamPort + cameraId);
                }
                else
                {
                    Thread.Sleep(1);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Camera {cameraId} streaming error: {e.Message}");
                Thread.Sleep(1000);
            }
        }
    }

    void OnDestroy()
    {
        isStreaming = false;
        if (streamThread != null && streamThread.IsAlive)
        {
            streamThread.Join(1000);
        }
        if (udpClient != null)
        {
            udpClient.Close();
        }
        if (renderTexture != null)
        {
            renderTexture.Release();
        }
        if (screenShot != null)
        {
            Destroy(screenShot);
        }
    }
}