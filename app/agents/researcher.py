from app.utils.state import ResearchState
import os
import google.generativeai as genai
from tavily import TavilyClient
from typing import Dict, List, Optional, Callable, Any
import json
import jsonschema
from datetime import datetime
from pathlib import Path
import pickle
from dataclasses import asdict
import logging
import time
from functools import wraps
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Performance metrics decorator
def track_performance(func: Callable) -> Callable:
    """Decorator to track function performance metrics."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        metrics = {
            'function': func.__name__,
            'start_time': datetime.now().isoformat(),
            'tokens_used': 0,
            'api_calls': 0
        }
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Calculate metrics
            metrics.update({
                'duration': time.time() - start_time,
                'status': 'success'
            })
            
            # If result has token usage info (e.g., from Gemini response)
            if hasattr(result, 'candidates'):
                for candidate in result.candidates:
                    if hasattr(candidate, 'token_count'):
                        metrics['tokens_used'] += candidate.token_count
            
            return result
            
        except Exception as e:
            metrics.update({
                'duration': time.time() - start_time,
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            raise
            
        finally:
            # Save metrics
            save_metrics(metrics)
            
    return wrapper

def save_metrics(metrics: Dict[str, Any]) -> None:
    """Save performance metrics to disk."""
    metrics_dir = Path("./metrics")
    metrics_dir.mkdir(exist_ok=True)
    
    metrics_file = metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    try:
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics) + '\n')
    except Exception as e:
        logger.error(f"Error saving metrics: {e}")

# Debug mode configuration
DEBUG_MODE = os.getenv('RESEARCHER_DEBUG', 'false').lower() == 'true'

def debug_log(message: str, data: Any = None) -> None:
    """Log debug information if debug mode is enabled."""
    if DEBUG_MODE:
        if data:
            logger.debug(f"{message}: {json.dumps(data, indent=2)}")
        else:
            logger.debug(message)

@track_performance
def generate_queries(state: ResearchState):
    """Generate, validate, and deduplicate relevant search queries based on the input topic."""
    logger.info(f"Starting query generation for topic: {state.query}")
    debug_log("Initial state", asdict(state))
    
    try:
        # Configure Gemini
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        logger.debug("Configured Gemini API")
        
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generate queries
        start_time = time.time()
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1024,
                "candidate_count": 1
            }
        )
        generation_time = time.time() - start_time
        logger.info(f"Query generation completed in {generation_time:.2f} seconds")
        
        # Extract and process queries
        queries = [line.strip() for line in response.text.split('\n') 
                  if line.strip().startswith('Query:')]
        debug_log("Generated queries", queries)
        
        # Update state
        state.documents = queries
        state = update_research_state(state, {
            'status': {
                'queries_generated': True,
                'generation_time': generation_time
            }
        })
        
        # Validate and deduplicate
        state = validate_queries(state)
        state = deduplicate_queries(state)
        
        if not validate_state_consistency(state):
            logger.error("State validation failed after query generation")
            raise ValueError("Invalid state after query generation")
            
        logger.info(f"Successfully generated {len(state.documents)} unique queries")
        debug_log("Final state", asdict(state))
        
        return state
        
    except Exception as e:
        logger.error(f"Error in query generation: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Attempt recovery
        logger.info("Attempting state recovery")
        recovered_state = load_state()
        if recovered_state:
            logger.info("Successfully recovered state")
            return recovered_state
            
        logger.warning("State recovery failed, returning original state")
        return state


def retrieve_documents(state: ResearchState, search_method="deep_research"):
    """
    Retrieve documents using either DeepResearch, Tavily or Gemini Grounding
    Args:
        state: ResearchState object
        search_method: String indicating which search method to use 
                      ("deep_research", "tavily", or "grounding")
    """
    search_methods = {
        "deep_research": retrieve_with_deep_research,
        "tavily": retrieve_with_tavily,
        "grounding": retrieve_with_grounding
    }
    
    return search_methods.get(search_method, retrieve_with_deep_research)(state)


def retrieve_with_deep_research(state: ResearchState):
    """Use Gemini Deep Research for comprehensive research"""
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Create research plan
        plan_prompt = f"""Create a detailed research plan for: {state.query}
        Break it down into specific sub-topics to investigate."""
        
        plan_response = model.generate_content(plan_prompt)
        research_plan = plan_response.text
        
        # Execute deep research with multiple iterations
        research_prompt = f"""Conduct comprehensive research on: {state.query}
        Research Plan: {research_plan}
        
        Please:
        1. Search and analyze information from multiple sources
        2. Cross-reference findings
        3. Provide a detailed report with citations
        4. Include key insights and trends
        """
        
        response = model.generate_content(
            research_prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 8192,
            }
        )
        
        state.documents.extend([
            f"Research Plan: {research_plan}",
            f"Deep Research Findings: {response.text}"
        ])
        
    except Exception as e:
        state.documents.append(f"Error in Deep Research: {str(e)}")
        return retrieve_with_grounding(state)
    
    return state


def retrieve_with_tavily(state: ResearchState):
    """Use Tavily for document retrieval"""
    try:
        tavily = TavilyClient(api_key=os.getenv("tvly- cRsiaqwLS33cIFP4yHbthwLXiVUJe9 9n"))
        
        search_result = tavily.search(
            query=state.query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
            include_images=False
        )
        
        if search_result.get('results'):
            for result in search_result['results']:
                state.documents.extend([
                    f"Title: {result.get('title', 'No title')}",
                    f"Content: {result.get('content', 'No content')}",
                    f"URL: {result.get('url', 'No URL')}\n"
                ])
        
        if search_result.get('answer'):
            state.documents.append(f"Tavily Summary: {search_result['answer']}")
            
    except Exception as e:
        state.documents.append(f"Error in Tavily search: {str(e)}")
        return retrieve_with_grounding(state)
    
    return state


def retrieve_with_grounding(state: ResearchState):
    """Use Gemini with Google Search grounding for document retrieval"""
    model = genai.GenerativeModel(
        'gemini-2.0-flash-exp',
        tools={"google_search_retrieval": {}} 
    )
    
    response = model.generate_content(
        f"Research and provide detailed information about: {state.query}",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 2048
        }
    )
    
    if hasattr(response.candidates[0], 'grounding_metadata'):
        metadata = response.candidates[0].grounding_metadata
        state.documents.extend([
            f"Retrieved from Google Search: {response.text}",
            f"Sources: {metadata}"
        ])
    else:
        state.documents.append(f"Retrieved: {response.text}")
        
    return state


@track_performance
def validate_queries(state: ResearchState) -> ResearchState:
    """Validate the quality and relevance of generated search queries."""
    logger.info("Starting query validation")
    debug_log("Queries to validate", state.documents)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        validated_queries = []
        
        for query in state.documents:
            if not query.startswith('Query:'):
                continue
                
            start_time = time.time()
            clean_query = query.replace('Query:', '').strip()
            
            logger.debug(f"Validating query: {clean_query}")
            
            response = model.generate_content(
                validation_prompt.format(query=clean_query),
                generation_config={"temperature": 0.3}
            )
            
            validation_time = time.time() - start_time
            logger.debug(f"Validation completed in {validation_time:.2f} seconds")
            
            # Process validation results
            validation_result = process_validation_response(response.text)
            debug_log("Validation result", validation_result)
            
            if validation_result['score'] >= 7:
                validated_queries.append(validation_result)
                
        logger.info(f"Validated {len(validated_queries)} queries out of {len(state.documents)}")
        
        # Update state with validated queries
        state.documents = [format_validated_query(q) for q in validated_queries]
        debug_log("Final validated queries", state.documents)
        
        return state
        
    except Exception as e:
        logger.error(f"Error in query validation: {str(e)}")
        logger.error(traceback.format_exc())
        state.documents.append(f"Error in query validation: {str(e)}")
        return state

def process_validation_response(response_text: str) -> Dict:
    """Process and structure the validation response."""
    try:
        lines = response_text.split('\n')
        score = int(next((line.replace('SCORE:', '').strip() 
                         for line in lines if line.startswith('SCORE:')), '0'))
        feedback = next((line.replace('FEEDBACK:', '').strip() 
                        for line in lines if line.startswith('FEEDBACK:')), '')
        
        return {
            'score': score,
            'feedback': feedback
        }
    except Exception as e:
        logger.error(f"Error processing validation response: {e}")
        return {'score': 0, 'feedback': 'Error processing validation'}

def format_validated_query(validation_result: Dict) -> str:
    """Format a validated query with its metadata."""
    return f"Query: {validation_result['query']} [Score: {validation_result['score']}, Feedback: {validation_result['feedback']}]"

def deduplicate_queries(state: ResearchState) -> ResearchState:
    """Remove duplicate and semantically similar queries from the state.
    
    Args:
        state: ResearchState object containing queries
        
    Returns:
        Updated state with deduplicated queries
    """
    try:
        # Extract queries and their metadata
        query_data = []
        for doc in state.documents:
            if doc.startswith('Query:'):
                # Extract query and metadata if present
                parts = doc.split('[', 1)
                query = parts[0].replace('Query:', '').strip()
                metadata = f"[{parts[1]}" if len(parts) > 1 else ""
                query_data.append({"query": query, "metadata": metadata})

        # Configure Gemini for similarity checking
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        unique_queries = []
        
        for i, current in enumerate(query_data):
            is_duplicate = False
            
            # Skip if already processed
            if any(current["query"] == uq["query"] for uq in unique_queries):
                continue
                
            # Compare with remaining queries
            for other in query_data[i+1:]:
                similarity_prompt = f"""Compare these two search queries and determine if they are semantically similar or would likely return very similar results.
                Query 1: {current["query"]}
                Query 2: {other["query"]}
                
                Return only YES if they are similar, or NO if they are distinct."""
                
                response = model.generate_content(
                    similarity_prompt,
                    generation_config={"temperature": 0.1}
                )
                
                if response.text.strip().upper() == "YES":
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_queries.append(current)
        
        # Update state with deduplicated queries
        state.documents = [f"Query: {q['query']}{q['metadata']}" for q in unique_queries]
        
        # Add deduplication metadata
        state.documents.append(
            f"Deduplication: Reduced from {len(query_data)} to {len(unique_queries)} unique queries"
        )
        
    except Exception as e:
        state.documents.append(f"Error in query deduplication: {str(e)}")
    
    return state


# State Schema Definition
RESEARCH_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "documents": {"type": "array", "items": {"type": "string"}},
        "status": {
            "type": "object",
            "properties": {
                "queries_generated": {"type": "boolean"},
                "queries_validated": {"type": "boolean"},
                "queries_deduplicated": {"type": "boolean"},
                "documents_retrieved": {"type": "boolean"},
                "last_updated": {"type": "string", "format": "date-time"},
                "processed_sources": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "completed_sections": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "error_log": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["queries_generated", "last_updated"]
        }
    },
    "required": ["query", "documents", "status"]
}

def update_research_state(state: ResearchState, updates: Dict) -> ResearchState:
    """Update the research state with new information and validate changes.
    
    Args:
        state: Current ResearchState object
        updates: Dictionary containing state updates
        
    Returns:
        Updated and validated ResearchState
    """
    try:
        # Convert current state to dict for updating
        state_dict = asdict(state)
        
        # Initialize status if not present
        if 'status' not in state_dict:
            state_dict['status'] = {
                'queries_generated': False,
                'queries_validated': False,
                'queries_deduplicated': False,
                'documents_retrieved': False,
                'last_updated': datetime.now().isoformat(),
                'processed_sources': [],
                'completed_sections': [],
                'error_log': []
            }
        
        # Update state with new information
        state_dict.update(updates)
        state_dict['status']['last_updated'] = datetime.now().isoformat()
        
        # Validate updated state against schema
        jsonschema.validate(instance=state_dict, schema=RESEARCH_STATE_SCHEMA)
        
        # Create new state object with updates
        updated_state = ResearchState(
            query=state_dict['query'],
            documents=state_dict['documents']
        )
        updated_state.status = state_dict['status']
        
        # Persist state to disk
        save_state(updated_state)
        
        return updated_state
        
    except Exception as e:
        logging.error(f"Error updating research state: {str(e)}")
        state.status['error_log'].append(f"State update error: {str(e)}")
        return state

def save_state(state: ResearchState, backup: bool = True) -> None:
    """Persist research state to disk with optional backup.
    
    Args:
        state: ResearchState object to persist
        backup: Whether to create a backup copy
    """
    state_dir = Path("./state")
    state_dir.mkdir(exist_ok=True)
    
    # Main state file
    state_file = state_dir / "research_state.pkl"
    
    try:
        # Create backup if requested
        if backup and state_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = state_dir / f"research_state_backup_{timestamp}.pkl"
            with open(state_file, 'rb') as f:
                backup_data = f.read()
            with open(backup_file, 'wb') as f:
                f.write(backup_data)
        
        # Save current state
        with open(state_file, 'wb') as f:
            pickle.dump(state, f)
            
    except Exception as e:
        logging.error(f"Error saving state: {str(e)}")
        raise

def load_state() -> Optional[ResearchState]:
    """Recover research state from disk or backup.
    
    Returns:
        Recovered ResearchState or None if recovery fails
    """
    state_dir = Path("./state")
    state_file = state_dir / "research_state.pkl"
    
    try:
        # Try loading main state file
        if state_file.exists():
            with open(state_file, 'rb') as f:
                state = pickle.load(f)
            return state
            
        # If main file fails, try latest backup
        backup_files = sorted(state_dir.glob("research_state_backup_*.pkl"))
        if backup_files:
            latest_backup = backup_files[-1]
            with open(latest_backup, 'rb') as f:
                state = pickle.load(f)
            logging.warning(f"Recovered state from backup: {latest_backup}")
            return state
            
    except Exception as e:
        logging.error(f"Error loading state: {str(e)}")
    
    return None

def validate_state_consistency(state: ResearchState) -> bool:
    """Validate the consistency of the research state.
    
    Args:
        state: ResearchState object to validate
        
    Returns:
        Boolean indicating if state is valid
    """
    try:
        # Convert state to dict for validation
        state_dict = asdict(state)
        
        # Validate against schema
        jsonschema.validate(instance=state_dict, schema=RESEARCH_STATE_SCHEMA)
        
        # Additional consistency checks
        if state.status['queries_validated'] and not state.status['queries_generated']:
            raise ValueError("Queries cannot be validated before generation")
            
        if state.status['documents_retrieved'] and not state.status['queries_validated']:
            raise ValueError("Documents cannot be retrieved before query validation")
            
        return True
        
    except Exception as e:
        logging.error(f"State consistency error: {str(e)}")
        return False

with open('metrics/metrics_20240321.jsonl') as f:
    metrics = [json.loads(line) for line in f]
