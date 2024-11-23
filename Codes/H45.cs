using UnityEngine;
using UnityEngine.AI;
using System.Collections;
using System.Collections.Generic;

public class RobotAgent : MonoBehaviour
{
    public int id;
    public bool hasCube;
    public float stoppingDistance = 1.5f;
    public float hoverHeight = 3f;  // Altura de vuelo sobre el suelo
    
        // Nuevas variables para el despegue
    public bool hasInitializedTakeoff = false;
    private float takeoffDuration = 4f;
    private float spinSpeed = 360f;
    private float initialHeight = -0.7f;
    private float takeoffHeight = 2.5f; // Altura máxima durante el despegue
    private Vector3 originalScale;

    private GameObject carriedCube;
    private GameObject targetedCube;
    private bool isMoving = false;
    private static Dictionary<int, int> cubeTargets = new Dictionary<int, int>();
    private static object lockObject = new object();
    private Rigidbody rb;
    
    // NavMesh components
    private NavMeshAgent navAgent;
    private Transform attachmentPoint;
    private bool isExploring = false;
    private float explorationTimer = 0f;
    private float explorationDuration = 10f; // Duración de cada exploración en segundos

    private static readonly Vector3[] explorationPoints = new Vector3[]
    {
        new Vector3(-7.384952f, 0f, -15.99f),
        new Vector3(-7.384952f, 0f, -36.09f),
        new Vector3(14.8f, 0f, -85.92f),
        new Vector3(13.3f, 0f, -58.2f),
        new Vector3(23.9f, 0f, -17.6f),
        new Vector3(43.5f, 0f, -36.0f),
        new Vector3(7.0f, 0f, 51.0f),
        new Vector3(-57.4f, 0f, 51.0f),
        new Vector3(-57.0f, 0f, 7.6f)
    };
    
    private int currentExplorationIndex = 0;

    void Start()
    {
        // Get required components
        navAgent = GetComponent<NavMeshAgent>();
        rb = GetComponent<Rigidbody>();
        attachmentPoint = transform.Find("AttachmentPoint");
        originalScale = transform.localScale;

        // Configure NavMeshAgent for flying
        if (navAgent != null)
        {
            navAgent.enabled = false; // Desactivar inicialmente el NavMeshAgent
            navAgent.stoppingDistance = stoppingDistance;
            navAgent.speed = 15f;
            navAgent.angularSpeed = 120f;
            navAgent.acceleration = 5f;
            navAgent.baseOffset = 0.2f;  // Set the agent's height above the NavMesh
            navAgent.radius = 0.3f;
            navAgent.autoTraverseOffMeshLink = true;  // Auto handle links since we're flying
        }

        if (rb != null)
        {
            rb.useGravity = false;  // Disable gravity since we're flying
            rb.constraints = RigidbodyConstraints.FreezeRotation;
        }
                // Iniciar secuencia de despegue
        transform.position = new Vector3(transform.position.x, initialHeight, transform.position.z);
        StartCoroutine(PerformDramaticTakeoff());
    }

    

    void Update()
    {

        if (hasInitializedTakeoff == false)
        {
            return;
        }



        if (navAgent != null)
        {
            isMoving = navAgent.velocity.magnitude > 0.1f;
            
            // Maintain hover height
            Vector3 currentPos = transform.position;
            RaycastHit hit;
            if (Physics.Raycast(currentPos, Vector3.down, out hit))
            {
                float targetHeight = hit.point.y + hoverHeight;
                currentPos.y = Mathf.Lerp(currentPos.y, targetHeight, Time.deltaTime * 5f);
                transform.position = currentPos;
            }
                        // Actualizar timer de exploración
            if (isExploring)
            {
                explorationTimer += Time.deltaTime;
                if (explorationTimer >= explorationDuration)
                {
                    isExploring = false;
                    explorationTimer = 0f;
                }
            }
        
        }
    }

    public void MoveToCube(GameObject cube)
    {
        if (!hasCube && cube != null)
        {
            var cubeController = cube.GetComponent<CubeController>();
            if (cubeController != null && TryClaimCube(cubeController.cubeId))
            {
                targetedCube = cube;
                StopAllCoroutines();
                StartCoroutine(MoveToTarget(cube.transform.position));
                Debug.Log($"Drone {id} moving to pick up cube {cubeController.cubeId}");
            }
            else
            {
                Explore();
            }
        }
    }

    public void MoveToDeliveryZone(Vector3 deliveryZone)
    {
        if (hasCube)
        {
            StopAllCoroutines();
            Vector3 dropoffPoint = GetRandomPointAroundPosition(deliveryZone, 2f);
            StartCoroutine(MoveToTarget(dropoffPoint));
            Debug.Log($"Drone {id} moving to delivery zone with cube");
        }
    }

