import time
from ngc_requests import *

'''Python file containing functions relevant to the path where we 
load in a nemo checkpoint and validate its successful download'''

def download_nemo_checkpoint(ti, org, ace, workspace_name, team=None):
      
      #get workspace id
      workspace_response = create_workspace(ti, org, ace, workspace_name)
      workspace_id = workspace_response['workspace']['id']
      
      #ngc job parameters
      job_name = "airflow_download_gpt3_5b_ckpt"
      ace_instance = "dgxa100.80g.1.norm"
      ace_name = ace
      docker_image = f"{org}/nemofw-training:23.05-py3"
      replica_count = 1
      workspace_mount_path = "/mount/data"
      job_command = "cd ../; cd /mount/data/; mkdir gpt_models; cd gpt_models;\
                    wget https://huggingface.co/nvidia/nemo-megatron-gpt-5B/resolve/main/nemo_gpt5B_bf16_tp2.nemo"
      
      #send ngc job request
      job_response = ngc_job_request(ti, org, job_name, ace_instance, ace_name, docker_image, \
                                     replica_count, workspace_mount_path, workspace_id, job_command, team=team)
      
      #wait for job to complete on BCP before allowing airflow to "finish" task
      final_job_status = wait_for_job_completion(ti,
                                                 org, 
                                                 job_response, 
                                                 wait_time=15, 
                                                 team=team)

      return job_response, workspace_id

 