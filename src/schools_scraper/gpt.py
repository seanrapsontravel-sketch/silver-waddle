"""GPT integration for data analysis and prompts."""

import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openai import OpenAI

from schools_scraper.config import config
from schools_scraper.search import NewsletterSearch
from schools_scraper.search import NewsletterSearch


class GPTClient:
    """OpenAI GPT client for data analysis."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize GPT client.

        Args:
            api_key: OpenAI API key. Defaults to config.OPENAI_API_KEY.
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY in .env file."
            )
        self.client = OpenAI(api_key=self.api_key)

    def prompt(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a prompt to GPT and get a response.

        Args:
            prompt: The prompt text.
            model: GPT model to use.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum tokens in response.

        Returns:
            GPT response text.
        """
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        question: str,
        model: str = "gpt-4o-mini",
        sample_rows: int = 100,
    ) -> str:
        """Analyze a DataFrame using GPT.

        Args:
            df: DataFrame to analyze.
            question: Question about the data.
            sample_rows: Number of rows to include in the prompt (to avoid token limits).

        Returns:
            GPT analysis response.
        """
        # Sample data if too large
        sample_df = df.head(sample_rows) if len(df) > sample_rows else df

        # Create data summary
        summary = f"""
DataFrame shape: {df.shape}
Columns: {', '.join(df.columns.tolist())}
Data types: {df.dtypes.to_dict()}
Sample data (first {len(sample_df)} rows):
{sample_df.to_string()}
"""

        prompt = f"""You are a data analyst. Analyze the following data and answer the question.

{summary}

Question: {question}

Provide a clear, concise analysis."""
        return self.prompt(prompt, model=model)

    def generate_insights(
        self,
        table_name: str,
        db_query: str,
        question: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ) -> str:
        """Generate insights from a database query result.

        Args:
            table_name: Name of the table (for context).
            db_query: SQL query to execute (or description of data).
            question: Optional specific question to answer.

        Returns:
            GPT-generated insights.
        """
        if question:
            prompt = f"""Analyze data from the '{table_name}' table based on this query/description:
{db_query}

Question: {question}

Provide insights and analysis."""
        else:
            prompt = f"""Analyze data from the '{table_name}' table based on this query/description:
{db_query}

Provide key insights and patterns you notice."""
        return self.prompt(prompt, model=model)

    def answer_question(
        self,
        question: str,
        table_name: str = "newsletters",
        model: str = "gpt-4o-mini",
        max_newsletters: int = 20,
        max_chars: int = 10000,
        temperature: float = 0.3,
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Answer a question by searching newsletters and using GPT.

        Args:
            question: The question to answer.
            table_name: Name of the newsletters table.
            model: GPT model to use.
            max_newsletters: Maximum number of newsletters to search.
            max_chars: Maximum characters of newsletter text to include.
            temperature: Sampling temperature (lower = more focused).

        Returns:
            Tuple of (answer text, list of source dicts).
        """
        # Search for relevant newsletters
        with NewsletterSearch() as search:
            relevant_text, sources = search.get_relevant_text(
                query=question,
                table_name=table_name,
                max_results=max_newsletters,
                max_chars=max_chars,
            )

        # Build sources reference for GPT
        sources_text = ""
        if sources:
            sources_list = []
            for i, source in enumerate(sources, 1):
                source_line = f"{i}. Title: {source['title']}"
                if source.get('heading'):
                    source_line += f" | Heading: {source['heading']}"
                source_line += f" | URL: {source['url']}"
                sources_list.append(source_line)
            sources_text = "\n\nNewsletter Sources:\n" + "\n".join(sources_list)

        # Build prompt for GPT
        system_prompt = (
            "You are an assistant that analyzes WeST (Westcountry Schools Trust) "
            "newsletters to provide detailed, comprehensive answers. Use only the information "
            "provided in the newsletter excerpts. If the information is not "
            "available in the excerpts, say so clearly. When referencing a newsletter, "
            "use markdown link format: [newsletter title](URL) to create clickable links. "
            "Always provide detailed explanations with specific examples, dates, and context "
            "when available in the source material."
        )

        user_prompt = f"""Here are relevant newsletter excerpts:

{relevant_text}
{sources_text}

Answer this question based on the information above: {question}

Provide a detailed, comprehensive answer that includes:
1. A clear explanation of the answer
2. Specific examples, dates, or details from the newsletters when available
3. Context and background information if relevant
4. Multiple examples if the newsletters mention several instances

When you reference a specific newsletter, format it as a markdown link like this: [newsletter title](URL). For example, if referencing a newsletter titled "Weekly Whistle 06/09/24" with URL "https://example.com/newsletter?id=123", write: [Weekly Whistle 06/09/24](https://example.com/newsletter?id=123).

Be thorough and include as much relevant detail as possible from the source material. If there are multiple examples or instances mentioned, include them all."""

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        response = self.client.chat.completions.create(**kwargs)
        answer = response.choices[0].message.content or ""
        return answer, sources


