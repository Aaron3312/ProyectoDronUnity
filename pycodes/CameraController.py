import cv2
import numpy as np
import socket
import threading
import struct
import time
import logging
import json
from ultralytics import YOLO
import torch
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AgentVisionReceiver:
    def __init__(self, num_agents=1, base_port=5123, conf_threshold=0.5, model_type='yolov8n'):
        self.num_agents = num_agents
        self.base_port = base_port
        self.running = True
        self.frame_buffer = {}
        self.lock = threading.Lock()
        self.conf_threshold = conf_threshold
        
        # Load YOLOv8 model
        logger.info(f"Loading {model_type} model...")
        try:
            self.model = YOLO(f'{model_type}.pt')
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
            
        # Initialize tracking dictionary
        self.trackers = {}
        
        # Add socket for human detections
        self.human_detection_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.controller_address = ('localhost', 5557)
        
    def process_frame_yolo(self, frame, agent_id):
        try:
            results = self.model.track(frame, persist=True, conf=self.conf_threshold, tracker="bytetrack.yaml")
            
            if results and len(results) > 0:
                result = results[0]
                annotated_frame = result.plot()
                
                # Process human detections
                if hasattr(result, 'boxes'):
                    for i, (box, cls) in enumerate(zip(result.boxes.xyxy, result.boxes.cls)):
                        if int(cls) == 0:  # Person class
                            confidence = float(result.boxes.conf[i])
                            if confidence >= self.conf_threshold:
                                x1, y1, x2, y2 = box.cpu().numpy()
                                center_x = (x1 + x2) / 2 / frame.shape[1]
                                center_y = (y1 + y2) / 2 / frame.shape[0]
                                
                                detection_data = {
                                    'type': 'human',
                                    'agent_id': agent_id,
                                    'confidence': float(confidence),
                                    'position': {
                                        'x': float(center_x),
                                        'y': float(center_y)
                                    },
                                    'timestamp': time.time()
                                }
                                
                                try:
                                    self.human_detection_socket.sendto(
                                        json.dumps(detection_data).encode(),
                                        self.controller_address
                                    )
                                    logger.info(f"Human detection sent for dron {agent_id}")
                                except Exception as e:
                                    logger.error(f"Error sending human detection: {e}")
                
                if hasattr(result, 'boxes') and result.boxes.id is not None:
                    tracks = result.boxes.id.cpu().numpy().astype(int)
                    for i, box in enumerate(result.boxes.xyxy):
                        if i < len(tracks):
                            track_id = tracks[i]
                            x1, y1 = box[:2].cpu().numpy().astype(int)
                            cv2.putText(annotated_frame, f"ID: {track_id}", 
                                      (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.5, (0, 255, 0), 2)
                
                fps = 1000 / (results[0].speed['inference'] + results[0].speed['preprocess'])
                cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                return annotated_frame
            
            return frame
            
        except Exception as e:
            logger.error(f"Error in YOLO process: {e}")
            return frame
    
    def _receive_stream(self, agent_id):
        port = self.base_port + agent_id
        logger.info(f"Starting reception on port {port} for agent {agent_id}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.settimeout(1.0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        except Exception as e:
            logger.error(f"Error setting up socket for agent {agent_id}: {e}")
            return
            
        while self.running:
            try:
                data, addr = sock.recvfrom(65535)
                logger.debug(f"Data received from {addr} for agent {agent_id}")
                
                if len(data) < 4:
                    continue
                
                received_agent_id = struct.unpack('i', data[:4])[0]
                if received_agent_id != agent_id:
                    continue
                
                img_data = data[4:]
                nparr = np.frombuffer(img_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    frame = np.ones((240, 320, 3), dtype=np.uint8) * 128
                    cv2.putText(frame, f"Dron {agent_id} - No Data", (10, 120),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                else:
                    frame = cv2.resize(frame, (320, 240))
                    frame = self.process_frame_yolo(frame, agent_id)
                
                with self.lock:
                    self.frame_buffer[agent_id] = frame.copy()
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in reception for agent {agent_id}: {e}")
                continue
    
    def start_receiving(self):
        logger.info("Starting stream reception")
        
        for i in range(self.num_agents):
            receiver = threading.Thread(
                target=self._receive_stream,
                args=(i,),
                name=f"Receiver-{i}"
            )
            receiver.daemon = True
            receiver.start()
        
        self._display_streams()
    
    def _display_streams(self):
        logger.info("Starting visualization")
        cv2.namedWindow('Agent Vision Streams', cv2.WINDOW_NORMAL)
        
        while self.running:
            try:
                with self.lock:
                    current_frames = self.frame_buffer.copy()
                
                if current_frames:
                    rows = (self.num_agents + 2) // 3
                    cols = min(3, self.num_agents)
                    cell_height = 240
                    cell_width = 320
                    
                    grid = np.zeros((cell_height * rows, cell_width * cols, 3), dtype=np.uint8)
                    
                    for agent_id, frame in current_frames.items():
                        i = agent_id // cols
                        j = agent_id % cols
                        grid[i*cell_height:(i+1)*cell_height, j*cell_width:(j+1)*cell_width] = frame
                    
                    cv2.imshow('Agent Vision Streams', grid)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                    break
                elif key == ord('s'):
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f'capture_{timestamp}.jpg', grid)
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in visualization: {e}")
                continue
    
    def stop(self):
        logger.info("Stopping AgentVisionReceiver")
        self.running = False
        self.human_detection_socket.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    receiver = AgentVisionReceiver(
        num_agents=1,
        model_type='yolov8n',
        conf_threshold=0.5
    )
    receiver.start_receiving()