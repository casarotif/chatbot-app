from openai import OpenAI
from openai import AuthenticationError, APIError, RateLimitError
from flask import current_app
from decouple import config
from typing import List, Dict
import re

# Cliente OpenAI será inicializado dinamicamente
client = None

def is_valid_api_key(key):
    """Valida se a API key não é um valor de exemplo ou placeholder"""
    if not key or not key.strip():
        return False
    
    key_lower = key.lower().strip()
    
    # Detecta a chave padrão/placeholder configurada
    if 'sk-default-key-placeholder-replace-in-env' in key_lower or 'placeholder' in key_lower:
        return False
    
    # Detecta valores de exemplo comuns
    invalid_patterns = [
        r'sua-.*-aqui',
        r'your-.*-here',
        r'sua-.*-api-key',
        r'exemplo',
        r'example',
        r'xxx',
        r'your_api_key',
        r'api_key_here'
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, key_lower):
            return False
    
    # OpenAI API keys geralmente começam com 'sk-' e têm pelo menos 20 caracteres
    if key.startswith('sk-') and len(key) >= 20:
        return True
    # Aceitamos outras chaves também (pode ser de outras APIs OpenAI-compatible)
    return len(key) >= 10

def get_openai_client():
    """
    Obtém ou inicializa o cliente OpenAI usando a configuração centralizada do Flask.
    Retorna None se a API key não estiver configurada ou for inválida.
    """
    global client
    
    # Se o cliente já foi criado, retorna ele
    if client is not None:
        return client
    
    # Obtém a API key da configuração centralizada do Flask
    try:
        api_key = current_app.config.get('OPENAI_API_KEY', '')
    except RuntimeError:
        # Se não estiver em contexto de aplicação, tenta usar decouple diretamente
        api_key = config('OPENAI_API_KEY', default='')
    
    # Verifica se a API key é válida antes de criar o cliente
    if api_key and is_valid_api_key(api_key):
        client = OpenAI(api_key=api_key)
        return client
    else:
        client = None
        return None

class ChatbotPersonality:
    def __init__(self):
        self.system_prompt = """
        Você é um assistente sábio e amigável, inspirado no Professor Dumbledore.
        Suas características principais são:
        - Sábio e gentil, mas com um toque de humor
        - Oferece respostas profundas de forma acessível
        - Ocasionalmente faz referências metafóricas
        - Mantém um tom acolhedor e paciente
        - Incentiva a reflexão e o crescimento pessoal
        
        Diretrizes de resposta:
        1. Mantenha um tom consistente e amigável
        2. Use analogias quando apropriado
        3. Evite respostas muito longas
        4. Sempre mantenha a ética e a empatia
        """

    def get_conversation_context(self, conversation_history: List[Dict] = None) -> List[Dict]:
        """
        Prepara o contexto da conversa incluindo o histórico quando disponível
        """
        context = [{"role": "system", "content": self.system_prompt}]
        if conversation_history:
            context.extend(conversation_history)
        return context

class ResponseGenerator:
    def __init__(self):
        self.personality = ChatbotPersonality()
        self.conversation_history = []
        self.max_history = 5  # Mantém as últimas 5 interações

    def generate_response(self, user_message: str) -> str:
        """
        Gera uma resposta contextualizada baseada no histórico da conversa.
        Usa a configuração centralizada do Flask para obter a API key.
        """
        # Obtém o cliente OpenAI usando a configuração centralizada
        openai_client = get_openai_client()
        
        if openai_client is None:
            return "Erro: API key do OpenAI não configurada ou inválida. Por favor, configure a variável OPENAI_API_KEY no arquivo .env com uma chave válida da OpenAI (https://platform.openai.com/account/api-keys)"
        
        try:
            # Adiciona a mensagem do usuário ao histórico
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # Mantém apenas as últimas interações
            if len(self.conversation_history) > self.max_history * 2:  # *2 porque cada interação tem pergunta e resposta
                self.conversation_history = self.conversation_history[-self.max_history * 2:]

            # Prepara o contexto completo
            messages = self.personality.get_conversation_context(self.conversation_history)

            # Gera a resposta usando a nova sintaxe da API
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7,
                presence_penalty=0.6,  # Encoraja respostas mais variadas
                frequency_penalty=0.3   # Reduz repetições
            )

            bot_response = response.choices[0].message.content.strip()
            
            # Adiciona a resposta ao histórico
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            
            return bot_response

        except RateLimitError as e:
            # Erro de rate limit (429) - quota excedida ou muitas requisições
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower() or "429" in error_msg:
                return "❌ Limite de cota excedido: Sua conta OpenAI atingiu o limite de uso. Por favor, verifique seu plano e faturamento em https://platform.openai.com/account/billing. Você pode precisar aguardar o reset da cota ou atualizar seu plano."
            return "⏱️ Limite de requisições excedido: Aguarde alguns instantes antes de tentar novamente."
        
        except AuthenticationError as e:
            error_msg = str(e)
            if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
                return "🔑 Erro de autenticação: A API key do OpenAI está inválida ou expirada. Por favor, verifique sua chave em https://platform.openai.com/account/api-keys e atualize o arquivo .env"
            return f"Erro de autenticação: {error_msg}"
        
        except APIError as e:
            error_msg = str(e)
            # Verifica se é erro de quota mesmo quando não é RateLimitError
            if "429" in error_msg or "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                return "❌ Limite de cota excedido: Sua conta OpenAI atingiu o limite de uso. Verifique seu plano e faturamento em https://platform.openai.com/account/billing"
            # Outros erros da API
            return f"⚠️ Erro na API do OpenAI: {error_msg}. Por favor, tente novamente mais tarde ou verifique a documentação: https://platform.openai.com/docs/guides/error-codes"
        
        except Exception as e:
            error_str = str(e)
            # Verifica se a mensagem contém informações sobre quota
            if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
                return "❌ Limite de cota excedido: Sua conta OpenAI atingiu o limite de uso. Verifique seu plano e faturamento em https://platform.openai.com/account/billing"
            
            print(f"Erro ao gerar resposta: {error_str}")
            return "Perdoe-me, parece que tive um momento de confusão. Poderia reformular sua pergunta?"

# Instância global do gerador de respostas
response_generator = ResponseGenerator()

def generate_response(user_message: str) -> str:
    """
    Função de interface para gerar respostas
    """
    return response_generator.generate_response(user_message)