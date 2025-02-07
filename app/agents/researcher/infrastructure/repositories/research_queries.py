class ResearchQueries:
    """SQL queries for research repository"""
    
    CREATE_RESEARCH_STATE_TABLE = """
        CREATE TABLE IF NOT EXISTS research_state (
            section_id TEXT PRIMARY KEY,
            state_json TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """
    
    CREATE_ERROR_LOG_TABLE = """
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id TEXT,
            error_message TEXT,
            timestamp TIMESTAMP
        )
    """
    
    CREATE_METRICS_TABLE = """
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metrics_json TEXT,
            timestamp TIMESTAMP
        )
    """
    
    INSERT_METRICS = """
        INSERT INTO performance_metrics (metrics_json, timestamp)
        VALUES (?, CURRENT_TIMESTAMP)
    """ 