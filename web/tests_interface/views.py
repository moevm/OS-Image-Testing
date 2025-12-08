import subprocess
import os
from django.shortcuts import render
from django.http import JsonResponse

def index(request):
    return render(request, 'tests_interface/index.html')

def yocto_page(request):
    return render(request, 'tests_interface/yocto.html')

def opensuse_page(request):
    return render(request, 'tests_interface/opensuse.html')

def run_tests(request):
    referer = request.META.get('HTTP_REFERER', '')

    if 'yocto' in referer:
        env_req = {'SSH_USER': 'root', 'SSH_PASS': '', 'SSH_ADDR': '10.5.0.10'}
    else:
        env_req = {'SSH_USER': 'suser', 'SSH_PASS': 'password', 'SSH_ADDR': '10.5.0.12'}

    env_vars = os.environ.copy()
    env_vars.update(env_req)

    try:
        result = subprocess.run(
            'python3 /home/user/image/runner.py',
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
            env=env_vars
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n\nErrors:\n{result.stderr}"
            
        return JsonResponse({
            'success': True,
            'output': output,
            'exit_code': result.returncode
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
