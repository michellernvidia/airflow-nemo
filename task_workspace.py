from ngc_requests import *


def create_task_workspace(ti, ngc_api_key, org, ace, workspace_name):
    #check if workspace exists already
    print('checking if wksp exists...')
    workspace_response=get_existing_workspace(ti, ngc_api_key, org, workspace_name)
    
    #if not, create new one
    if workspace_response["requestStatus"]["statusCode"] == 'NOT_FOUND':
        print('workspace does not exist', workspace_name)
        workspace_response = create_workspace(ti, ngc_api_key, org, ace, workspace_name)
    else:
        print('workspace exists already.. getting id..')
    
    workspace_id = workspace_response['workspace']['id']
    return workspace_id