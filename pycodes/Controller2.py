import agentpy as ap
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import logging
import math
import socket
import json
import threading
import time

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class RobotAgent(ap.Agent):
    def setup(self):
        self.id = 0
        self.start_time = datetime.now()
        self.total_distance_traveled = 0
        self.last_position = None
        self.last_movement_time = None
        self.MIN_MOVEMENT_THRESHOLD = 1
        self.current_action = None
        self.target_position = None
        self._investigating = False
        self._investigation_complete = False
        self._detected_person = None
        self._last_detection_time = None
        self.detection_cooldown = 5.0
        self.camera_positions = [
            {'x': -2.833347, 'y': 8.0, 'z': 44.74295},
            {'x': -61.0, 'y': 10.0, 'z': 67.0},
            {'x': 52.0, 'y': 4.0, 'z': -35.0},
            {'x': 28.24, 'y': 4.0, 'z': -104.0}
        ]
        logger.debug(f"Drone initialized with id: {self.id}")

    @property
    def investigating(self):
        return self._investigating

    @investigating.setter
    def investigating(self, value):
        self._investigating = value
        logger.debug(f"Setting investigating to: {value}")

    def handle_person_detection(self, detection_data):
        current_time = time.time()
        
        # Log current state for debugging
        logger.debug(f"Current state before processing detection:")
        logger.debug(f"investigating: {self.investigating}")
        logger.debug(f"last_detection_time: {self._last_detection_time}")
        logger.debug(f"detected_person: {self._detected_person}")
        
        # Check cooldown period
        if self._last_detection_time:
            time_since_last = current_time - self._last_detection_time
            logger.debug(f"Time since last detection: {time_since_last:.2f} seconds")
            if time_since_last < self.detection_cooldown:
                logger.debug(f"In cooldown period ({time_since_last:.2f} < {self.detection_cooldown})")
                return
        
        # Check if we're already investigating
        if self.investigating:
            if not self._investigation_complete:
                logger.debug("Currently investigating, cannot start new investigation")
                return
            else:
                logger.debug("Previous investigation complete, can start new one")
        
        # Process new detection
        camera_id = detection_data['camera_id']
        logger.info(f"Starting new investigation for camera {camera_id}")
        
        self._detected_person = {
            'camera_id': camera_id,
            'position': self.camera_positions[camera_id],
            'detection_time': current_time
        }
        self._investigating = True
        self._investigation_complete = False
        self._last_detection_time = current_time
        
        logger.debug("Detection processed - New state:")
        logger.debug(f"investigating: {self._investigating}")
        logger.debug(f"detected_person: {self._detected_person}")

    def calculate_distance(self, pos1, pos2):
        distance = math.sqrt(
            (pos1['x'] - pos2['x'])**2 +
            (pos1['y'] - pos2['y'])**2 +
            (pos1['z'] - pos2['z'])**2
        )
        calculated_distance = distance if distance >= self.MIN_MOVEMENT_THRESHOLD else 0
        return calculated_distance


    def step(self, current_state):
        position = current_state['position']
        current_time = current_state.get('time', time.time())
        self.update_metrics(position, current_time)

        logger.debug(f"Step - Current state:")
        logger.debug(f"Position: {position}")
        logger.debug(f"Investigating: {self._investigating}")
        logger.debug(f"Investigation complete: {self._investigation_complete}")
        logger.debug(f"Detected person: {self._detected_person}")
        
        if self._investigating and self._detected_person:
            if self.check_investigation_complete(position):
                logger.info("Investigation complete, resuming exploration")
                return {"decision": "explore"}
            
            camera_pos = self._detected_person['position']
            logger.debug(f"Moving to investigation target: {camera_pos}")
            return {
                "decision": "move_to_target",
                "target": camera_pos
            }
        
        return {"decision": "explore"}

    def check_investigation_complete(self, current_position):
        if not self._detected_person:
            return False
            
        target_pos = self._detected_person['position']
        distance = self.calculate_distance(current_position, target_pos)
        
        logger.debug(f"Checking investigation completion - Distance to target: {distance:.2f}")
        
        if distance < 2.0:
            logger.info(f"Investigation complete - Distance to target: {distance:.2f}")
            self._investigating = False
            self._investigation_complete = True
            self._detected_person = None
            return True
            
        return False

    def update_metrics(self, current_position, current_time):
        if self.last_position and self.last_movement_time:
            if isinstance(current_time, datetime):
                time_diff = (current_time - self.last_movement_time).total_seconds()
            else:
                time_diff = current_time - self.last_movement_time
            
            if time_diff >= 0.1:
                distance = self.calculate_distance(current_position, self.last_position)
                if distance > 0:
                    self.total_distance_traveled += distance
                self.last_movement_time = current_time
        else:
            self.last_movement_time = current_time

        self.last_position = current_position.copy()