    public void Explore()
    {
        if (hasInitializedTakeoff == false)
        {
            return;
        }

        if (isExploring && explorationTimer < explorationDuration)
        {
            return;
        }
        Vector3 randomPoint = GetRandomExplorationPoint();
        StopAllCoroutines();
        StartCoroutine(MoveToTarget(randomPoint));

        // Iniciar nueva exploración
        isExploring = true;
        explorationTimer = 0f;
    }
    private Vector3 GetRandomExplorationPoint()
    {
        // Get a random point from our predefined array
        Vector3 point = explorationPoints[Random.Range(0, explorationPoints.Length)];
        
        // Sample the nearest valid position on the NavMesh
        if (NavMesh.SamplePosition(point, out NavMeshHit hit, 20f, NavMesh.AllAreas))
        {
            return new Vector3(hit.position.x, hit.position.y + hoverHeight, hit.position.z);
        }
        
        // If no valid position found, return the original point with hover height
        return new Vector3(point.x, point.y + hoverHeight, point.z);
    }


    Vector3 GetRandomNavMeshPosition()
    {
        Vector3 randomPos = new Vector3(
            Random.Range(-55f, 82f),
            hoverHeight,
            Random.Range(48f, -100f)
        );

        if (NavMesh.SamplePosition(randomPos, out NavMeshHit hit, 20f, NavMesh.AllAreas))
        {
            return new Vector3(hit.position.x, hit.position.y + hoverHeight, hit.position.z);
        }

        return transform.position;
    }

    Vector3 GetRandomPointAroundPosition(Vector3 center, float radius)
    {
        Vector3 randomPos = center + Random.insideUnitSphere * radius;
        randomPos.y = center.y + hoverHeight;

        if (NavMesh.SamplePosition(randomPos, out NavMeshHit hit, radius, NavMesh.AllAreas))
        {
            return new Vector3(hit.position.x, hit.position.y + hoverHeight, hit.position.z);
        }

        return new Vector3(center.x, center.y + hoverHeight, center.z);
    }

    IEnumerator PerformDramaticTakeoff()
    {
        // Efectos de "calentamiento" antes del despegue
        float warmupTime = 1.5f;
        float elapsedTime = 0f;
        
        // Vibración suave durante el calentamiento
        while (elapsedTime < warmupTime)
        {
            float vibrationIntensity = 0.02f * (1 - (elapsedTime / warmupTime));
            transform.position += Random.insideUnitSphere * vibrationIntensity;
            transform.localScale = originalScale + Vector3.one * Mathf.Sin(elapsedTime * 20f) * 0.02f;
            elapsedTime += Time.deltaTime;
            yield return null;
        }

        // Despegue principal
        elapsedTime = 0f;
        Vector3 startPos = transform.position;
        Vector3 peakPos = new Vector3(startPos.x, takeoffHeight, startPos.z);
        
        while (elapsedTime < takeoffDuration)
        {
            float t = elapsedTime / takeoffDuration;
            
            // Movimiento vertical con efecto de suavizado
            float heightProgress = Mathf.Sin(t * Mathf.PI * 0.5f);
            Vector3 newPos = Vector3.Lerp(startPos, peakPos, heightProgress);
            
            // Rotación dramática
            transform.Rotate(Vector3.up, spinSpeed * Time.deltaTime * (1 - t));
            
            // Efecto de escala pulsante
            float scale = 1f + Mathf.Sin(t * Mathf.PI * 4) * 0.1f * (1 - t);
            transform.localScale = originalScale * scale;
            
            transform.position = newPos;
            elapsedTime += Time.deltaTime;
            yield return null;
        }

        // Estabilización final
        elapsedTime = 0f;
        float stabilizationTime = 0.5f;
        Vector3 finalPos = new Vector3(transform.position.x, hoverHeight, transform.position.z);
        
        while (elapsedTime < stabilizationTime)
        {
            float t = elapsedTime / stabilizationTime;
            transform.position = Vector3.Lerp(transform.position, finalPos, t);
            transform.localScale = Vector3.Lerp(transform.localScale, originalScale, t);
            elapsedTime += Time.deltaTime;
            yield return null;
        }

        // Finalizar secuencia de despegue
        transform.localScale = originalScale;
        transform.rotation = Quaternion.identity;
        navAgent.enabled = true;
        hasInitializedTakeoff = true;
        
        Debug.Log($"Drone {id} ha completado su secuencia de despegue");
        Explore();
    }
    IEnumerator MoveToTarget(Vector3 target)
    {
        if (navAgent != null)
        {
            // Adjust target position to hover height
            Vector3 targetWithHeight = new Vector3(target.x, target.y + hoverHeight, target.z);
            navAgent.SetDestination(targetWithHeight);
            
            while (navAgent.pathStatus == NavMeshPathStatus.PathInvalid)
            {
                yield return new WaitForSeconds(0.1f);
            }

            while (navAgent.pathStatus == NavMeshPathStatus.PathPartial)
            {
                yield return null;
            }

            while (navAgent.pathStatus == NavMeshPathStatus.PathComplete &&
                   !navAgent.isStopped &&
                   navAgent.remainingDistance > navAgent.stoppingDistance)
            {
                yield return null;
            }

            // Handle arrival at destination
            if (!hasCube && targetedCube != null)
            {
                if (Vector3.Distance(transform.position, targetedCube.transform.position) < stoppingDistance * 1.2f)
                {
                    yield return StartCoroutine(PickupCube(targetedCube));
                }
                else
                {
                    var cubeController = targetedCube.GetComponent<CubeController>();
                    if (cubeController != null)
                    {
                        ReleaseCube(cubeController.cubeId);
                    }
                    targetedCube = null;
                }
            }
            else if (transform.position.x > 10)
            {
                yield return StartCoroutine(DropCube());
            }
        }
    }

