using UnityEngine;
using UnityEngine.AI;
using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections;
using Newtonsoft.Json;

public class SecurityCamera : MonoBehaviour
{
    public int cameraId;
    public Animator cameraAnimator;
    
    void Start()
    {
        // El controlador de animación se mantiene para el movimiento de la cámara
        if (cameraAnimator == null)
        {
            cameraAnimator = GetComponent<Animator>();
        }
    }

    void Update()
    {
        // Mantener la funcionalidad de control manual de la cámara
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