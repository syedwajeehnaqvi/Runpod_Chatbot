from websocket_server import WebsocketServer
import runpod
import os
import requests

shutdown_flag = False  # Flag to track when to stop the server
from dotenv import load_dotenv
load_dotenv()

def call_groq_llm(message, model="groq/compound"):
    """Send a message to the Groq compound model and return the response."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.RequestException as e:
        print(f"[Groq API Error] {e}")
        return "Error: Could not get response from Groq LLM."
    
def on_new_client(client, server):
    """Handle new client connection."""
    print(f"New client connected: {client['id']}")

def on_message(client, server, message):
    """Handle incoming messages from clients."""
    global shutdown_flag

    # print(f"Received: {message}")
    # server.send_message(client, f"Echo: {message}")

    print(f"Received from client {client['id']}: {message}")
    
    # If the client sends "shutdown", set flag and close server
    if message.strip().lower() == "shutdown":
        print("Shutdown command received. Stopping WebSocket server...")
        shutdown_flag = True
        server.shutdown()  # Gracefully stop the WebSocket server
        return

    # Get LLM response
    response = call_groq_llm(message)
    server.send_message(client, response)

def on_client_left(client, server):
    """Handle client disconnection."""
    print(f"Client {client['id']} disconnected")

def start_websocket():
    """Start WebSocket server and wait for shutdown."""
    global shutdown_flag

    server = WebsocketServer(host="0.0.0.0", port=8765)
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)

    print("WebSocket server started on port 8765...")

    try:
        while not shutdown_flag:  # Keep running until shutdown is triggered
            server.run_forever()  # Blocking call, but allows shutdown handling
    except KeyboardInterrupt:
        print("WebSocket server manually stopped.")
    finally:
        print("WebSocket server has been shut down.")

    return "WebSocket server stopped successfully"  # Return handler response

def handler(event):
    """RunPod job handler that runs the WebSocket server and waits for shutdown."""

    public_ip = os.getenv('RUNPOD_PUBLIC_IP', 'localhost')  
    tcp_port = int(os.getenv('RUNPOD_TCP_PORT_8765', '8765')) 
    
    print(f"Public IP: {public_ip}")  
    print(f"TCP Port: {tcp_port}")  

    runpod.serverless.progress_update(event, f"Public IP: {public_ip}, TCP Port: {tcp_port}")

    # Start WebSocket server and wait for shutdown message
    result = start_websocket()

    return {
        "message": result,
        "public_ip": public_ip,
        "tcp_port": tcp_port
    }

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})