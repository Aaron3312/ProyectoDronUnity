using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using UnityEngine.Networking;
using System.Text;
//this is for controlling the robot agent the drone in the simulation its called RobotWorld2
//this code is in folder Codes in the Assets
public class RobotWorld : MonoBehaviour
{
    public GameObject robotPrefab;
    private List<RobotAgent> robots = new List<RobotAgent>();
    private int nextRobotId = 0; // Add counter for unique IDs

    [System.Serializable]
    public class Target
    {
        public float x;
        public float y;
        public float z;
    }
    
    [System.Serializable]
    public class WorldState
    {
        // Change the dictionary to a serializable format
        public List<AgentStateEntry> agentStates = new List<AgentStateEntry>();
    }

    [System.Serializable]
    public class AgentStateEntry
    {
        public string id;
        public AgentState state;
    }

    [System.Serializable]
    public class AgentState
    {
        public Vector3 position;
    }



    [System.Serializable]
    public class Decision
    {
        public string decision;
        public Target target;

    }

    [System.Serializable]
    public class PythonResponse
    {
        public List<Decision> decisions;
    }

    void CreateInitialSetup()
    {

        // Crear robots con IDs únicos
        
        Vector3 robotPosition = new Vector3(0.7065587f, -1f, -6.189068f);
        GameObject robotObj = Instantiate(robotPrefab, robotPosition, Quaternion.identity);
        RobotAgent robot = robotObj.AddComponent<RobotAgent>();
        robot.id = 0; // Asignar ID único
        robot.name = $"Robot_{robot.id}"; // Nombrar el objeto con su ID
        robots.Add(robot);
        Debug.Log($"Created Robot with ID: {robot.id} at position {robotPosition}"); // Agregar log para debugging
        StartCoroutine(DecisionLoop());
    }



    WorldState GetCurrentWorldState()
    {
        WorldState state = new WorldState();

            foreach (RobotAgent robot in robots)
            {
               state.agentStates.Add(new AgentStateEntry
            {
                id = robot.id.ToString(),
                state = new AgentState
                {
                    position = robot.transform.position,
                }
            }); 
            Debug.Log($"Agent {robot.id} state added to world state.");
            }

            // Logging for debugging
        

        // Log to check the complete state
        return state;
    }


     IEnumerator DecisionLoop()
    {
        while (true)
        {
            WorldState currentState = GetCurrentWorldState();
            string jsonState = JsonUtility.ToJson(currentState);
            Debug.Log($"Sending state: {jsonState}"); // Add logging for debugging

            using (UnityWebRequest www = new UnityWebRequest("http://localhost:5000/get_decisions", "POST"))
            {
                byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonState);
                www.uploadHandler = new UploadHandlerRaw(bodyRaw);
                www.downloadHandler = new DownloadHandlerBuffer();
                www.SetRequestHeader("Content-Type", "application/json");

                yield return www.SendWebRequest();

                if (www.result == UnityWebRequest.Result.Success)
                {
                    string responseText = www.downloadHandler.text;
                    // Debug.Log($"Received response: {responseText}"); // Add logging for debugging
                    PythonResponse response = JsonUtility.FromJson<PythonResponse>(responseText);
                    ExecuteDecisions(response.decisions);
                }
                else
                {
                    Debug.LogError($"Error: {www.error}");
                }
            }

        yield return new WaitForSeconds(3f); // Aumentado desde 1f a 3f
        }
    }
    void ExecuteDecisions(List<Decision> decisions)
    {
        for (int i = 0; i < decisions.Count && i < robots.Count; i++)
        {
            Decision decision = decisions[i];
            RobotAgent robot = robots[i];

            switch (decision.decision)
            {
                case "explore":
                    robot.Explore();
                    break;
                case "move_to_target":
                    if (decision.target != null)
                    {
                        Vector3 targetPosition = new Vector3(
                            decision.target.x,
                            decision.target.y,
                            decision.target.z
                        );
                        robot.MoveToTarget(targetPosition);
                    }
                    break;
                case "move_to_target_human":
                    if (decision.target != null)
                    {
                        Vector3 targetPosition = new Vector3(
                            decision.target.x,
                            decision.target.y,
                            decision.target.z
                        );
                        robot.MoveToTargetHuman(targetPosition);
                    }
                    break;
                case "wait":
                    robot.Wait();
                    break; 
            }
        }
    }


    void Start()
    {
        CreateInitialSetup();
    }
}

