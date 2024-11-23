using UnityEngine;

public class ControlerStaticCams : MonoBehaviour
{
    // Start is called once before the first execution of Update after the MonoBehaviour is created

    public Animator cameraAnimator;

    void Start()
    {
        
    }

    // Update is called once per frame
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.Alpha1))
        {
            cameraAnimator.SetBool("CameraLeft", true);
            cameraAnimator.SetBool("CameraRight", false);
        }
        else if (Input.GetKeyDown(KeyCode.Alpha2))
        {
            cameraAnimator.SetBool("CameraLeft", false);
            cameraAnimator.SetBool("CameraRight", true);
        }
        else if (Input.GetKeyDown(KeyCode.Alpha3))
        {
            cameraAnimator.SetBool("CameraLeft", false);
            cameraAnimator.SetBool("CameraRight", false);
        }
    }
}
