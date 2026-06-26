"""
RAG-based Q&A over an indexed codebase using LangChain + pgvector.
"""
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.embedding_service import search_symbols

settings = get_settings()

SYSTEM_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert software engineer helping a new developer understand a codebase.

Use the following code snippets retrieved from the repository to answer the question.
Be specific — mention file paths, function names, and line numbers when relevant.
If the code snippets don't contain enough info, say so clearly.

Retrieved code context:
{context}

Question: {question}

Answer:"""
)


def answer_question(repository_id: str, question: str) -> dict:
    db = SessionLocal()
    try:
        raw_results = search_symbols(
            repository_id=repository_id,
            query=question,
            db=db,
            n_results=8,
        )

        # Build context string from top results
        context_parts = []
        sources = []
        for r in raw_results:
            symbol = r["symbol"]
            db_file = db.query(__import__(
                "app.models.models", fromlist=["CodeFile"]
            ).CodeFile).filter_by(id=symbol.file_id).first()
            file_path = db_file.path if db_file else "unknown"

            context_parts.append(
                f"# {symbol.qualified_name} ({symbol.kind}) in {file_path} "
                f"(lines {symbol.line_start}–{symbol.line_end})\n"
                f"{symbol.source_code or ''}"
            )
            sources.append({
                "file_path": file_path,
                "qualified_name": symbol.qualified_name,
                "kind": symbol.kind.value if symbol.kind else None,
                "line_start": symbol.line_start,
            })

        context = "\n\n---\n\n".join(context_parts)

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key,
        )

        prompt = SYSTEM_PROMPT.format(context=context, question=question)
        response = llm.invoke(prompt)

        return {
            "answer": response.content,
            "sources": sources,
        }
    finally:
        db.close()
