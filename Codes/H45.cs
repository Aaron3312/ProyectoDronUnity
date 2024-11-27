using UnityEngine;
using UnityEngine.AI;
using System.Collections;
using System.Collections.Generic;

public class RobotAgent : MonoBehaviour
{
    public int id;
    public float stoppingDistance = 1.5f;
    public float hoverHeight = 3f;  // Altura de vuelo sobre el suelo
    public bool hasInitializedTakeoff = false;
    private float takeoffDuration = 4f;
    private float spinSpeed = 360f;
    private float initialHeight = -0.7f;
    private float takeoffHeight = 2.5f; // Altura máxima durante el despegue
    private Vector3 originalScale;
    private bool isMoving = false;
    private static Dictionary<int, int> cubeTargets = new Dictionary<int, int>();
    private static object lockObject = new object();
    private Rigidbody rb;
    private NavMeshAgent navAgent;
    private Transform attachmentPoint;
    private bool isExploring = false;
    private float explorationTimer = 0f;
    private float explorationDuration = 1f; // Duración de cada exploración en segundos
    private bool isWaiting = false;
    private bool isViewingHuman = false;

    private Animator animator;
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
        animator = GetComponent<Animator>();
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

    public void Land()
    {
        if (hasInitializedTakeoff == false)
        {
            return;
        }

        // Detener cualquier acción actual
        StopAllCoroutines();
        isWaiting = false;
        isExploring = false;
        isViewingHuman = false;
        
        // Posición inicial de despegue/aterrizaje
        Vector3 landingPosition = new Vector3(0.67f, initialHeight, -6.16f);
        
        // Primero moverse a la posición de aterrizaje
        StartCoroutine(PerformDramaticLanding(landingPosition));
    }

    public void MoveToTargetHuman(Vector3 target)
    {
        if (hasInitializedTakeoff == false)
        {
            return;
        }

        isWaiting = false;
        isExploring = false;
        isViewingHuman = true;

        StopAllCoroutines();
        
        // Detener inmediatamente el NavMeshAgent
        if (navAgent != null)
        {
            navAgent.isStopped = true;
            navAgent.ResetPath();
            navAgent.velocity = Vector3.zero;
        }

        // Detener cualquier movimiento del Rigidbody
        if (rb != null)
        {
            rb.linearVelocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
        }
        isViewingHuman = false;

        Debug.Log("Drone stopped immediately - human detected");
    }

