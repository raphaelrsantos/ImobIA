# helena_main.py
import os
import io
import json
import re
from contextlib import redirect_stdout
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from tools.search_tool import knowledge_search_tool

load_dotenv()

# --- CONFIGURAÇÃO DO MODELO DE LINGUAGEM ---
# Assegura que a chave da API da OpenAI está disponível
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("A variável de ambiente OPENAI_API_KEY não foi encontrada.")

# Define o modelo de linguagem para todos os agentes
llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0.2,
    api_key=SecretStr(api_key)
)

# --- AGENTES ESPECIALISTAS E DE EXTRAÇÃO ---

# 1. Agente Extrator Mestre: O único responsável por analisar e atualizar o estado da conversa.
extrator_mestre_agente = Agent(
    role="Assistente Mestre de Extração de Dados",
    goal="Analisar o estado de uma conversa e a última mensagem de um usuário para extrair e estruturar informações (nome, cidade, assunto), retornando um JSON completo com o estado atualizado.",
    backstory="Um especialista em NLP treinado para entender o fluxo de diálogo e preencher informações faltantes de forma inteligente, simplificando os tópicos para serem acionáveis.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# 2. Agente Roteador para decidir a quem delegar
roteador_agente = Agent(
    role="Roteador de Atendimento",
    goal="Analisar um assunto e escolher o agente especialista adequado.",
    backstory="Um despachante eficiente que direciona casos para o departamento correto.",
    llm=llm,
    verbose=True, allow_delegation=False
)

# 3. Agentes Especialistas por Assunto
agente_rh = Agent(
    role="Especialista de RH",
    goal="Responder perguntas sobre vagas de emprego usando a base de conhecimento.",
    backstory="Você é um assistente da Cardoso Imóveis. Sua ÚNICA função é usar a 'Ferramenta de Busca na Base de Conhecimento' para responder perguntas. Você NUNCA deve inventar informações. Se a ferramenta não encontrar nada, você deve apenas informar isso.",
    tools=[knowledge_search_tool],
    llm=llm,
    verbose=True, allow_delegation=False
)

agente_financeiro = Agent(
    role="Especialista Financeiro",
    goal="Ajudar clientes com dúvidas sobre boletos e pagamentos usando a base de conhecimento.",
    backstory="Você é um assistente da Cardoso Imóveis. Sua ÚNICA função é usar a 'Ferramenta de Busca na Base de Conhecimento' para responder perguntas. Você NUNCA deve inventar informações. Se a ferramenta não encontrar nada, você deve apenas informar isso.",
    tools=[knowledge_search_tool],
    llm=llm,
    verbose=True, allow_delegation=False
)

agente_imoveis = Agent(
    role="Consultor de Imóveis",
    goal="Apresentar informações sobre empreendimentos usando a base de conhecimento.",
    backstory="Você é um assistente da Cardoso Imóveis. Sua ÚNICA função é usar a 'Ferramenta de Busca na Base de Conhecimento' para responder perguntas. Você NUNCA deve inventar informações. Se a ferramenta não encontrar nada, você deve apenas informar isso.",
    tools=[knowledge_search_tool],
    llm=llm,
    verbose=True, allow_delegation=False
)

# 4. Agente para finalizar a conversa
finalizador_agente = Agent(
    role="Avaliador de Fim de Conversa",
    goal="Analisar o texto do usuário para determinar se ele está se despedindo ou agradecendo, indicando o fim da conversa. Responda com um JSON contendo a chave 'finalizar' (true ou false).",
    backstory="Você é um especialista em análise de sentimento e intenção, focado em identificar sinais de conclusão em um diálogo.",
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# Mapeamento de nomes para objetos de agente
agentes_especialistas = {
    "agente_rh": agente_rh,
    "agente_financeiro": agente_financeiro,
    "agente_imoveis": agente_imoveis
}


def extrair_info_e_atualizar_estado(estado_conversa, texto_usuario, agente_extrator):
    """
    Usa um único agente poderoso para analisar o estado e a entrada do usuário,
    e retorna um JSON com o estado completamente atualizado.
    """
    estado_json = json.dumps(estado_conversa)

    tarefa_extracao = Task(
        description=f"""Sua tarefa é analisar o estado ATUAL de uma conversa e a ÚLTIMA mensagem do usuário para preencher as informações que faltam: nome, cidade e assunto.

### Estado Atual da Conversa (em JSON):
{estado_json}

### Última Mensagem do Usuário:
'{texto_usuario}'

### Suas Regras:
1.  **Analise a mensagem do usuário** e veja se ela contém alguma das informações que estão como `null` no estado atual.
2.  **Assunto:** O 'assunto' deve ser sempre simplificado para 1-3 palavras-chave (ex: 'imóveis', 'vagas de emprego', 'segunda via boleto'). Ignore palavras de preenchimento como "quero saber sobre", "falar de", etc.
3.  **Não invente o assunto:** Se a mensagem do usuário for apenas um nome ou uma cidade (ex: "Raphael" ou "Rio Verde"), o campo 'assunto' deve permanecer `null`. O assunto só deve ser preenchido quando o usuário explicitamente perguntar sobre algo.
4.  **Retorne o estado COMPLETO** e atualizado em um único bloco de código JSON. Mantenha os valores que já existiam se a nova mensagem não os contradisser.

### Exemplo:
Se o estado atual for `{{"nome": "Raphael", "cidade": null, "assunto": null}}` e a mensagem for "Gostaria de informações sobre imóveis em Rio Verde", sua saída deve ser:
```json
{{
  "nome": "Raphael",
  "cidade": "Rio Verde",
  "assunto": "imóveis"
}}
```

### Sua Tarefa Agora:
Analise o estado e a mensagem fornecidos e retorne o JSON atualizado.
""",
        expected_output="Um único bloco de código JSON contendo o estado da conversa completo e atualizado com as chaves 'nome', 'cidade' e 'assunto'.",
        agent=agente_extrator,
    )
    
    try:
        resultado_obj = Crew(agents=[agente_extrator], tasks=[tarefa_extracao]).kickoff()
    except Exception as e:
        print(f"--- ERRO NO KICKOFF DA EXTRAÇÃO: {e} ---")
        return {}

    resultado_str = str(resultado_obj) if resultado_obj else ""

    try:
        match = re.search(r"```(json)?\s*(\{.*?\})\s*```", resultado_str, re.DOTALL)
        json_str = ""
        if match:
            json_str = match.group(2)
        else:
            match = re.search(r"(\{.*?\})", resultado_str, re.DOTALL)
            if match:
                json_str = match.group(1)

        if json_str:
            return json.loads(json_str)
        return {}
    except (json.JSONDecodeError, IndexError):
        return {}

def verificar_se_finaliza(entrada_usuario):
    """Usa o agente finalizador para verificar se a conversa deve terminar."""
    tarefa_finalizacao = Task(
        description=f"Analise a seguinte mensagem do usuário: '{entrada_usuario}'. O usuário está agradecendo ou se despedindo (ex: 'obrigado', 'ok', 'valeu', 'tchau')? Responda com um JSON contendo apenas a chave 'finalizar' com o valor booleano 'true' se a conversa deve terminar, ou 'false' se deve continuar.",
        expected_output='Um JSON com uma única chave "finalizar" e um valor booleano (true ou false).',
        agent=finalizador_agente
    )
    
    try:
        resultado_str = str(Crew(agents=[finalizador_agente], tasks=[tarefa_finalizacao]).kickoff())
        match = re.search(r"(\{.*?\})", resultado_str, re.DOTALL)
        if match:
            json_data = json.loads(match.group(1))
            return json_data.get("finalizar", False)
    except Exception:
        return False # Em caso de erro, assume que a conversa não deve finalizar
    return False

def rodar_atendimento(estado_conversa, entrada_usuario):
    """
    Gerencia o estado da conversa: coleta dados, delega para um especialista e permite a conversa contínua.
    """
    # Se a conversa já tem um especialista definido, a interação é com ele (com lógica de re-roteamento).
    if estado_conversa.get('agente_atual'):
        if verificar_se_finaliza(entrada_usuario):
            return {"nome": None, "cidade": None, "assunto": None, "agente_atual": None}, "Que bom que pude ajudar! Se precisar de mais alguma coisa, é só chamar."
        
        # O extrator mestre também pode identificar mudanças de contexto
        estado_potencialmente_novo = extrair_info_e_atualizar_estado(estado_conversa, entrada_usuario, extrator_mestre_agente)
        
        mudou_de_assunto = estado_potencialmente_novo.get('assunto') and estado_potencialmente_novo['assunto'] != estado_conversa['assunto']
        
        # Atualiza estado e força re-roteamento se o assunto mudou
        if mudou_de_assunto:
            estado_conversa['assunto'] = estado_potencialmente_novo['assunto']
            if estado_potencialmente_novo.get('cidade'):
                 estado_conversa['cidade'] = estado_potencialmente_novo['cidade']
            estado_conversa['agente_atual'] = None # Força re-roteamento
        
        else: # Se não mudou de assunto, continua a conversa
            agente_especialista = agentes_especialistas.get(estado_conversa['agente_atual'])
            if agente_especialista:
                contexto_conversa = f"Contexto: Cliente={estado_conversa['nome']}, Cidade={estado_conversa['cidade']}, Assunto={estado_conversa['assunto']}. Mensagem: '{entrada_usuario}'."
                tarefa_continuada = Task(
                    description=f"Continue a conversa com base no contexto: {contexto_conversa}. Use a ferramenta de busca com o assunto e a cidade para encontrar a resposta.",
                    expected_output="Uma resposta relevante para o cliente, baseada estritamente no resultado da ferramenta de busca.",
                    agent=agente_especialista
                )
                resposta = str(Crew(agents=[agente_especialista], tasks=[tarefa_continuada]).kickoff())
                return estado_conversa, resposta

    # --- LÓGICA DE COLETA COM EXTRATOR MESTRE ---
    
    # 1. Sempre chame o extrator para ter o estado mais atualizado possível.
    novo_estado_extraido = extrair_info_e_atualizar_estado(estado_conversa, entrada_usuario, extrator_mestre_agente)

    # Atualiza o estado da sessão com o que foi extraído.
    for key, value in novo_estado_extraido.items():
        if value is not None and key in estado_conversa:
            estado_conversa[key] = value

    # 2. Verifica o checklist e pergunta pelo primeiro item que falta.
    if estado_conversa.get('nome') is None:
        return estado_conversa, "Olá! Para começarmos, por favor, me diga seu nome."

    if estado_conversa.get('cidade') is None:
        return estado_conversa, f"Prazer, {estado_conversa['nome'].split()[0]}! Agora, por favor, me informe de qual cidade você está falando ou sobre qual cidade gostaria de informações."

    if estado_conversa.get('assunto') is None:
        return estado_conversa, f"Entendido. E como posso te ajudar hoje, {estado_conversa['nome'].split()[0]}?"
    
    # 3. Se todos os dados estão preenchidos, delega para o especialista.
    tarefa_roteamento = Task(
        description=f"Para um cliente querendo tratar sobre '{estado_conversa['assunto']}', qual agente é o mais indicado? Opções: agente_rh, agente_financeiro, agente_imoveis. Retorne APENAS o nome do agente.",
        expected_output="O nome exato de um dos agentes (ex: 'agente_rh').",
        agent=roteador_agente
    )
    nome_agente_escolhido = str(Crew(agents=[roteador_agente], tasks=[tarefa_roteamento]).kickoff()).strip()

    agente_escolhido = agentes_especialistas.get(nome_agente_escolhido)
    if not agente_escolhido:
        agente_escolhido = agente_imoveis
        estado_conversa['agente_atual'] = "agente_imoveis"
    else:
        estado_conversa['agente_atual'] = nome_agente_escolhido

    contexto_para_especialista = f"Cliente: {estado_conversa['nome']}, Cidade: {estado_conversa['cidade']}, Assunto: '{estado_conversa['assunto']}'."
    tarefa_final = Task(
        description=f"Inicie o atendimento com base no contexto: {contexto_para_especialista}. Use a ferramenta de busca com o assunto e a cidade. Se não achar, informe que não encontrou detalhes.",
        expected_output="Uma resposta inicial e factual para o cliente, baseada apenas nos dados da ferramenta de busca.",
        agent=agente_escolhido
    )
    resposta_final = str(Crew(agents=[agente_escolhido], tasks=[tarefa_final]).kickoff())
    
    return estado_conversa, resposta_final 