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
4. Include technical terms where appropriate

Make the query specific enough to find high-quality, relevant sources while covering the breadth needed for the report structure."""

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

Consider which sections require web research. For example, introduction and conclusion will not require research because they will distill information from other parts of the report."""

# Research prompts
RESEARCH_QUERY_WRITER = """Your goal is to generate targeted web search queries that will gather comprehensive information for writing a technical report section.

Topic for this section:
{section_topic}

When generating {number_of_queries} search queries, ensure they:
1. Cover different aspects of the topic (e.g., core features, real-world applications, technical architecture)
2. Include specific technical terms related to the topic
3. Target recent information by including year markers where relevant (e.g., "2024")
4. Look for comparisons or differentiators from similar technologies/approaches
5. Search for both official documentation and practical implementation examples

Your queries should be:
- Specific enough to avoid generic results
- Technical enough to capture detailed implementation information
- Diverse enough to cover all aspects of the section plan
- Focused on authoritative sources (documentation, technical blogs, academic papers)"""

# Writing prompts
# SECTION_WRITER = """Write a section for a technical report.
#
# Section Topic: {section_topic}
# Section Description: {section_description}
#
# Use these guidelines:
# 1. Be technically precise
# 2. Include specific examples
# 3. Cite sources appropriately
# 4. Use clear structure
# 5. Focus on key insights
#
# Available source material:
# {context}"""

SECTION_WRITER = """You are an expert technical writer crafting one section of a technical report.

Topic for this section:
{section_topic}

Guidelines for writing:

1. Technical Accuracy:
- Include specific version numbers
- Reference concrete metrics/benchmarks
- Cite official documentation
- Use technical terminology precisely

2. Length and Style:
- Strict 150-200 word limit
- No marketing language
- Technical focus
- Write in simple, clear language
- Start with your most important insight in **bold**
- Use short paragraphs (2-3 sentences max)

3. Structure:
- Use ## for section title (Markdown format)
- Only use ONE structural element IF it helps clarify your point:
  * Either a focused table comparing 2-3 key items (using Markdown table syntax)
  * Or a short list (3-5 items) using proper Markdown list syntax:
    - Use `*` or `-` for unordered lists
    - Use `1.` for ordered lists
    - Ensure proper indentation and spacing
- End with ### Sources that references the below source material formatted as:
  * List each source with title, date, and URL
  * Format: `- Title : URL`

3. Writing Approach:
- Include at least one specific example or case study
- Use concrete details over general statements
- Make every word count
- No preamble prior to creating the section content
- Focus on your single most important point

4. Use this source material to help write the section:
{context}

5. Quality Checks:
- Exactly 150-200 words (excluding title and sources)
- Careful use of only ONE structural element (table or list) and only if it helps clarify your point
- One specific example / case study
- Starts with bold insight
- No preamble prior to creating the section content
- Sources cited at end"""