    public void Wait()
    {
        if (hasInitializedTakeoff == false)
        {
            return;
        }

        isWaiting = true;
        StopAllCoroutines();
        
        // Optional: Make the drone hover in place or perform a subtle hovering animation
        StartCoroutine(HoverInPlace());
    }
    public void Takeoff()
    {
        Debug.Log($"Drone {id} is taking off");
        isWaiting = false;
        StopAllCoroutines();
        // Iniciar secuencia de despegue

        
        StartCoroutine(PerformDramaticTakeoff());
    }
    public void Explore()
    {
        //add a log to debug
        Debug.Log($"Drone {id} is exploring");
        if (hasInitializedTakeoff == false || isWaiting || isViewingHuman)
        {
            return;
        }

        if (isExploring && explorationTimer < explorationDuration)
        {
            return;
        }
        
        Vector3 randomPoint = GetRandomExplorationPoint();
        StopAllCoroutines();
        StartCoroutine(MoveToTargetCoroutine(randomPoint));

        // Iniciar nueva exploración
        isExploring = true;
        explorationTimer = 0f;
    }

IEnumerator PerformDramaticLanding(Vector3 landingPosition)
{
    Debug.Log($"Drone {id} iniciando secuencia de aterrizaje");
    
    // Asegurarnos de que el drone esté en estado de aterrizaje
    isWaiting = false;
    isExploring = false;
    isViewingHuman = false;
    
    // First move the drone to the landing position while maintaining height
    Vector3 approachPosition = new Vector3(landingPosition.x, transform.position.y, landingPosition.z);
    
    if (navAgent != null)
    {
        // Enable NavMeshAgent if it's disabled
        if (!navAgent.enabled)
        {
            navAgent.enabled = true;
            yield return null; // Wait a frame to ensure NavMeshAgent is properly initialized
        }

        bool pathFound = false;
        float pathFindingTimeout = 2f;
        float elapsedPathFindingTime = 0f;

        // Set destination and check for valid path
        if (navAgent.isOnNavMesh)
        {
            navAgent.SetDestination(approachPosition);
            
            // Wait for path calculation with timeout
            while (navAgent.pathStatus == NavMeshPathStatus.PathInvalid && 
                   elapsedPathFindingTime < pathFindingTimeout)
            {
                elapsedPathFindingTime += Time.deltaTime;
                yield return null;
            }

            pathFound = navAgent.pathStatus != NavMeshPathStatus.PathInvalid;
        }

        if (!pathFound)
        {
            Debug.LogWarning($"Drone {id} couldn't find valid path to landing position. Proceeding with direct landing.");
        }
        else
        {
            // Wait until we're close enough to the approach position
            while (Vector3.Distance(transform.position, approachPosition) > stoppingDistance)
            {
                yield return null;
            }
        }

        // Disable NavMeshAgent before vertical landing sequence
        navAgent.enabled = false;
    }

    // Begin dramatic landing sequence
    float landingDuration = 3f; // Reducido de 5f a 3f para que sea más rápido
    float elapsedTime = 0f;
    Vector3 startPos = transform.position;
    Vector3 finalPos = new Vector3(landingPosition.x, initialHeight, landingPosition.z);
    Quaternion startRotation = transform.rotation;
    Quaternion targetRotation = Quaternion.identity;
    
    // Phase 1: Hover and pre-landing effects (reducido el tiempo)
    float preLandingTime = 0.75f;
    while (elapsedTime < preLandingTime)
    {
        float t = elapsedTime / preLandingTime;
        float vibrationIntensity = 0.01f * (1 - t); // Reducida la intensidad
        transform.position += Random.insideUnitSphere * vibrationIntensity;
        
        // Escala suave
        float scale = 1f + Mathf.Sin(t * 10f) * 0.03f;
        transform.localScale = originalScale * scale;
        
        elapsedTime += Time.deltaTime;
        yield return null;
    }

    if (animator != null)
    {
        animator.SetBool("isEnding", true);
        animator.SetBool("isNothing", false);
    }

    // Phase 2: Dramatic descent
    elapsedTime = 0f;
    float rotationEndTime = landingDuration * 0.7f; // La rotación termina antes que el descenso
    
    while (elapsedTime < landingDuration)
    {
        float t = elapsedTime / landingDuration;
        
        // Curva de descenso suavizada
        float heightProgress = 1 - Mathf.Pow(1 - t, 2); // Curva cuadrática para suavizar el final
        Vector3 newPos = Vector3.Lerp(startPos, finalPos, heightProgress);
        
        // Rotación suave que termina antes que el descenso
        if (elapsedTime < rotationEndTime)
        {
            float rotT = elapsedTime / rotationEndTime;
            transform.rotation = Quaternion.Slerp(startRotation, targetRotation, rotT);
        }
        else
        {
            transform.rotation = targetRotation;
        }
        
        // Reducir la escala gradualmente
        float scaleT = Mathf.Clamp01(t * 1.5f); // Más rápido al principio
        transform.localScale = Vector3.Lerp(originalScale, originalScale * 0.98f, scaleT);
        
        // Sway suave que se reduce con el tiempo
        float sway = Mathf.Sin(t * Mathf.PI * 3) * 0.05f * (1 - t);
        newPos += transform.right * sway;
        
        transform.position = newPos;
        elapsedTime += Time.deltaTime;
        yield return null;
    }

    // Asegurar posición y rotación finales
    transform.position = finalPos;
    transform.rotation = targetRotation;
    transform.localScale = originalScale * 0.98f;
    
    if (rb != null)
    {
        rb.isKinematic = true;
    }
    
    // Desactivar el NavMeshAgent y establecer estados finales
    if (navAgent != null)
    {
        navAgent.enabled = false;
    }
    
    hasInitializedTakeoff = false;
    Debug.Log($"Drone {id} ha completado su secuencia de aterrizaje");
}

    IEnumerator HoverInPlace()
    {
        while (isWaiting)
        {
            transform.position += Vector3.up * Mathf.Sin(Time.time * 2f) * 0.02f;
            yield return null;
        }
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

    IEnumerator PerformDramaticTakeoff()
    {

        if (animator != null)
        {
            animator.SetBool("isStarted", true);
            animator.SetBool("isEnding", false);
            animator.SetBool("isNothing", true);
        }

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
    }

    public void MoveToTarget(Vector3 target)
    {
        if (hasInitializedTakeoff == false)
        {
            return;
        }

        isWaiting = false; // Clear waiting state when moving to target


        StopAllCoroutines();
        StartCoroutine(MoveToTargetCoroutine(target));
    }

    IEnumerator MoveToTargetCoroutine(Vector3 target)
    {
        if (navAgent != null)
        {
            Debug.Log($"Drone {id} moving to target: {target}");
            
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

            Debug.Log($"Drone {id} reached target position");

            // Una vez que llegamos al objetivo, podemos reiniciar la exploración
            isExploring = false;
            explorationTimer = 0f;
        }
    }
}