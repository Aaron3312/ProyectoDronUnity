# robot_controller.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
import math
import time
import socket
import json
import threading

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class Robot:
    def __init__(self):
        self.investigating = False
        self.target = None
        self.last_detection_time = None
        self.detection_cooldown = 5.0
        self.detection_socket = None
        self.running = True
        
        # Posiciones fijas de las cámaras
        self.camera_positions = [
            {'x': -2.833347, 'y': 8.0, 'z': 44.74295},
            {'x': -61.0, 'y': 10.0, 'z': 67.0},
            {'x': 52.0, 'y': 4.0, 'z': -35.0},
            {'x': 28.24, 'y': 4.0, 'z': -104.0}
        ]
        
        # Iniciar socket para recibir detecciones
        self._setup_detection_socket()

    def _setup_detection_socket(self):
        try:
            self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.detection_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.detection_socket.bind(('0.0.0.0', 5556))  # Puerto que usa SecurityCameraSystem
            
            # Iniciar thread para escuchar detecciones
            self.detection_thread = threading.Thread(target=self._listen_for_detections)
            self.detection_thread.daemon = True
            self.detection_thread.start()
            logger.info("Detection socket setup complete")
            
        except Exception as e:
            logger.error(f"Error setting up detection socket: {e}")
            raise

    def _listen_for_detections(self):
        logger.info("Started listening for detections")
        while self.running:
            try:
                data, _ = self.detection_socket.recvfrom(65536)
                detection = json.loads(data.decode())
                self.handle_detection(detection['camera_id'])
                logger.debug(f"Received detection from camera {detection['camera_id']}")
            except Exception as e:
                if self.running:
                    logger.error(f"Error processing detection: {e}")
                time.sleep(0.1)

    def handle_detection(self, camera_id):
        current_time = time.time()
        
        # Verificar cooldown
        if self.last_detection_time and (current_time - self.last_detection_time) < self.detection_cooldown:
            logger.debug(f"In cooldown period ({current_time - self.last_detection_time:.2f} < {self.detection_cooldown})")
            return
            
        # Verificar si ya está investigando
        if self.investigating:
            logger.debug("Already investigating, ignoring detection")
            return
            
        # Iniciar nueva investigación
        self.investigating = True
        self.target = self.camera_positions[camera_id]
        self.last_detection_time = current_time
        logger.info(f"Starting investigation for camera {camera_id} at position {self.target}")

    def check_investigation_complete(self, current_pos):
        if not self.investigating:
            return False
            
        distance = math.sqrt(
            (current_pos['x'] - self.target['x'])**2 +
            (current_pos['y'] - self.target['y'])**2 +
            (current_pos['z'] - self.target['z'])**2
        )
        
        if distance < 2.0:
            logger.info(f"Investigation complete - Distance: {distance:.2f}")
            self.investigating = False
            self.target = None
            return True
            
        return False

    def get_decision(self, current_pos):
        self.check_investigation_complete(current_pos)
        
        if self.investigating
            logger.debug("Moving to target")
            return {
                "decision": "move_to_target",
                "target": self.target
            }
        logger.debug("Exploring")
        return {"decision": "explore"}

    def cleanup(self):
        self.running = False
        if self.detection_socket:
            self.detection_socket.close()

# Crear instancia del robot
robot = Robot()

@app.route('/get_decisions', methods=['POST'])
def get_decisions():
    try:
        world_state = request.json
        current_pos = world_state['agentStates'][0]['state']['position']
        decision = robot.get_decision(current_pos)
        return jsonify({'decisions': [decision]})
    except Exception as e:
        logger.error(f"Error in get_decisions: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting Robot Controller")
        app.run(debug=True, port=5000)
    finally:
        robot.cleanup()