FINAL_SECTION_WRITER = """You are an expert technical writer tasked with compiling a comprehensive, professional, and structured report about an AI tool or agent.

Section to write: 
{section_topic}

Available report content:
{context}

1. Section-Specific Approach:

For Introduction:
- Focus on answer initial questions, use the following as a guide
  - What is the main category of the solution? You should identify whether it is a development tool, platform or a final product
  - What level of implementation does it have? Here we must differentiate between low, medium or high level
- Use # for report title (Markdown format)
- up to 400 word limit
- Write in simple and clear language
- Focus on the core motivation for the report in 1-2 paragraphs
- Use a clear narrative arc to introduce the report
- Include NO structural elements (no lists or tables)
- No sources section needed

For Body:
- Focus on answer fundamental questions, use the following as a guide
  - What does it do? This is intended to clarify the capabilities of the solution
    - What is the problem statement?
    - Who is the primary user type?
    - What are the key capabilities?
    - What types of input/output does it support?
    - What is the scope of functionality?
  - How does it work? Here the focus is on understanding the technical architecture, which leads to the question
    - What is the core architecture pattern?
    - How is the agent model organized?
    - What are the key technical components?
    - What are the external dependencies?
    - How does interaction between components occur?
  - When should you use it? This question asks about practical scenarios
    - What are the specific use cases?
    - What technical prerequisites are needed?
    - What is the operational scale?
    - What are the unsuitable scenarios?
    - How does the solution compare to alternatives?
  - How is it implemented? Examining implementation involves
    - What is the basic setup process?
    - What integration methods will be needed?
    - What are the resource requirements?
    - What is the estimated implementation timeline?
    - What type of maintenance will be required?
  - What makes it unique? Here you need to identify what sets the solution apart in the market
    - What are the key differentiators?
    - What competitive advantages do you have?
    - What is your market position?
    - How innovative are you really?
    - What is your future potential?
  - What is the pricing and evaluation structure? In this section, it is required to establish
    - What is the pricing and licensing structure?
    - What are the associated costs?
    - What is the ultimate business value of the solution?

- Use several sub-sections and mark then with ## for report title (Markdown format)
- up to 1200 word limit for each sub-section
- Write in simple and clear language
- Include NO structural elements (no lists or tables)
- No sources section needed

For Conclusion/Summary:
- Use ## for section title (Markdown format)
- up to 400 word limit
- End with specific next steps or implications
- No sources section needed

3. Writing Approach:
- Use concrete details over general statements
- Make every word count
- Focus on your single most important point

4. Quality Checks:
- For introduction: up to 400 word limit, # for report title, no structural elements, no sources section
- For body: up to 1200 word limit for sub-section, ## for sub-section title, only ONE structural element at most, no sources section
- For conclusion: up to 400 word limit, ## for section title, only ONE structural element at most, no sources section
- Markdown format
- Do not include word count or any preamble in your response"""

FINAL_REPORT_FORMAT = """You are an expert technical writer. Your task is to write a final report, addressing each specific section one at a time. Ensure the report strictly follows the guidelines and sections below, with a focus on coherence, readability, and grammatical correctness.

**Important:** 
- Avoid mentioning ideas or facts that have been previously discussed in the report.
- For the Introduction and Conclusions sections, write **only one paragraph.** If the information does not contribute to the section, don't write it.
- Introduction will always be the first section and Conclusions will always be the first section.  

## Report Structure and Guidelines:  
### **Base Section (Mandatory for All Agents):**  
{report_organization}  

### **Specific Guidelines for Agent Types:**  
- For **Frameworks (e.g., LangChain, Haystack, Rasa):**  
  - Detailed installation process and dependencies (versions, libraries, recommended environments).  
  - Explanation of internal architecture (e.g., chains, memories, and tools).  
  - Provide **well-tested examples of reproducible code snippets** to demonstrate usage.  
  - Include steps for integrating with LLMs or external services (e.g., OpenAI, Llama2).  
- For **Low-Code/No-Code Platforms (e.g., Zapier with AI, Bubble):**  
  - Cover onboarding instructions (e.g., creating accounts, activating plugins).  
  - Specify concrete **limitations or constraints** of the visual environment (what can/cannot be done without coding).  
  - Outline subscription plans (e.g., Free, Pro) and highlight onboarding differences.  
- For **Products with Internal Agents (SaaS):**  
  - Detailed configuration steps for internal AI setups (e.g., prompts or model parameters).  
  - Examples of functional testing (e.g., internal chatbots, automated analysis).  

### **Writing Standards:**  
- **Deep Analysis:** Avoid repeated or surface-level statements; dig into functionality, usability, and real implications.  
- **Objective Evaluation:** Strive for balance when presenting strengths and limitations; underline them clearly.  
- **Transparency in Missing Data:** Highlight any gaps in provided data and their possible impact on the report.  
- **Practical Examples:** Emphasize real-world examples, and ensure practicality in the report suggestions.  
- **Clarity and Conciseness:** Remain clear and professional, avoiding jargon unless critical. Limit to **400 words** for section unless additional length is necessary for technical clarity. Explain briefly if this happens.

 ### Provided Context:
 {all_sections}

**Note:** Ensure the report adheres to these instructions precisely while maintaining a professional tone in Spanish. Maximum length is 400 words per section unless otherwise justified.
"""

# **Report Section: {section_name}**
# {section_content}  

# ### Current Partial Report:  
# {partial_final_report}  
