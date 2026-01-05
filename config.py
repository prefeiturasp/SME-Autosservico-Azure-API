import os
import logging

from dotenv import load_dotenv

# Carrega variáveis do .env antes de instanciar configurações globais.
load_dotenv()


class Settings:
    def __init__(self):
        self.azure_devops_pat = os.getenv("AZURE_DEVOPS_PAT")
        self.default_organization = os.getenv("AZURE_DEVOPS_ORGANIZATION", "")
        self.default_project = os.getenv("AZURE_DEVOPS_PROJECT", "")
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")

    def validate_required_env_vars(self):
        missing_vars = []
        if not self.azure_devops_pat:
            missing_vars.append("AZURE_DEVOPS_PAT")

        if missing_vars:
            error_msg = f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}"
            logging.error(error_msg)
            raise ValueError(error_msg)


# Instância global das configurações
settings = Settings()
