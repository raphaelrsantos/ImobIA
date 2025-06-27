# tools/search_tool.py
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import re
import json

# Define o esquema de entrada para a ferramenta, para guiar o LLM
class SearchToolSchema(BaseModel):
    search_query: str = Field(..., description="O termo de busca a ser usado na base de conhecimento. Deve ser o mais específico possível, combinando o assunto e a cidade, se aplicável.")

# Define o esquema de entrada para a ferramenta, garantindo que o agente passe um único argumento 'search_query'
class SearchInput(BaseModel):
    search_query: str = Field(description="O termo ou frase que deve ser buscado na base de conhecimento.")

class KnowledgeSearchTool(BaseTool):
    name: str = "Ferramenta de Busca na Base de Conhecimento"
    description: str = "Busca informações na base de conhecimento da empresa. Use esta ferramenta para encontrar detalhes sobre imóveis, processos financeiros, vagas, etc."
    args_schema: type[BaseModel] = SearchInput

    def _run(self, search_query: str) -> str:
        """Busca informações na base de conhecimento de forma estruturada."""
        # O agente pode, por engano, passar um JSON string. Esta lógica extrai a query real.
        try:
            data = json.loads(search_query)
            if isinstance(data, dict):
                actual_query = data.get('search_query', search_query)
            else:
                actual_query = search_query
        except (json.JSONDecodeError, TypeError):
            actual_query = search_query

        try:
            with open("knowledge_base.txt", "r", encoding="utf-8") as f:
                knowledge_base = f.read().lower()
            
            sections = knowledge_base.split('## ')
            
            query_terms = actual_query.lower().split()
            
            relevant_sections = []
            for section in sections:
                if all(term in section for term in query_terms):
                    relevant_sections.append(section.strip())

            if relevant_sections:
                return "\\n\\n".join(relevant_sections)
            else:
                return f"Nenhum conhecimento encontrado para: '{actual_query}'"

        except FileNotFoundError:
            return "Erro: O arquivo 'knowledge_base.txt' não foi encontrado."
        except Exception as e:
            return f"Ocorreu um erro inesperado ao buscar na base de conhecimento: {e}"

# Instanciar a ferramenta para ser importada em outros lugares
knowledge_search_tool = KnowledgeSearchTool() 