    IEnumerator PickupCube(GameObject cube)
    {
        var cubeController = cube.GetComponent<CubeController>();
        if (cubeController == null || cubeController.isCarried || attachmentPoint == null)
        {
            Debug.Log("Cannot pick up cube: controller is null, cube is carried, or attachment point not found");
            yield break;
        }

        var rigidbody = cube.GetComponent<Rigidbody>();
        if (rigidbody != null)
        {
            rigidbody.isKinematic = true;
        }

        cube.transform.SetParent(attachmentPoint);
        cube.transform.localPosition = Vector3.zero;
        cube.transform.localRotation = Quaternion.identity;
        
        carriedCube = cube;
        cubeController.isCarried = true;
        hasCube = true;
        targetedCube = null;
        
        Debug.Log($"Drone {id} picked up cube {cubeController.cubeId}");
    }

    IEnumerator DropCube()
    {
        if (carriedCube == null) yield break;

        var cubeController = carriedCube.GetComponent<CubeController>();
        if (cubeController == null) yield break;

        carriedCube.transform.SetParent(null);

        var rigidbody = carriedCube.GetComponent<Rigidbody>();
        if (rigidbody != null)
        {
            rigidbody.isKinematic = false;
        }

        Vector3 dropPosition = new Vector3(transform.position.x, 0.1f, transform.position.z);
        carriedCube.transform.position = dropPosition;

        cubeController.isCarried = false;
        ReleaseCube(cubeController.cubeId);
        Debug.Log($"Drone {id} dropped cube {cubeController.cubeId}");
        carriedCube = null;
        hasCube = false;
    }

    private bool TryClaimCube(int cubeId)
    {
        lock (lockObject)
        {
            if (cubeTargets.TryGetValue(cubeId, out int targetingAgent))
            {
                if (targetingAgent == id)
                    return true;
                return false;
            }

            cubeTargets[cubeId] = id;
            Debug.Log($"Drone {id} claimed cube {cubeId}");
            return true;
        }
    }

    private void ReleaseCube(int cubeId)
    {
        lock (lockObject)
        {
            if (cubeTargets.ContainsKey(cubeId) && cubeTargets[cubeId] == id)
            {
                cubeTargets.Remove(cubeId);
                Debug.Log($"Drone {id} released cube {cubeId}");
            }
        }
    }

    public void PutCube()
    {
        if (hasCube)
        {
            StopAllCoroutines();
            StartCoroutine(DropCube());
        }
    }

    GameObject FindNearestCube()
    {
        GameObject nearest = null;
        float minDistance = float.MaxValue;

        foreach (GameObject cube in GameObject.FindGameObjectsWithTag("Cube"))
        {
            var cubeController = cube.GetComponent<CubeController>();
            if (cubeController == null) continue;

            if (cubeController.isCarried || 
                cubeController.isInPlaneB ||
                (cubeTargets.ContainsKey(cubeController.cubeId) && cubeTargets[cubeController.cubeId] != id))
            {
                continue;
            }

            float distance = Vector3.Distance(transform.position, cube.transform.position);
            if (distance < minDistance)
            {
                minDistance = distance;
                nearest = cube;
            }
        }

        return nearest;
    }
}