
REPORT_PLAN_PROMPT = """
You are an expert report planner. Your task is to create a structure based on the topic: {topic}.
Include sections with descriptions and indicate which sections require research.
"""

# Planning prompts
REPORT_PLANNER_QUERY_WRITER = """You are an expert technical writer, planning a comprehensive report.

The report will focus on: {topic}

The report structure should follow:
{report_organization}

Generate {number_of_queries} search queries that will help gather comprehensive information for planning the report sections.

Each query should:
1. Be specific to the topic
2. Help fulfill the report structure requirements
3. Target authoritative sources
4. Include technical terms where appropriate"""

REPORT_PLANNER_INSTRUCTIONS = """You are an expert technical writer creating a report outline.

Topic: {topic}

Report Organization: 
{report_organization}

Use this context to inform the section planning:
{context}

For each section, provide:
1. Name - Clear section title
2. Description - Overview of topics covered
3. Research - Whether web research is needed (true/false)
4. Content - Leave blank for now

Consider carefully which sections need research vs which can synthesize information from other sections."""

# Research prompts
RESEARCH_QUERY_WRITER = """Generate targeted search queries for the section: {section_topic}

Create {number_of_queries} queries that:
1. Focus on specific technical aspects
2. Target recent information (include year markers)
3. Look for implementation examples
4. Search for comparisons with alternatives
5. Find authoritative sources"""

# Writing prompts
SECTION_WRITER = """Write a section for a technical report.

Section Topic: {section_topic}
Section Description: {section_description}

Use these guidelines:
1. Be technically precise
2. Include specific examples
3. Cite sources appropriately
4. Use clear structure
5. Focus on key insights

Available source material:
{context}"""