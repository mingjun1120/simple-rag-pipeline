import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from cerebras.cloud.sdk import Cerebras

load_dotenv()

def invoke_ai(system_message: str, user_message: str) -> str:
    """
    Generic function to invoke an AI model given a system and user message.
    Supports both Azure OpenAI and Cerebras platforms based on config.yml.
    """
    # Load configuration from config.yml
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config.yml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing configuration file: {e}")
    
    # Get configuration values
    provider = config.get('ai_platform', {}).get('provider')
    common_config = config.get('common', {})
    
    if not provider:
        raise ValueError("No provider specified in configuration")
    
    # Prepare common parameters
    temperature = common_config.get('temperature', 0.5)
    top_p = common_config.get('top_p', 1)
    seed = common_config.get('seed', 123)
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
    
    if provider == "azure_openai":
        # Azure OpenAI configuration
        azure_config = config.get('azure_openai', {})
        if not azure_config:
            raise ValueError("Azure OpenAI configuration not found")
            
        client = AzureOpenAI(
            azure_deployment=azure_config.get('azure_deployment'),
            api_version=azure_config.get('api_version'),
            api_key=os.getenv("AZURE_OPENAI_API_KEY2"),
            azure_endpoint=azure_config.get('azure_endpoint')
        )
        
        response = client.chat.completions.create(
            model=azure_config.get('model'),
            reasoning_effort=azure_config.get('reasoning_effort', 'medium'),
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            messages=messages,
        )
    elif provider == "cerebras":
        # Cerebras configuration
        cerebras_config = config.get('cerebras', {})
        if not cerebras_config:
            raise ValueError("Cerebras configuration not found")
            
        client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
        
        response = client.chat.completions.create(
            messages=messages,
            model=cerebras_config.get('model'),
            max_completion_tokens=cerebras_config.get('max_completion_tokens', 65536),
            temperature=temperature,
            top_p=top_p,
            seed=seed,
            reasoning_effort=cerebras_config.get('reasoning_effort', 'medium')
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    
    return response.choices[0].message.content
