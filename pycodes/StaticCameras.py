import cv2
import numpy as np
import socket
import threading
import struct
import time
import logging
from ultralytics import YOLO
import torch
import json
from collections import defaultdict
#this code is called staticCameras.py and is in the folder pycodes in the assets folder
#this code is for the static cameras that are in the environment, they are 4 cameras that are in the corners of the environment
#this detect the people in the environment and send the data to the unity app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityCameraSystem:
    def __init__(self, num_cameras=4, base_port=5123):
        self.num_cameras = num_cameras
        self.base_port = base_port
        self.running = True
        self.frame_buffer = {}
        self.lock = threading.Lock()
        
        # Tracking temporal de detecciones
        self.detection_history = defaultdict(lambda: defaultdict(dict))
        self.MIN_DETECTION_TIME = 0.1 # Tiempo mínimo de detección continua (segundos)
        self.MAX_POSITION_CHANGE = 1000  # Cambio máximo permitido en posición normalizada entre frames
        self.CLEANUP_INTERVAL = 5.0  # Intervalo para limpiar detecciones antiguas
        
        # Cargar modelo YOLOv8
        self.model = YOLO('yolov8n.pt')
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Socket para enviar datos de detección
        self.unity_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.unity_detection_port = 5556
        
        # Último tiempo de limpieza
        self.last_cleanup_time = time.time()
        
    def _is_valid_detection(self, camera_id, track_id, position, current_time):
        """
        Verifica si una detección es válida basada en su historia temporal y movimiento
        """
        history = self.detection_history[camera_id][track_id]
        
        # Si es una nueva detección
        if not history:
            history['first_seen'] = current_time
            history['last_seen'] = current_time
            history['positions'] = [position]
            history['confirmed'] = False
            return False
        
        # Actualizar último tiempo visto
        history['last_seen'] = current_time
        
        # Verificar si el movimiento es realista
        if history['positions']:
            last_position = history['positions'][-1]
            position_change = np.sqrt(
                (position['x'] - last_position['x'])**2 + 
                (position['y'] - last_position['y'])**2
            )
            
            # Si el cambio de posición es muy grande, podría ser un falso positivo
            if position_change > self.MAX_POSITION_CHANGE:
                history['positions'] = [position]  # Reiniciar tracking
                history['first_seen'] = current_time
                history['confirmed'] = False
                return False
        
        # Actualizar historial de posiciones
        history['positions'].append(position)
        if len(history['positions']) > 10:  # Mantener solo las últimas 10 posiciones
            history['positions'].pop(0)
        
        # Verificar tiempo mínimo de detección
        detection_duration = current_time - history['first_seen']
        
        # Si ya está confirmada, mantener la confirmación
        if history['confirmed']:
            return True
        
        # Si cumple el tiempo mínimo, confirmar la detección
        if detection_duration >= self.MIN_DETECTION_TIME:
            history['confirmed'] = True
            return True
            
        return False
    
    def _cleanup_old_detections(self, current_time):
        """
        Limpia detecciones antiguas que ya no están activas
        """
        if current_time - self.last_cleanup_time < self.CLEANUP_INTERVAL:
            return
            
        self.last_cleanup_time = current_time
        
        for camera_id in list(self.detection_history.keys()):
            for track_id in list(self.detection_history[camera_id].keys()):
                history = self.detection_history[camera_id][track_id]
                if current_time - history['last_seen'] > self.MIN_DETECTION_TIME:
                    del self.detection_history[camera_id][track_id]
    
    def process_frame(self, frame, camera_id):
        try:
            current_time = time.time()
            self._cleanup_old_detections(current_time)
            
            # Ejecutar detección con YOLOv8
            results = self.model.track(frame, persist=True, classes=[0])
            
            if results and len(results) > 0:
                result = results[0]
                
                if hasattr(result, 'boxes') and len(result.boxes) > 0:
                    # Procesar detecciones
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    track_ids = result.boxes.id.cpu().numpy() if result.boxes.id is not None else None
                    
                    # Dibujar detecciones
                    annotated_frame = frame.copy()
                    
                    for i, box in enumerate(boxes):
                        if confidences[i] > 0.5:  # Umbral de confianza
                            x1, y1, x2, y2 = map(int, box)
                            track_id = int(track_ids[i]) if track_ids is not None else i
                            
                            # Calcular posición central normalizada
                            position = {
                                'x': (x1 + x2) / (2 * frame.shape[1]),
                                'y': (y1 + y2) / (2 * frame.shape[0])
                            }
                            
                            # Verificar si la detección es válida
                            if self._is_valid_detection(camera_id, track_id, position, current_time):
                                # Dibujar bbox en verde para detecciones confirmadas
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                
                                # Añadir texto de tiempo de tracking
                                tracking_time = current_time - self.detection_history[camera_id][track_id]['first_seen']
                                cv2.putText(annotated_frame, 
                                          f"ID: {track_id} Time: {tracking_time:.1f}s",
                                          (x1, y1 - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX,
                                          0.5,
                                          (0, 255, 0),
                                          2)
                                
                                # Enviar datos solo de detecciones confirmadas
                                detection_data = {
                                    'camera_id': camera_id,
                                    'track_id': track_id,
                                    'position': position,
                                    'confidence': float(confidences[i]),
                                    'tracking_time': tracking_time
                                }
                                self._send_detection_to_unity(detection_data)
                            else:
                                # Dibujar bbox en rojo para detecciones no confirmadas
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
                    return annotated_frame
            
            return frame
        
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return frame
    
    def _send_detection_to_unity(self, detection_data):
        try:
            data_str = json.dumps(detection_data)
            self.unity_socket.sendto(data_str.encode(), ('127.0.0.1', self.unity_detection_port))
        except Exception as e:
            logger.error(f"Error sending detection to Unity: {e}")
    
    def _receive_camera_stream(self, camera_id):
        port = self.base_port + camera_id
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            sock.bind(('0.0.0.0', port))
            sock.settimeout(1.0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        except Exception as e:
            logger.error(f"Error setting up socket for camera {camera_id}: {e}")
            return
        
        while self.running:
            try:
                data, _ = sock.recvfrom(65535)
                
                if len(data) < 4:
                    continue
                
                received_camera_id = struct.unpack('i', data[:4])[0]
                if received_camera_id != camera_id:
                    continue
                
                img_data = data[4:]
                nparr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    processed_frame = self.process_frame(frame, camera_id)
                    with self.lock:
                        self.frame_buffer[camera_id] = processed_frame
            
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in reception for camera {camera_id}: {e}")
                continue
    
    def start(self):
        logger.info("Starting Security Camera System")
        
        # Iniciar hilos para cada cámara
        threads = []
        for i in range(self.num_cameras):
            thread = threading.Thread(
                target=self._receive_camera_stream,
                args=(i,),
                name=f"Camera-{i}"
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Iniciar visualización
        self._display_feeds()
        
        # Limpieza
        self.running = False
        for thread in threads:
            thread.join()
        
    def _display_feeds(self):
        cv2.namedWindow('Security Camera Feeds', cv2.WINDOW_NORMAL)
        
        while self.running:
            try:
                with self.lock:
                    frames = self.frame_buffer.copy()
                
                if frames:
                    # Crear grid de 2x2 para las 4 cámaras
                    rows = 2
                    cols = 2
                    cell_height = 480
                    cell_width = 640
                    grid = np.zeros((cell_height * rows, cell_width * cols, 3), dtype=np.uint8)
                    
                    for camera_id, frame in frames.items():
                        i = camera_id // cols
                        j = camera_id % cols
                        frame_resized = cv2.resize(frame, (cell_width, cell_height))
                        grid[i*cell_height:(i+1)*cell_height, 
                             j*cell_width:(j+1)*cell_width] = frame_resized
                    
                    cv2.imshow('Security Camera Feeds', grid)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.running = False
                    break
                elif key == ord('s'):
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f'security_capture_{timestamp}.jpg', grid)
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in visualization: {e}")
                continue
    
    def stop(self):
        """Detener el sistema y limpiar recursos"""
        logger.info("Stopping Security Camera System")
        self.running = False
        cv2.destroyAllWindows()
        self.unity_socket.close()

if __name__ == "__main__":
    try:
        system = SecurityCameraSystem(
            num_cameras=4,  # Número de cámaras de seguridad
            base_port=5124  # Puerto base para la comunicación
        )
        system.start()
    except KeyboardInterrupt:
        system.stop()
        logger.info("System stopped by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        system.stop()