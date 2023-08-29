'''File with branching functions for NeMo Airflow DAG'''

def get_base_model(ti, pretrain_decision):
    if pretrain_decision == "False":
        return 'download_nemo_checkpoint'
    else:
        return 'download_pile_dataset'
    
def choose_tuning_method(ti, method):
    if method == 'p_tuning':
        return 'p_tuning_train'
    elif method == 'lora':
        return 'LoRA_train'
    elif method == 'sft':
        return 'SFT_train'
    
def choose_inference_lora(ti, interactive):
    if interactive:
        return 'merge_lora_adapter_weights'
    else:
        return 'LoRA_inference_script'

def choose_inference_ptuning(ti, interactive):
    if interactive:
        return 'create_triton_model_repository'
    else:
        return 'p_tuning_inference_script'

def choose_inference_sft(ti, interactive):
    if interactive:
        return 'create_triton_model_repository'
    else:
        return 'SFT_inference_script'
    

def choose_inference(ti, interactive, method):
    interactive = bool(interactive) #convert string to bool
    if method == 'lora':
        if interactive:
            return 'merge_lora_adapter_weights'
        else:
            return 'inference_scripts.LoRA_inference_script'
    elif method == 'p_tuning':
        if interactive:
            return 'create_triton_model_repository'
        else:
            return 'inference_scripts.p_tuning_inference_script'
    elif method == 'sft':
        if interactive:
            return 'create_triton_model_repository'
        else:
            return 'inference_scripts.SFT_inference_script'
