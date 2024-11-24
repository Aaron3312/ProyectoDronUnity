from flask import Flask, request, jsonify
import socket
import json
import threading
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DroneController:
    def __init__(self):
        self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.detection_socket.bind(('0.0.0.0', 5556))
        self.detection_socket.settimeout(1.0)

        self.dronDetection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dronDetection_socket.bind(('0.0.0.0', 5557))
        self.dronDetection_socket.settimeout(1.0)
        
        self.last_detection_time = 0
        self.detection_cooldown = 3.0  # Tiempo mínimo entre respuestas a detecciones
        self.current_target = None
        self.last_target_time = 0
        self.target_timeout = 10.0  # Tiempo máximo para mantener un objetivo
        self.wait_because_see_human = False
        self.last_human_detection_time = 0  # Nuevo: tiempo de la última detección de humano
        self.human_detection_timeout = 5.0  # Nuevo: timeout para detecciones de humanos en segundos

        # Nuevo: variables para el cooldown de exploración
        self.last_explore_time = 0
        self.explore_cooldown = 10.0  # Tiempo mínimo entre comandos de exploración
        self.exploring = False  # Para rastrear si estamos en modo exploración
        
        # Posiciones de las cámaras en el mundo (ajustar según tu escena)
        self.camera_positions = {
            0: {'x': -2.833347, 'y': 2.0, 'z': 16.74295},  # Cámara 1
            1: {'x': -37.0, 'y': 4.0, 'z': 51.0},        # Cámara 2
            2: {'x': 36.0, 'y': 2.0, 'z': -35.0},        # Cámara 3
            3: {'x': 28.24, 'y': 4.0, 'z': -104.0}           # Cámara 4
        }
        
        # Iniciar thread para recibir detecciones
        self.running = True
        self.detection_thread = threading.Thread(target=self._handle_detections)
        self.detection_thread.daemon = True
        self.detection_thread.start()

        # Iniciar thread para recibir detecciones del dron
        self.dronDetection_thread = threading.Thread(target=self._handle_dron_detections)
        self.dronDetection_thread.daemon = True
        self.dronDetection_thread.start()
        
    def _handle_dron_detections(self):
        while self.running:
            try:
                data, _ = self.dronDetection_socket.recvfrom(65535) # for what is this number? 
                # is for the buffer size, the maximum amount of data to be received at once
                detection = json.loads(data.decode())
                
                current_time = time.time()
                if current_time - self.last_detection_time < self.detection_cooldown:
                    continue
                
                # detection= {
                #                     'type': 'human',
                #                     'agent_id': agent_id,
                #                     'confidence': float(confidence),
                #                     'position': {
                #                         'x': float(center_x),
                #                         'y': float(center_y)
                #                     },
                #                     'timestamp': time.time()
                #                 }

                type = detection['type']
                agent_id = detection['agent_id']
                confidence = detection['confidence']
                position = detection['position']
                
                if confidence > 0.8:
                    self.current_target = position
                    self.last_target_time = current_time
                    self.last_detection_time = current_time
                    self.exploring = False


                    if type == 'human':  # Solo actualizar tiempos para detecciones de humanos
                        self.wait_because_see_human = True
                        self.last_human_detection_time = current_time
                        logger.info(f"Nueva detección de humano en dron con confianza {confidence}")
                    else:
                        logger.info(f"Nueva detección en dron de tipo {type} con confianza {confidence}")

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error procesando detección: {e}")
                continue



    def _handle_detections(self):
        while self.running:
            try:
                data, _ = self.detection_socket.recvfrom(65535)
                detection = json.loads(data.decode())
                
                current_time = time.time()
                if current_time - self.last_detection_time < self.detection_cooldown:
                    continue
                
                camera_id = detection['camera_id']
                confidence = detection['confidence']
                
                # Solo procesar detecciones con alta confianza
                if confidence > 0.6:
                    self.current_target = self.camera_positions[camera_id]
                    self.last_target_time = current_time
                    self.last_detection_time = current_time
                    self.exploring = False  # Interrumpir exploración si hay una detección
                    self.detection_cooldown = 3.0  # Ajustar el cooldown para evitar interferencias
                    logger.info(f"Nueva detección en cámara {camera_id} con confianza {confidence}")
                
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error procesando detección: {e}")
                continue

    def get_decision(self, agent_position):
        """Determina la siguiente acción para el dron basado en el estado actual"""
        current_time = time.time()
        # Verificar si el tiempo desde la última detección de humano excede el timeout
        if self.wait_because_see_human and (current_time - self.last_human_detection_time) >= self.human_detection_timeout:
            logger.info("Timeout de detección de humano alcanzado, volviendo a operación normal")
            self.wait_because_see_human = False
        
        if self.wait_because_see_human:
            logger.info(f"Enviando stop al dron: {agent_position}")
            return {
                "decision": "move_to_target_human",
                "target": agent_position
            }
        
        logger.info(f"Posición del agente: {agent_position}")
        logger.info(f"Objetivo actual: {self.current_target}")

                # Si hay un objetivo activo y no ha expirado
        if self.current_target and (current_time - self.last_target_time) < self.target_timeout:
            self.exploring = False  # Asegurarse de que no estamos en modo exploración
            logger.info(f"Moviendo hacia objetivo {self.current_target}")
            return {
                "decision": "move_to_target",
                "target": self.current_target
            }
        
        # Si no hay objetivo o expiró, considerar exploración
        self.current_target = None
        
        # Verificar si podemos enviar un nuevo comando de exploración
        if not self.exploring or (current_time - self.last_explore_time) >= self.explore_cooldown:
            self.exploring = True
            self.last_explore_time = current_time
            logger.info("Iniciando nueva exploración")
            return {
                "decision": "explore",
                "target": None
            }
        else:
            # Si estamos en cooldown de exploración, continuar con el último comando
            logger.info("Continuando exploración actual")
            return {
                "decision": "continue",
                "target": None
            }

    def stop(self):
        """Detener el controlador"""
        self.running = False
        self.detection_socket.close()

# Instancia global del controlador
drone_controller = DroneController()

@app.route('/get_decisions', methods=['POST'])
def get_decisions():
    try:
        world_state = request.get_json()
        decisions = []
        
        # Procesar cada agente en el estado del mundo
        for agent_state in world_state['agentStates']:
            agent_pos = agent_state['state']['position']
            decision = drone_controller.get_decision(agent_pos)
            decisions.append(decision)
        
        return jsonify({"decisions": decisions})
    
    except Exception as e:
        logger.error(f"Error procesando decisión: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        drone_controller.stop()
        logger.info("Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"Error del sistema: {e}")
        drone_controller.stop()