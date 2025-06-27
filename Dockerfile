# Use uma imagem Python oficial como base
FROM python:3.11-slim

# Defina o diretório de trabalho no container
WORKDIR /app

# Copie o arquivo de dependências para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências
# Usamos --no-cache-dir para manter a imagem leve
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação para o diretório de trabalho
COPY . .

# Exponha a porta que o Streamlit usa (o padrão é 8501)
EXPOSE 8501

# Comando para rodar a aplicação quando o container iniciar
# Usamos --server.port para garantir que ele rode na porta exposta
# Usamos --server.address=0.0.0.0 para permitir conexões externas
CMD ["streamlit", "run", "interface/app.py", "--server.port=8501", "--server.address=0.0.0.0"] 