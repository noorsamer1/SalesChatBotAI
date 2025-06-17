from sqlalchemy import create_engine, text
import pandas as pd
from pathlib import Path
from app.core.config import settings

def build_final_prompt(user_input: str, base_prompt_path: str = "prompts/system_prompt.txt") -> str:
    # Step 1: Load base prompt with placeholders
    base_prompt = Path(base_prompt_path).read_text(encoding="utf-8")

    # Step 2: Create SQLAlchemy engine
    engine = create_engine(
        f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:{settings.PG_PORT}/chatbot_data"
    )

    # Step 3: Get all table names
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        tables = [row[0] for row in result.fetchall()]
        table_names_str = ", ".join(tables)

        # Step 4: For each table, preview top 5 rows
        preview_blocks = []
        for table in tables:
            df = pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT 5', con=engine)
            markdown_table = df.to_markdown(index=False)
            preview_blocks.append(f"Table: {table}\n{markdown_table}\n")

    preview_str = "\n".join(preview_blocks)

    # Step 5: Replace placeholders in the base prompt
    filled_prompt = (
        base_prompt
        .replace("$table_names", table_names_str)
        .replace("$sample_data", preview_str)
    )

    return filled_prompt
