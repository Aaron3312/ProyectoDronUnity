import socket
import threading
import logging
import signal
import sys
import time

class DroneCommandServer:
    def __init__(self, host='127.0.0.1', port=5782):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.clients = set()  # Para conexiones de Unity
        self.drone_clients = set()  # Para conexiones de DroneAgent
        self.clients_lock = threading.Lock()
        self.drone_clients_lock = threading.Lock()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(5)  # Aumentado para permitir múltiples conexiones
            self.running = True
            self.logger.info(f"Server started on {self.host}:{self.port}")
            
            self.server.settimeout(1.0)
            
            while self.running:
                try:
                    client_socket, address = self.server.accept()
                    self.logger.info(f"New connection from {address}")
                    
                    # El primer mensaje determina si es Unity o DroneAgent
                    client_socket.settimeout(5.0)  # Timeout para identificación inicial
                    try:
                        init_message = client_socket.recv(1024).decode('utf-8').strip()
                        if init_message == "DRONE_AGENT":
                            with self.drone_clients_lock:
                                self.drone_clients.add(client_socket)
                            self.logger.info("DroneAgent connected")
                            client_handler = threading.Thread(
                                target=self.handle_drone_client,
                                args=(client_socket,)
                            )
                        elif init_message == "UNITY_CLIENT":  # Añadida esta condición
                            with self.clients_lock:
                                self.clients.add(client_socket)
                            self.logger.info("Unity client connected")
                            client_handler = threading.Thread(
                                target=self.handle_unity_client,
                                args=(client_socket,)
                            )
                        else:
                            with self.clients_lock:
                                self.clients.add(client_socket)
                            self.logger.info("Unity client connected")
                            client_handler = threading.Thread(
                                target=self.handle_unity_client,
                                args=(client_socket,)
                            )
                        
                        client_handler.daemon = True
                        client_handler.start()
                    except socket.timeout:
                        self.logger.error("Client identification timeout")
                        client_socket.close()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")
                
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()

    def handle_unity_client(self, client_socket):
        """Maneja las conexiones del cliente Unity"""
        try:
            while self.running:
                try:
                    client_socket.settimeout(1.0)
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    command = data.strip().lower()
                    if command == "aterriza dron":
                        self.broadcast_to_drones("LAND")
                        self.logger.info("Landing command received from Unity and broadcasted to drones")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling Unity client: {e}")
                    break
        finally:
            with self.clients_lock:
                self.clients.remove(client_socket)
            client_socket.close()
            self.logger.info("Unity client disconnected")

    def handle_drone_client(self, client_socket):
        """Maneja las conexiones del DroneAgent"""
        try:
            while self.running:
                try:
                    client_socket.settimeout(1.0)
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    if data.startswith("HUMAN_DETECTED:"):
                        self.logger.warning("¡Alarma activada!")
                        # Aquí podrías agregar más acciones cuando se detecta una persona
                    
                    time.sleep(0.1)  # Previene uso excesivo de CPU
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling drone client: {e}")
                    break
        finally:
            with self.drone_clients_lock:
                self.drone_clients.remove(client_socket)
            client_socket.close()
            self.logger.info("Drone client disconnected")

            
    def broadcast_to_drones(self, command):
        """Envía un comando a todos los drones conectados"""
        with self.drone_clients_lock:
            disconnected_drones = set()
            for drone_socket in self.drone_clients:
                try:
                    drone_socket.send(command.encode('utf-8'))
                except:
                    disconnected_drones.add(drone_socket)
            
            # Limpia las conexiones muertas
            for drone_socket in disconnected_drones:
                self.drone_clients.remove(drone_socket)
                drone_socket.close()

    def stop(self):
        self.logger.info("Stopping server...")
        self.running = False
        
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()
            
        with self.drone_clients_lock:
            for client in self.drone_clients:
                try:
                    client.close()
                except:
                    pass
            self.drone_clients.clear()
        
        try:
            self.server.close()
        except:
            pass
        
        self.logger.info("Server stopped")

def signal_handler(signum, frame):
    print("\nSignal received. Shutting down...")
    if 'server' in globals():
        server.stop()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    server = DroneCommandServer()
    try:
        server.start()
    except Exception as e:
        server.logger.error(f"Fatal error: {e}")
        server.stop()