import os, json, base64, requests, time
from datetime import datetime
from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.operators.python import BranchPythonOperator
from airflow.models import Variable
from airflow.utils.trigger_rule import TriggerRule

from ngc_requests import *

## 0. Variables
key_v = Variable.get("key_v", deserialize_json=True)
org_v = Variable.get("org_v", deserialize_json=True)
team_v = Variable.get("team_v", deserialize_json=True)
ace_v = Variable.get("ace_v", deserialize_json=True)
workspace_name_v = Variable.get("workspace_name_v", deserialize_json=True)
nemo_ckpt_v = Variable.get("nemo_ckpt_v", deserialize_json=True)
pretrain_decision_v = Variable.get("pretrain_decision_v", deserialize_json=True)

key_= str(key_v)
org_=str(org_v)
team_= str(team_v)
ace_=str(ace_v)
workspace_name_ = str(workspace_name_v)
nemo_ckpt_=str(nemo_ckpt_v)
pretrain_decision_ = str(pretrain_decision_v)

def bcp_job_launch(ti, org, ace, team=None):
      
      #get workspace id
      workspace_id = 'BZQLetfySFuBjdIHee6fLg' #anotha-airflow-wksp
      
      #ngc job parameters
      job_name = "airflow_job_status_debug"
      ace_instance = "dgxa100.80g.4.norm"
      ace_name = ace
      docker_image = f"{org}/nemofw-training:23.05-py3"
      replica_count = 1
      workspace_mount_path = "/mount/workspace"
      job_command = "jupyter lab --ip=0.0.0.0 --allow-root --no-browser --NotebookApp.token='' --notebook-dir=/ --NotebookApp.allow_origin='*'" 
      
      #send ngc job request
      job_response = ngc_job_request(ti, org, job_name, ace_instance, ace_name, docker_image, \
                                     replica_count, workspace_mount_path, workspace_id, job_command, team=team)
      job_id = job_response['job']['id']

      return job_response, job_id


def wait_for_job_completion(ti, org, team=None):

     _, job_id = ti.xcom_pull(task_ids='bcp_job_launch')
     job_status = ngc_job_status(ti, org, job_id)

     min=0

     while job_status != 'FINISHED_SUCCESS' and job_status != 'FAILED' and job_status != 'KILLED_BY_USER':
         time.sleep(60) #increase wait time to 5 mins
         min += 1
         job_status = ngc_job_status(ti, org, job_id)
         print(f'minute: {min} | Job status: ', job_status)
     return job_status


## Define DAG + Tasks
with DAG(
         "BCP_DEBUG_JOB_STATUS", 
         schedule_interval='@once',
         start_date=datetime(2022, 1, 1),
         catchup=False
    ) as dag:

    token_task = PythonOperator(
            task_id = 'token',
            python_callable=get_token,
            op_kwargs={"key": key_, "org": org_ , "team": team_},
            dag = dag
    ) 

    bcp_job_launch_task = PythonOperator(
            task_id = 'bcp_job_launch',
            python_callable= bcp_job_launch,
            op_kwargs= {"org":org_, "ace": ace_, "team": team_},
            trigger_rule=TriggerRule.ONE_SUCCESS,
            dag = dag)
    
    wait_task = PythonOperator(
            task_id = 'wait_for_job_completion',
            python_callable= wait_for_job_completion,
            op_kwargs= {"org":org_, "team": team_},
            dag = dag)

token_task >> bcp_job_launch_task >> wait_task