import cv2
import numpy as np
import socket
import threading
import struct
import time
import logging
from ultralytics import YOLO
import torch
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AgentVisionReceiver:
    def __init__(self, num_agents=1, base_port=5123, conf_threshold=0.5, model_type='yolov8n'):
        """
        Initialize the AgentVisionReceiver with improved YOLOv8 support
        
        Args:
            num_agents (int): Number of agents to monitor
            base_port (int): Starting port number
            conf_threshold (float): Confidence threshold for detections
            model_type (str): YOLOv8 model type ('yolov8n', 'yolov8s', 'yolov8m', 'yolov8l', 'yolov8x')
        """
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
        
    def process_frame_yolo(self, frame, agent_id):
        """
        Process a frame using YOLOv8 with improved tracking and visualization
        """
        try:
            # Run YOLOv8 inference with tracking
            results = self.model.track(frame, persist=True, conf=self.conf_threshold, 
                                     tracker="bytetrack.yaml")
            
            if results and len(results) > 0:
                result = results[0]  # Get first result
                
                # Draw boxes and labels
                annotated_frame = result.plot()
                
                # Add additional information if tracking is available
                if hasattr(result, 'boxes') and result.boxes.id is not None:
                    tracks = result.boxes.id.cpu().numpy().astype(int)
                    for i, box in enumerate(result.boxes.xyxy):
                        if i < len(tracks):
                            track_id = tracks[i]
                            # Add track ID above the box
                            x1, y1 = box[:2].cpu().numpy().astype(int)
                            cv2.putText(annotated_frame, f"ID: {track_id}", 
                                      (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                      0.5, (0, 255, 0), 2)
                
                # Add performance metrics
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
            # Increase buffer size for better performance
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
        """Start receiving and displaying streams"""
        logger.info("Starting stream reception")
        
        # Start receiver threads
        for i in range(self.num_agents):
            receiver = threading.Thread(
                target=self._receive_stream,
                args=(i,),
                name=f"Receiver-{i}"
            )
            receiver.daemon = True
            receiver.start()
        
        # Start display thread
        self._display_streams()
    
    def _display_streams(self):
        """Display all agent streams in a grid"""
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
                    
                    grid = np.zeros((cell_height * rows, cell_width * cols, 3), 
                                  dtype=np.uint8)
                    
                    for agent_id, frame in current_frames.items():
                        i = agent_id // cols
                        j = agent_id % cols
                        grid[i*cell_height:(i+1)*cell_height, 
                             j*cell_width:(j+1)*cell_width] = frame
                    
                    cv2.imshow('Agent Vision Streams', grid)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                    break
                elif key == ord('s'):  # Save current frame
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    cv2.imwrite(f'capture_{timestamp}.jpg', grid)
                
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in visualization: {e}")
                continue
    
    def stop(self):
        """Stop all threads and clean up"""
        logger.info("Stopping AgentVisionReceiver")
        self.running = False
        cv2.destroyAllWindows()

if __name__ == "__main__":
    receiver = AgentVisionReceiver(
        num_agents=1,
        model_type='yolov8n',  # Puedes cambiar a 'yolov8s', 'yolov8m', 'yolov8l' o 'yolov8x'
        conf_threshold=0.5
    )
    receiver.start_receiving()