class RobotWorld(ap.Model):
    def setup(self):
        self.agents = ap.AgentList(self, self.p.num_robots, RobotAgent)
        self.detection_thread = None
        self.detection_socket = None
        self.running = True
        self._setup_detection_socket()
        logger.info(f"Created model with {self.p.num_robots} agents")

    def _setup_detection_socket(self):
        try:
            if self.detection_socket:
                self.detection_socket.close()
            
            self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Permitir la reutilización del socket
            self.detection_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Intentar vincular el socket varias veces
            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                try:
                    self.detection_socket.bind(('0.0.0.0', 5556))
                    logger.info("Successfully bound detection socket")
                    break
                except OSError as e:
                    attempt += 1
                    if attempt == max_attempts:
                        raise e
                    logger.warning(f"Socket binding attempt {attempt} failed, retrying...")
                    time.sleep(1)
            
            if not self.detection_thread or not self.detection_thread.is_alive():
                self.detection_thread = threading.Thread(target=self._listen_for_detections)
                self.detection_thread.daemon = True
                self.detection_thread.start()
                
        except Exception as e:
            logger.error(f"Error setting up detection socket: {e}")
            raise

    def _listen_for_detections(self):
        logger.info("Starting detection listener thread")
        while self.running:
            try:
                data, _ = self.detection_socket.recvfrom(65536)
                detection = json.loads(data.decode())
                # logger.info(f"Received detection: {detection}")
                for agent in self.agents:
                    agent.handle_person_detection(detection)
            except Exception as e:
                if self.running:  # Solo logear errores si aún estamos ejecutando
                    logger.error(f"Error processing detection: {e}")
                    time.sleep(0.1)

    def get_decisions(self, world_state):
        logger.debug(f"Getting decisions for world state: {world_state}")
        decisions = []
        agent_states = {entry['id']: entry['state'] for entry in world_state['agentStates']}
        
        for agent in self.agents:
            if str(agent.id) in agent_states:
                agent_state = agent_states[str(agent.id)]
                decision = agent.step(agent_state)
                decisions.append(decision)
                logger.debug(f"Decision for agent {agent.id}: {decision}")
        
        return decisions

    def get_metrics(self, world_state):
        metrics = []
        agent_states = {entry['id']: entry['state'] for entry in world_state['agentStates']}
        for agent in self.agents:
            if str(agent.id) in agent_states:
                agent_state = agent_states[str(agent.id)]
                agent.update_metrics(agent_state['position'], agent_state.get('time', 0))
                metrics.append({
                    'agent_id': agent.id,
                    'total_distance': round(agent.total_distance_traveled, 2)
                })
        return metrics

    def cleanup(self):
        self.running = False
        if self.detection_socket:
            try:
                self.detection_socket.close()
            except:
                pass

model = RobotWorld({'num_robots': 1})
model.sim_setup()

@app.route('/get_decisions', methods=['POST'])
def get_decisions():
    try:
        world_state = request.json
        decisions = model.get_decisions(world_state)
        return jsonify({'decisions': decisions})
    except Exception as e:
        logger.error(f"Error processing decisions request: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_metrics', methods=['POST'])
def get_metrics():
    try:
        world_state = request.json
        metrics = model.get_metrics(world_state)
        return jsonify({'metrics': metrics})
    except Exception as e:
        logger.error(f"Error processing metrics request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application")
        app.run(debug=True)
    finally:
        model.cleanup()