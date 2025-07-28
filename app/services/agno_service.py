import os
from pathlib import Path

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.text import TextKnowledgeBase
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.postgres import PostgresStorage
from agno.vectordb.pgvector import PgVector, SearchType
from dotenv import load_dotenv


class AgnoService:
    def __init__(self) -> None:
        load_dotenv()

        self.archive_path = Path(__file__).parents[2] / "archive"
        self.db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/substack"

        self.memory_db = PostgresMemoryDb(table_name="memories", db_url=self.db_url)
        self.memory = Memory(db=self.memory_db)

        self.knowledge_base = self._knowledge_base()

        self.agent = self._agent()

    def _knowledge_base(self) -> TextKnowledgeBase:
        knowledge_base = TextKnowledgeBase(
            path=self.archive_path,
            vector_db=PgVector(
                table_name="knowledge",
                db_url=self.db_url,
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(id="text-embedding-3-small"),
                vector_score_weight=0.7,
                content_language="portuguese",
                auto_upgrade_schema=True,
            ),
        )
        knowledge_base.load()
        return knowledge_base

    def _agent(self) -> Agent:
        agent_storage = PostgresStorage(
            table_name="agent_sessions",
            db_url=self.db_url,
            auto_upgrade_schema=True,
        )

        return Agent(
            knowledge=self.knowledge_base,
            model=OpenAIChat(id="gpt-4o", temperature=0),
            storage=agent_storage,
            memory=self.memory,
            search_knowledge=True,
            add_references=True,
            markdown=True,
            enable_user_memories=True,
        )

    def run(self) -> None:
        os.system("clear")
        while True:
            print("Talk to the assistant. Type 'exit' to quit.")
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            self.agent.print_response(user_input, markdown=True)
