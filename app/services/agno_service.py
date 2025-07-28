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
        """
        Initialize an AgnoService, which is capable of chatting with a user
        using the knowledge from the substack database.

        The database is loaded into memory, and a chatbot agent is created
        using the knowledge from the database.

        The chatbot is configured to use the text-embedding-3-large model, with
        a hybrid search type and a vector score weight of 0.7. The content
        language is set to portuguese, and the database schema is automatically
        upgraded if necessary.

        The chatbot is also configured to add references to the output, and to
        use markdown.
        """
        load_dotenv()

        self.archive_path = Path(__file__).parents[2] / "archive"
        self.db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/substack"

        # Create memory storage
        self.memory_db = PostgresMemoryDb(table_name="memories", db_url=self.db_url)
        self.memory = Memory(db=self.memory_db)

        self.knowledge_base = self._knowledge_base()
        self.agent = self._agent()

    def _knowledge_base(self) -> TextKnowledgeBase:
        """
        Create a TextKnowledgeBase from the Substack data stored in the
        `archive` directory.

        The knowledge base is configured to use the `substack` table in the
        PostgreSQL database at `self.db_url`, and to use the
        `text-embedding-3-large` model to generate vector embeddings.

        The knowledge base is also configured to use a hybrid search type,
        with a vector score weight of 0.7, and to automatically upgrade the
        database schema if necessary.

        The content language is set to Portuguese.

        The knowledge base is loaded into memory when created.
        """
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
        """
        Run the AgnoService, which is capable of chatting with a user
        using the knowledge from the substack database.

        The chatbot is configured to use the text-embedding-3-large model, with
        a hybrid search type and a vector score weight of 0.7. The content
        language is set to portuguese, and the database schema is automatically
        upgraded if necessary.

        The chatbot is also configured to add references to the output, and to
        use markdown.
        """
        os.system("clear")
        while True:
            print("Talk to the assistant. Type 'exit' to quit.")
            user_input = input("User: ")
            if user_input.lower() == "exit":
                break
            self.agent.print_response(user_input, markdown=True)
