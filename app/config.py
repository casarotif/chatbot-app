from decouple import config

class Config:
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
    # Chave padrão - substitua pela sua chave real no arquivo .env ou variável de ambiente
    # Você pode obter uma chave em: https://platform.openai.com/account/api-keys
    OPENAI_API_KEY = config('OPENAI_API_KEY', default='sk-default-key-placeholder-replace-in-env')