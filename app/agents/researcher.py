from typing import List, Dict, Set, Optional, Protocol
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import hashlib
import re
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from app.config.config import get_settings
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.state import ResearchState, SectionState, Section
import json
import os
from datetime import datetime
from pathlib import Path
import sqlite3
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SearchEngine(Enum):
    TAVILY = "tavily"
    GEMINI = "gemini"
    DEEP_RESEARCH = "deep_research"

@dataclass
class QueryValidation:
    specificity: float
    relevance: float
    clarity: float
    
    @property
    def overall_score(self) -> float:
        return (self.specificity + self.relevance + self.clarity) / 3

class ResearchStatus(Enum):
    NOT_STARTED = "not_started"
    GENERATING_QUERIES = "generating_queries"
    SEARCHING = "searching"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"

class ResearchStateSchema(BaseModel):
    """Schema for validating research state"""
    section_id: str
    status: ResearchStatus
    queries: List[Dict] = Field(default_factory=list)
    sources: List[Dict] = Field(default_factory=list)
    content: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    error_log: List[Dict] = Field(default_factory=list)

class ResearchRepository(Protocol):
    """Interface for research state persistence"""
    async def save_state(self, section_id: str, state: Dict) -> None:
        """Save research state"""
        pass

    async def load_state(self, section_id: str) -> Optional[Dict]:
        """Load research state"""
        pass

    async def log_error(self, section_id: str, error_message: str) -> None:
        """Log error message"""
        pass

