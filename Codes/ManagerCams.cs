// SecurityCameraManager.cs
using UnityEngine;
using System.Collections.Generic;
//this is for controlling the security cameras in the simulation its called SecurityCameraManager
public class SecurityCameraManager : MonoBehaviour
{
    [SerializeField] private GameObject cameraPrefab;
    [SerializeField] private Vector3[] cameraPositions;
    [SerializeField] private Vector3[] cameraRotations;
    
    private List<StaticSecurityCamera> securityCameras = new List<StaticSecurityCamera>();
    private Dictionary<int, Camera> unityCamera = new Dictionary<int, Camera>();

    void Start()
    {
        InitializeCameras();
    }

    void InitializeCameras()
    {
        for (int i = 0; i < cameraPositions.Length; i++)
        {
            // Instantiate the main prefab
            GameObject cameraObj = Instantiate(cameraPrefab, cameraPositions[i], Quaternion.Euler(cameraRotations[i]));
            
            // Find the actual camera object (assuming it's two levels deep: Prefab -> Base -> Camera)
            Transform baseTransform = cameraObj.transform.Find("Base");
            if (baseTransform == null)
            {
                Debug.LogError($"Camera {i}: Base object not found in prefab hierarchy!");
                continue;
            }

            Transform cameraTransform = baseTransform.Find("Camera");
            if (cameraTransform == null)
            {
                Debug.LogError($"Camera {i}: Camera object not found in Base hierarchy!");
                continue;
            }

            // Get or add both camera components
            StaticSecurityCamera securityCamera = cameraTransform.gameObject.GetComponent<StaticSecurityCamera>();
            if (securityCamera == null)
            {
                securityCamera = cameraTransform.gameObject.AddComponent<StaticSecurityCamera>();
            }

            Camera camera = cameraTransform.gameObject.GetComponent<Camera>();
            if (camera == null)
            {
                camera = cameraTransform.gameObject.AddComponent<Camera>();
            }
            
            securityCamera.Initialize(i);
            securityCameras.Add(securityCamera);
            unityCamera[i] = camera;
        }
    }

    public StaticSecurityCamera GetSecurityCamera(int cameraId)
    {
        if (cameraId >= 0 && cameraId < securityCameras.Count)
        {
            return securityCameras[cameraId];
        }
        Debug.LogWarning($"Security camera with ID {cameraId} not found!");
        return null;
    }

    public Camera GetCamera(int cameraId)
    {
        if (unityCamera.TryGetValue(cameraId, out Camera camera))
        {
            return camera;
        }
        Debug.LogWarning($"Unity camera with ID {cameraId} not found!");
        return null;
    }

    public void NotifyPersonDetected(Vector3 personPosition, int detectedByCameraId)
    {
        // Notificar a todas las cámaras sobre la posición de la persona
        foreach (var camera in securityCameras)
        {
            camera.OnPersonDetected(personPosition);
        }
    }
}