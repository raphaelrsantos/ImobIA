# Script para criar o arquivo .env com encoding correto
with open('.env', 'w', encoding='utf-8') as f:
    f.write("""# Configurações da API OpenAI
OPENAI_API_KEY=sua-chave-api-aqui

# Configurações da Serper API
SERPER_API_KEY=sua-chave-serper-aqui

# Modelo OpenAI (opcional - padrão: gpt-3.5-turbo)
OPENAI_MODEL=gpt-3.5-turbo

# Temperatura do modelo (opcional - padrão: 0.7)
TEMPERATURE=0.7
""")

print("Arquivo .env criado com sucesso!") 