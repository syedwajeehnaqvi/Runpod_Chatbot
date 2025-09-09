from django.shortcuts import render
import uuid
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
import time
import re

global JOB_ID

def chatbot_view(request):
    return render(request, 'chatbot.html')

def chatbot(request):
    session_id = str(uuid.uuid4())  # Unique WebSocket connection per user
    ws_url = "ws://YOUR_PUBLIC_IP:8765"  # Replace with actual RunPod IP/port or fetch dynamically

    return render(request, "chat/chatbot.html", {
        "session_id": session_id,
        "ws_url": ws_url
    })

@csrf_exempt
def runpod_proxy(request):
    global JOB_ID 
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    data = json.loads(request.body)
    prompt = data.get('prompt', '')

    api_url = 'https://api.runpod.ai/v2/9m4r1uykcytq3g/run'
    api_key = os.getenv('RUNPOD_API_KEY')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    payload = {
        'input': {
            'prompt': prompt
        }
    }

    # Step 1: Start the job
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code != 200:
        return JsonResponse({'error': 'Failed to start job', 'details': response.text}, status=response.status_code)

    response_data = response.json()

    job_id = response_data.get('id') or response_data.get('jobId')
    if not job_id:
        return JsonResponse({'error': 'Job ID not found in response', 'response': response_data}, status=500)

    JOB_ID = job_id

    status_url = f'https://api.runpod.ai/v2/9m4r1uykcytq3g/status/{job_id}'

    max_wait_seconds = 30  # Increase timeout if needed
    poll_interval = 5
    waited = 0

    while waited < max_wait_seconds:
        status_response = requests.get(status_url, headers=headers)

        if status_response.status_code != 200:
            return JsonResponse({'error': 'Failed to get status', 'details': status_response.text}, status=status_response.status_code)

        status_response_data = status_response.json()

        job_status = status_response_data.get('status', '').lower()
        raw_output = status_response_data.get('output', '')

        # Try to parse IP and port from the output string
        match = re.search(r'Public IP: ([\d.]+), TCP Port: (\d+)', raw_output)

        if match:
            public_ip = match.group(1)
            tcp_port = int(match.group(2))

            # Return immediately if IP and port found, along with current job status
            return JsonResponse({
                'public_ip': public_ip,
                'tcp_port': tcp_port,
                'status': job_status,
                'message': 'Server info retrieved',
                'raw_output': raw_output
            })

        # If no IP/port found, wait and poll again
        time.sleep(poll_interval)
        waited += poll_interval

    # If timeout and no IP/port, return error
    return JsonResponse({'error': 'Timeout waiting for server to provide IP and port'}, status=504)

@csrf_exempt
def cancel_runpod_job(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        data = json.loads(request.body)
        job_id = JOB_ID
        if not job_id:
            return JsonResponse({'error': 'Missing job_id'}, status=400)

        api_key = os.getenv('RUNPOD_API_KEY')
        cancel_url = f'https://api.runpod.ai/v2/9m4r1uykcytq3g/cancel/{job_id}'

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        response = requests.post(cancel_url, headers=headers)

        if response.status_code == 200:
            return JsonResponse({'message': 'Job canceled successfully'})
        else:
            return JsonResponse({
                'error': 'Failed to cancel job',
                'status': response.status_code,
                'details': response.text
            }, status=response.status_code)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)