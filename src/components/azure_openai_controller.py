import os
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from openai import get_bearer_token_provider

# This module provides a simple interface for accessing Azure OpenAI (nano-model LLM)
# Update environment variables or pass them directly as needed


class AzureOpenAIController:
    def __init__(self, deployment_name=None):
        # Use DefaultAzureCredential for authentication
        self.default_credential = DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_developer_cli_credential=True,
            exclude_workload_identity_credential=True,
            exclude_managed_identity_credential=True,
            exclude_visual_studio_code_credential=True,
            exclude_shared_token_cache_credential=True,
            exclude_interactive_browser_credential=True,
        )
        self.azure_endpoint = "https://oai02-aiserv.openai.azure.com/"
        self.api_version = "2024-10-21"
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not self.deployment_name:
            raise ValueError("Azure OpenAI deployment name missing.")
        self.token_provider = get_bearer_token_provider(
            self.default_credential, "https://cognitiveservices.azure.com/.default"
        )
        self.client = AzureOpenAI(
            azure_endpoint=self.azure_endpoint,
            azure_ad_token_provider=self.token_provider,
            api_version=self.api_version,
        )

    def call_nano_model(self, prompt, max_tokens=1000, temperature=0.2, **kwargs):
        # Calls the nano-model LLM deployment with the given prompt
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content