class SQLiteResearchRepository(ResearchRepository):
    def __init__(self, db_path: str = "research_state.db"):
        """Initialize SQLite repository"""
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_state (
                    section_id TEXT PRIMARY KEY,
                    state_json TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id TEXT,
                    error_message TEXT,
                    timestamp TIMESTAMP
                )
            """)

    async def save_state(self, section_id: str, state: Dict) -> None:
        """Save research state to database"""
        try:
            # Validate state against schema
            state_model = ResearchStateSchema(**state)
            state_json = json.dumps(state_model.dict())
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO research_state 
                    (section_id, state_json, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (section_id, state_json))
                
        except Exception as e:
            logger.error(f"Error saving state for section {section_id}: {str(e)}")
            raise

    async def load_state(self, section_id: str) -> Optional[Dict]:
        """Load research state from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT state_json FROM research_state WHERE section_id = ?",
                    (section_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    state_dict = json.loads(result[0])
                    # Validate loaded state
                    state_model = ResearchStateSchema(**state_dict)
                    return state_model.dict()
                return None
                
        except Exception as e:
            logger.error(f"Error loading state for section {section_id}: {str(e)}")
            return None

    async def log_error(self, section_id: str, error_message: str) -> None:
        """Log errors to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO error_log (section_id, error_message, timestamp)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (section_id, error_message))
        except Exception as e:
            logger.error(f"Error logging error for section {section_id}: {str(e)}")

class ResearchManager:
    def __init__(self, settings=None, repository: Optional[ResearchRepository] = None):
        """Initialize ResearchManager with configuration settings and repository."""
        self.settings = settings or get_settings()
        self.max_retries = 3
        self.min_wait = 1
        self.max_wait = 10
        
        # Initialize Gemini API
        genai.configure(api_key=self.settings.google_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
        self.query_cache: Set[str] = set()
        
        # Initialize repository (default to SQLite if none provided)
        self.repository = repository or SQLiteResearchRepository()

    def _normalize_query(self, query: str) -> str:
        """Normalize a query by removing extra spaces and converting to lowercase."""
        return re.sub(r'\s+', ' ', query.lower().strip())

    def _get_query_hash(self, query: str) -> str:
        """Generate a hash for a query to help with deduplication."""
        return hashlib.md5(query.encode()).hexdigest()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        retry=retry_if_exception_type((
            TimeoutError, 
            ConnectionError, 
            Exception,
            google_exceptions.ResourceExhausted
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _call_gemini_with_retry(self, prompt: str) -> str:
        """Helper method to make Gemini API calls with retry logic."""
        try:
            if len(prompt) > 30000:
                prompt = prompt[:30000] + "..."
            
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config={
                    'temperature': 0.1,
                    'max_output_tokens': 8192,
                    'top_p': 0.8,
                    'top_k': 40
                }
            )
            return response.text.strip() if response else ""
        except Exception as e:
            logger.warning(f"Gemini API call failed: {str(e)}")
            if "ResourceExhausted" in str(e):
                logger.error("Resource exhausted error - waiting longer before retry")
                await asyncio.sleep(10)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def validate_query(self, query: str) -> QueryValidation:
        """Validate a search query using Gemini's capabilities."""
        try:
            prompt = f"""
            Evaluate this search query: "{query}"
            Score the following criteria (0.0 to 1.0):
            - Specificity: How specific and focused is the query?
            - Relevance: How likely is it to return useful results?
            - Clarity: How clear and well-formed is the query?
            Return only the scores in JSON format.
            """
            
            response = await self._call_gemini_with_retry(prompt)
            scores = eval(response)
            return QueryValidation(
                specificity=scores['specificity'],
                relevance=scores['relevance'],
                clarity=scores['clarity']
            )
        except Exception as e:
            logger.error(f"Query validation failed: {str(e)}")
            return QueryValidation(specificity=0.0, relevance=0.0, clarity=0.0)

    async def generate_initial_queries(self, state: SectionState) -> List[str]:
        """Generate initial queries using Gemini with retry logic."""
        try:
            prompt = f"""
            Generate {self.settings.number_of_queries} specific and diverse search queries for researching:
            Topic: {state['section'].name}
            Context: {state['section'].description}

            Requirements:
            - Each query should focus on a different aspect
            - Make queries specific and actionable
            - Avoid generic or overly broad queries
            - Include both factual and analytical queries

            Return only the numbered list of queries, one per line.
            Maximum number of queries: {self.settings.number_of_queries}
            """
            
            response = await self._call_gemini_with_retry(prompt)
            
            if not response:
                logger.warning("Empty response from Gemini after retries")
                return []
                
            queries = response.split('\n')
            queries = [q.strip() for q in queries if q.strip()][:self.settings.number_of_queries]
            
            return queries

        except Exception as e:
            logger.error(f"Error in generate_initial_queries after retries: {str(e)}")
            return []

    async def generate_queries(self, state: SectionState) -> dict:
        """Generate and validate search queries using multiple engines."""
        try:
            logger.debug(f"Generating queries for section: {state['section'].name}")
            
            initial_queries = await self.generate_initial_queries(state)
            
            if not initial_queries:
                logger.warning("No initial queries generated after retries")
                return {"search_queries": []}
            
            validated_queries = []
            for query in initial_queries:
                try:
                    normalized_query = self._normalize_query(query)
                    query_hash = self._get_query_hash(normalized_query)
                    
                    if query_hash in self.query_cache:
                        continue
                    
                    validation = await self.validate_query(normalized_query)
                    
                    if validation.overall_score >= 0.6:
                        validated_queries.append({
                            'search_query': normalized_query,
                            'validation': validation,
                            'engines': self._select_search_engines(validation)
                        })
                        self.query_cache.add(query_hash)
                        
                    if len(validated_queries) >= self.settings.number_of_queries:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error processing query '{query}' after retries: {str(e)}")
                    continue
            
            return {"search_queries": validated_queries}

        except Exception as e:
            logger.error(f"Error generating queries after retries: {str(e)}")
            return {"search_queries": []}

    async def write_section(self, state: SectionState) -> dict:
        """Write a section based on research results using Gemini."""
        try:
            logger.debug(f"Writing section: {state['section'].name}")
            section = state["section"]
            source_str = state["source_str"]

            if len(source_str) > 25000:
                logger.warning("Source material too long, truncating...")
                source_str = source_str[:25000] + "... [truncated for length]"

            prompt = f"""
            Write a comprehensive section about: {section.name}
            
            Context and requirements:
            - Topic description: {section.description}
            - Use the following source material: {source_str}
            
            Guidelines:
            - Be thorough but concise
            - Include key facts and analysis
            - Maintain a professional tone
            - Organize information logically
            - Cite sources where appropriate
            
            Maximum length: 2000 words.
            Write the section content now.
            """

            try:
                section_content = await self._call_gemini_with_retry(prompt)
                if not section_content:
                    raise ValueError("Empty response from Gemini")
                
                section.content = section_content
                logger.debug(f"Completed writing section: {section.name}")
                return {"completed_sections": [section]}

            except Exception as e:
                logger.error(f"Error in first attempt, trying with reduced content: {str(e)}")
                shorter_prompt = f"""
                Write a brief section about: {section.name}
                Topic description: {section.description}
                Key points from sources: {source_str[:5000]}...
                
                Write a concise summary (max 500 words).
                """
                section_content = await self._call_gemini_with_retry(shorter_prompt)
                section.content = section_content
                return {"completed_sections": [section]}

        except Exception as e:
            logger.error(f"Error writing section: {str(e)}")
            section.content = f"Error generating content for section: {section.name}. Please try again later."
            return {"completed_sections": [section]}

    def _select_search_engines(self, validation: QueryValidation) -> List[SearchEngine]:
        """Select appropriate search engines based on query validation."""
        engines = []
        
        # Always include Tavily for baseline results
        engines.append(SearchEngine.TAVILY)
        
        # Add Gemini for highly specific queries
        if validation.specificity >= 0.8:
            engines.append(SearchEngine.GEMINI)
        
        # Add Deep Research for complex queries needing detailed analysis
        if validation.relevance >= 0.8 and validation.clarity >= 0.7:
            engines.append(SearchEngine.DEEP_RESEARCH)
        
        return engines

    async def _update_state(self, section: Section, status: ResearchStatus, **kwargs):
        """Update and save research state"""
        try:
            current_state = await self.repository.load_state(section.id) or {}
            
            # Update state with new information
            new_state = {
                "section_id": section.id,
                "status": status,
                "last_updated": datetime.utcnow(),
                **current_state,
                **kwargs
            }
            
            await self.repository.save_state(section.id, new_state)
            
        except Exception as e:
            error_msg = f"Error updating state: {str(e)}"
            logger.error(error_msg)
            await self.repository.log_error(section.id, error_msg)

    async def research_section(self, section: Section) -> Section:
        """Perform complete research process for a single section with state management."""
        try:
            # Initialize or recover state
            state = await self.repository.load_state(section.id)
            if state and state["status"] == ResearchStatus.COMPLETED:
                logger.info(f"Section {section.id} already completed, loading from state")
                section.content = state["content"]
                return section

            # Start research process
            await self._update_state(section, ResearchStatus.GENERATING_QUERIES)
            section_state = SectionState(section=section)
            
            # Generate queries
            queries_result = await self.generate_queries(section_state)
            await self._update_state(
                section, 
                ResearchStatus.SEARCHING,
                queries=queries_result["search_queries"]
            )
            section_state.update(queries_result)
            
            # Perform web search
            search_result = await self.search_web(section_state)
            await self._update_state(
                section,
                ResearchStatus.WRITING,
                sources=search_result["source_str"]
            )
            section_state.update(search_result)
            
            # Write section
            write_result = await self.write_section(section_state)
            completed_section = write_result["completed_sections"][0]
            
            # Update final state
            await self._update_state(
                section,
                ResearchStatus.COMPLETED,
                content=completed_section.content
            )
            
            return completed_section
            
        except Exception as e:
            error_msg = f"Error researching section {section.id}: {str(e)}"
            logger.error(error_msg)
            await self._update_state(section, ResearchStatus.FAILED)
            await self.repository.log_error(section.id, error_msg)
            raise

    async def recover_state(self, section: Section) -> Optional[Section]:
        """Attempt to recover research state for a section"""
        try:
            state = await self.repository.load_state(section.id)
            if not state:
                return None
                
            if state["status"] == ResearchStatus.COMPLETED:
                section.content = state["content"]
                return section
                
            # If failed or incomplete, return last known state
            return Section(
                id=section.id,
                name=section.name,
                description=section.description,
                content=state.get("content", "")
            )
            
        except Exception as e:
            logger.error(f"Error recovering state for section {section.id}: {str(e)}")
            return None

    async def search_web(self, state: SectionState) -> dict:
        """Perform web searches based on generated queries.

        Args:
            state: Current section state containing search queries

        Returns:
            dict: Dictionary containing formatted search results
        """
        try:
            logger.debug("Starting web search")
            search_queries = state["search_queries"]

            # Extract queries and perform searches
            query_list = [query.search_query for query in search_queries]
            search_docs = await tavily_search_async(
                query_list,
                self.settings.tavily_topic,
                self.settings.tavily_days
            )

            # Format and deduplicate results
            source_str = deduplicate_and_format_sources(
                search_docs,
                max_tokens_per_source=5000,
                include_raw_content=True
            )

            logger.debug("Web search completed")
            return {"source_str": source_str}

        except Exception as e:
            logger.error(f"Error during web search: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup method to clear Gemini API caches when done."""
        pass
