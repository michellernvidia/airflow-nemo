import json, base64, requests, time


def get_token(ngc_api_key, org=None, team=None):
    '''Uses NGC API key to generate auth token'''
    scope_list = []
    scope = f'group/ngc:{org}'
    scope_list.append(scope)
    if team:
        team_scope = f'group/ngc:{org}/{team}'
        scope_list.append(team_scope)

    querystring = {
        "service": "ngc", 
        "scope": scope_list
    }

    auth = '$oauthtoken:{0}'.format(ngc_api_key)
    auth = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
    }
    url = 'https://authn.nvidia.com/token'
    response = requests.request("GET", url, headers=headers, params=querystring)
    if response.status_code != 200:
        raise Exception("HTTP Error %d: from %s" % (response.status_code, url))
    return json.loads(response.text.encode('utf8'))["token"]


def create_workspace(ti, ngc_api_key, org, ace, workspace_name):
    '''Create a workspace in a given NGC org for the authenticated user'''
    
    token = get_token(ngc_api_key, org)
    
    url = f'https://api.ngc.nvidia.com/v2/org/{org}/workspaces/'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    data = {
        'aceName': f'{ace}',
        'name': workspace_name
    }
    
    response = requests.request("POST", url, headers=headers, data=json.dumps(data))
    print(f'Workspace response: {response}')

    if response.status_code != 200:
        raise Exception("HTTP Error %d: from '%s'" % (response.status_code, url))
    return response.json()


def get_existing_workspace(ti, ngc_api_key, org, workspace_name):
    '''Gets the details of an NGC workspace. Useful for extracting the workspace ID and launching jobs downstream.'''

    token = get_token(ngc_api_key, org)

    url = f'https://api.ngc.nvidia.com/v2/org/{org}/workspaces/{workspace_name}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers)

    #ok if status code is 404. We use this later on to decide if we should create a new wksp
    if response.status_code != 200 and response.status_code != 404:
        raise Exception("HTTP Error %d: from '%s'" % (response.status_code, url))
    return response.json()


def get_workspace_contents(ngc_api_key, org, workspace_id, page_size=800):
    '''Get all files in a workspace's directory from NGC. Limited up to *page_size* files.'''

    token = get_token(ngc_api_key, org)
    url = f'https://api.ngc.nvidia.com/v2/org/{org}/workspaces/{workspace_id}/listFiles'
    params={
        'flat-dir': True, 
        'page-size': page_size
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    response = requests.request("GET", url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception("HTTP Error %d: from '%s'" % (response.status_code, url))
    return response.json()


def find_file_in_workspace(ngc_api_key, org, workspace_id, filename):
    '''Goes through all contents in an NGC workspace to search for the file specified in filename parameter'''

    contents=get_workspace_contents(ngc_api_key, org, workspace_id)['storageObjects']
    for workspace_item in contents:
        if workspace_item['name'] == filename:
            print(f"Found {filename} already existing in workspace.")
            return True
    return False #file does not exist in workspace


def ngc_job_request(ti, ngc_api_key, org, job_name, ace_instance, ace_name, docker_image, replica_count, workspaces, \
                    job_command, team=None, multinode=False, array_type=None, total_runtime=None, ports=None):
    
    '''Creates an NGC job request via API'''

    #authentication 
    token = get_token(ngc_api_key, org, team)
    if team:
        url = f'https://api.ngc.nvidia.com/v2/org/{org}/team/{team}/jobs/'
    else:
        url = f'https://api.ngc.nvidia.com/v2/org/{org}/jobs/'

    headers = {
        'Content-Type': 'application/json', 
        'Authorization': f'Bearer {token}'
    }

    #create workspace mounts for all workspaces
    workspace_mounts = []
    for workspace in workspaces:
        workspace_mounts.append(
            {
                "containerMountPoint": workspace['mount'], 
                "id": workspace['id'], 
                "mountMode": "RW"
            }
        )

    #ngc job setup
    data = {
        "name": job_name,
        "aceInstance": ace_instance,
        "aceName": ace_name,
        "dockerImageName": docker_image,
        "jobOrder": 50,
        "jobPriority": "NORMAL",
        "replicaCount": replica_count,
        "reservedLabels": [],
        "resultContainerMountPoint": "/results",
        "runPolicy": {
            "preemptClass": "RUNONCE"
        },
        "systemLabels": [],
        "userLabels": [],
        "userSecretsSpec": [],
        "workspaceMounts": workspace_mounts,
        "command": job_command,
        "portMappings": ports
    }
        
    if multinode:
        data["arrayType"] = array_type
        data["totalRuntime"] = total_runtime
    
    response = requests.request("POST", url, headers=headers, data=json.dumps(data))
    if response.status_code != 200:
        raise Exception("HTTP Error %d: from '%s'" % (response.status_code, url))
    return response.json()


def ngc_job_status(ti, ngc_api_key, org, job_id):
    '''Gets status of NGC Job (e.g., SUCCESS, FAILED, CREATED, etc.)'''
    
    #get a new token each time to make sure the token doesn't expire 
    #since we have to get NGC job status continously
    token = get_token(ngc_api_key, org)

    url = f'https://api.ngc.nvidia.com/v2/org/{org}/jobs/{job_id}'
    headers = {
        'Content-Type': 'application/json', 
        'Authorization': f'Bearer {token}'
    }
    response = requests.request("GET", url, headers=headers)
    if response.status_code != 200:
        raise Exception("HTTP Error %d: from '%s'" % (response.status_code, url))
    
    job_info = response.json()
    return job_info['job']['jobStatus']['status']


def wait_for_job_completion(ti, ngc_api_key, org, job_response, wait_time, team=None):
    '''Continually gets NGC job status every `wait_time` seconds until 
    the job finishes, is killed, or fails'''
    
    job_id = job_response['job']['id']
    job_status = ngc_job_status(ti, ngc_api_key, org, job_id)
    
    while job_status != 'FINISHED_SUCCESS' and job_status != 'FAILED' and job_status != 'KILLED_BY_USER':
        time.sleep(wait_time)
        job_status=ngc_job_status(ti, ngc_api_key, org, job_id)
        print(f'Job status: ', job_status)
    
    return job_status
