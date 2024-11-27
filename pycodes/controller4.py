import agentpy as ap
from flask import Flask, request, jsonify
import socket
import json
import threading
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class DroneAgent(ap.Agent):
    """Individual drone agent with sensing and decision-making capabilities"""



    def setup(self):
        # Agent state variables
        self.security_socket = None
        self.connect_to_security_server()

        self.landing_commanded_executed = False
        self.position = {'x': 0, 'y': 0, 'z': 0}
        self.current_target = None
        self.last_target_time = 0
        self.target_timeout = 10.0
        self.wait_because_see_human = False
        self.last_human_detection_time = 0
        self.human_detection_timeout = 5.0
        self.exploring = False
        self.last_explore_time = 0
        self.explore_cooldown = 10.0
        self.starting = True
        
        self.landing_commanded = False

        # Detection timing
        self.last_detection_time = 0
        self.detection_cooldown = 3.0

    def connect_to_security_server(self):
        try:
            self.security_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.security_socket.connect(('127.0.0.1', 5782))
            self.security_socket.send("DRONE_AGENT".encode('utf-8'))
            logger.info("Connected to security agent server")
        except Exception as e:
            logger.error(f"Could not connect to security agent: {e}")
            self.security_socket = None

    def update_position(self, new_position):
        """Update the agent's position"""
        self.position = new_position

    def process_detection(self, detection, current_time, camera_positions=None):
        """Process incoming detection data"""
        if current_time - self.last_detection_time < self.detection_cooldown:
            return False

        if 'confidence' in detection and detection['confidence'] > 0.9 and detection.get('type') == 'human':
            # Enviar alerta al servidor de seguridad
            if self.security_socket:
                try:
                    alert_msg = f"HUMAN_DETECTED:confidence={detection['confidence']}"
                    self.security_socket.send(alert_msg.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Error sending human detection alert: {e}")
                    # Intentar reconectar si falla el envío
                    self.connect_to_security_server()

        if 'confidence' in detection and detection['confidence'] > 0.8:
            if 'camera_id' in detection and camera_positions:
                self.current_target = camera_positions[detection['camera_id']]
                logger.info(f"new detection in camera {detection['camera_id']} with confidence {detection['confidence']}")
            elif 'position' in detection:
                self.current_target = detection['position']
            self.last_target_time = current_time
            self.last_detection_time = current_time
            self.exploring = False
            
            if detection.get('type') == 'human':
                self.wait_because_see_human = True
                self.last_human_detection_time = current_time
                logger.info(f"Human detection with confidence {detection['confidence']}")
            return True
        return False

    def make_decision(self, current_time):
        """Determine next action based on current state"""
        # Check human detection timeout

        if self.starting:
            self.starting = False
            logger.info("Starting")
            return {
                "decision": "takeoff",
                "target": None
            }

        if self.landing_commanded:
            self.landing_commanded_executed = True
            self.landing_commanded = False
            logger.info("Executing landing command")
            return {
                "decision": "land",
                "target": None
            }

        if self.landing_commanded_executed:
            logger.info("Landed or so, doing nothing")
            return {
                "decision": "do_nothing_aterrizing",
                "target": None
            }



        if self.wait_because_see_human:
            if (current_time - self.last_human_detection_time) >= self.human_detection_timeout:
                logger.info("Human detection timeout reached, resuming normal operation")
                self.wait_because_see_human = False
            else:
                logger.info("Waiting because of human detection")
                return {
                    "decision": "move_to_target_human",
                    "target": self.position
                }

        # Handle active target
        if self.current_target and (current_time - self.last_target_time) < self.target_timeout:
            self.exploring = False
            logger.info(f"Moving to camera target {self.current_target}")
            return {
                "decision": "move_to_target",
                "target": self.current_target
            }

        # Handle exploration
        self.current_target = None
        if not self.exploring or (current_time - self.last_explore_time) >= self.explore_cooldown:
            self.exploring = True
            self.last_explore_time = current_time
            logger.info("Exploring")
            return {
                "decision": "explore",
                "target": None
            }
        
        logger.info("Continuing exploration")
        return {
            "decision": "continue",
            "target": None
        }

class DroneModel(ap.Model):
    """Main model coordinating the drone system"""
    
    def setup(self):
        # Environment configuration
        self.camera_positions = {
            0: {'x': -2.833347, 'y': 2.0, 'z': 16.74295},
            1: {'x': -37.0, 'y': 4.0, 'z': 51.0},
            2: {'x': 36.0, 'y': 2.0, 'z': -35.0},
            3: {'x': 28.24, 'y': 4.0, 'z': -104.0}
        }
        
        # Create agents
        n_drones = self.p.get('n_drones', 1)
        self.agents = ap.AgentList(self, n_drones, DroneAgent)
        
        # Setup communication sockets
        self.detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.detection_socket.bind(('0.0.0.0', 5556))
        self.detection_socket.settimeout(1.0)

        self.dron_detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.dron_detection_socket.bind(('0.0.0.0', 5557))
        self.dron_detection_socket.settimeout(1.0)

        # New command socket for receiving landing commands
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.command_socket.bind(('0.0.0.0', 5782))
        self.command_socket.listen(1)
        self.command_socket.settimeout(1.0)

        # Modificar la conexión al servidor de seguridad
        self.security_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.security_socket.connect(('127.0.0.1', 5782))
            # Identificarse como DroneAgent
            self.security_socket.send("DRONE_AGENT".encode('utf-8'))
            logger.info("Connected to security agent server")
        except Exception as e:
            logger.error(f"Could not connect to security agent: {e}")
            self.security_socket = None



        # Start detection threads
        self.running = True
        self.start_detection_threads()
        self.start_security_thread()


    def start_security_thread(self):
        """Start thread for receiving from security agent"""
        self.security_thread = threading.Thread(target=self._handle_security_commands)
        self.security_thread.daemon = True
        self.security_thread.start()

    def _handle_security_commands(self):
        """Handle incoming commands from security agent"""
        while self.running and self.security_socket:
            try:
                data = self.security_socket.recv(1024).decode('utf-8')
                if not data:
                    continue
                
                if data.strip() == "LAND":
                    logger.info("Received landing command from security server")
                    for agent in self.agents:
                        agent.landing_commanded = True
                
            except Exception as e:
                logger.error(f"Security command handling error: {e}")
                # Try to reconnect
                try:
                    self.security_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.security_socket.connect(('127.0.0.1', 5782))
                    # Re-identificarse como DroneAgent
                    self.security_socket.send("DRONE_AGENT".encode('utf-8'))
                    logger.info("Reconnected to security agent server")
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")
                    time.sleep(5)

    def start_detection_threads(self):
        """Initialize and start detection handling threads"""
        self.detection_thread = threading.Thread(target=self._handle_detections)
        self.detection_thread.daemon = True
        self.detection_thread.start()

        self.dron_detection_thread = threading.Thread(target=self._handle_dron_detections)
        self.dron_detection_thread.daemon = True
        self.dron_detection_thread.start()

    def _handle_detections(self):
        """Handle incoming detections from fixed cameras"""
        while self.running:
            try:
                data, _ = self.detection_socket.recvfrom(65535)
                detection = json.loads(data.decode())
                current_time = time.time()
                
                for agent in self.agents:
                    agent.process_detection(detection, current_time, self.camera_positions)
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Detection processing error: {e}")

    def _handle_dron_detections(self):
        """Handle incoming detections from drones"""
        while self.running:
            try:
                data, _ = self.dron_detection_socket.recvfrom(65535)
                detection = json.loads(data.decode())
                current_time = time.time()
                
                for agent in self.agents:
                    agent.process_detection(detection, current_time)
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Drone detection processing error: {e}")

    def step(self):
        """Model step - not used in this real-time system"""
        pass

    def end(self):
        """Clean shutdown"""
        self.running = False
        self.detection_socket.close()
        self.dron_detection_socket.close()
        if self.security_socket:
            self.security_socket.close()

# Global model instance
drone_model = DroneModel({'n_drones': 1})
drone_model.setup()

@app.route('/get_decisions', methods=['POST'])
def get_decisions():
    try:
        world_state = request.get_json()
        decisions = []
        current_time = time.time()
        
        for idx, agent_state in enumerate(world_state['agentStates']):
            if idx < len(drone_model.agents):
                agent = drone_model.agents[idx]
                agent.update_position(agent_state['state']['position'])
                decision = agent.make_decision(current_time)
                decisions.append(decision)
        
        return jsonify({"decisions": decisions})
    
    except Exception as e:
        logger.error(f"Decision processing error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        drone_model.end()
        logger.info("System stopped by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        drone_model.end()