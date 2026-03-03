"""
Skill Extraction Service - Extract raw skills from JD text.

Uses rule-based keyword extraction to identify:
- Required skills (must have, required, necessary)
- Optional skills (nice to have, preferred, bonus)

No normalization here - that happens in the LLM normalization step.
"""
import re
import logging
from typing import List, Dict, Tuple, Set

logger = logging.getLogger(__name__)

# ============================================================================
# KEYWORD PATTERNS FOR SKILL EXTRACTION
# ============================================================================

# Patterns that indicate required skills
REQUIRED_PATTERNS = [
    r"(?i)required\s*(?:skills|qualifications|experience)?[\s:]*",
    r"(?i)must\s+have[\s:]*",
    r"(?i)necessary\s+skills?[\s:]*",
    r"(?i)essential\s+skills?[\s:]*",
    r"(?i)minimum\s+(?:requirements|qualifications)[\s:]*",
    r"(?i)you\s+will\s+need[\s:]*",
    r"(?i)requirements?[\s:]*",
    r"(?i)mandatory[\s:]*",
]

# Patterns that indicate optional/preferred skills
OPTIONAL_PATTERNS = [
    r"(?i)nice\s+to\s+have[\s:]*",
    r"(?i)preferred\s*(?:skills|qualifications)?[\s:]*",
    r"(?i)bonus\s+(?:points?|skills?)?[\s:]*",
    r"(?i)plus[\s:]*",
    r"(?i)desired[\s:]*",
    r"(?i)advantageous[\s:]*",
    r"(?i)additional\s+skills?[\s:]*",
]

# Patterns to identify individual skill items
SKILL_ITEM_PATTERNS = [
    r"[-•·]\s*(.+?)(?=\n|$)",  # Bullet points
    r"\d+[\.\)]\s*(.+?)(?=\n|$)",  # Numbered lists
    r"(?:^|\n)\s*([A-Z][a-zA-Z0-9\+\#\.]+(?:\s+[A-Za-z0-9\+\#\.]+)*)",  # Capitalized terms
]

# Common technology/skill keywords to match
TECH_KEYWORDS = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust",
    "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "bash", "sql",
    
    # Frameworks
    "react", "angular", "vue", "django", "flask", "spring", "node", "express",
    "fastapi", "rails", "laravel", ".net", "pytorch", "tensorflow", "keras",
    "scikit-learn", "pandas", "numpy", "spark", "hadoop",
    
    # Databases
    "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "neo4j",
    "oracle", "sql server", "dynamodb", "cassandra", "sqlite",
    
    # Cloud/DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "terraform",
    "ansible", "ci/cd", "git", "linux", "unix",
    
    # AI/ML
    "machine learning", "deep learning", "nlp", "computer vision", "neural networks",
    "transformers", "bert", "gpt", "llm", "rag", "langchain", "llama",
    
    # Data
    "data science", "data engineering", "etl", "data pipeline", "data pipelines",
    "analytics", "data analytics", "predictive analytics", "business intelligence",
    "tableau", "power bi", "looker", "airflow", "dbt",
    
    # Other
    "agile", "scrum", "microservices", "rest api", "graphql", "kafka",
    "rabbitmq", "oauth", "jwt", "security", "testing", "tdd",
}

# Generic terms to filter out (too broad to be useful skills)
GENERIC_TERMS = {
    "business", "communication", "design", "development", "engineering",
    "experience", "information", "information technology", "it", "management",
    "operations", "planning", "problem solving", "products", "projects",
    "quality", "research", "strategy", "systems", "team", "teamwork",
    "technical", "technology", "work", "communication skills", "leadership",
    "analysis", "the", "to", "join", "our", "team", "with", "for", "and",
}


class SkillExtractService:
    """
    Extracts raw skills from Job Description text.
    
    Strategy:
    1. Identify sections (required vs optional)
    2. Extract bullet points and list items
    3. Match against known tech keywords
    4. Return categorized raw skill lists
    """
    
    def __init__(self, kg_skill_list: Set[str] = None):
        """
        Initialize extractor.
        
        Args:
            kg_skill_list: Optional set of canonical skills from KG for matching
        """
        self.kg_skills = kg_skill_list or set()
        self.tech_keywords = TECH_KEYWORDS.copy()
        if kg_skill_list:
            self.tech_keywords.update(s.lower() for s in kg_skill_list)
        logger.info(f"SkillExtractService initialized with {len(self.tech_keywords)} keywords")
    
    def extract_skills(self, jd_text: str) -> Dict[str, List[str]]:
        """
        Extract raw skills from JD text.
        
        Args:
            jd_text: Cleaned job description text
            
        Returns:
            {
                "raw_required_skills": [...],
                "raw_optional_skills": [],
                "job_title": "...",
                "extraction_metadata": {...}
            }
        """
        logger.info("Extracting skills from JD text")
        
        if not jd_text:
            return {
                "raw_required_skills": [],
                "raw_optional_skills": [],
                "job_title": "",
                "extraction_metadata": {"error": "Empty input"}
            }
        
        result = {
            "raw_required_skills": [],
            "raw_optional_skills": [],
            "job_title": self._extract_job_title(jd_text),
            "extraction_metadata": {
                "text_length": len(jd_text),
                "method": "hybrid"
            }
        }
        
        # Step 1: Split into sections
        sections = self._identify_sections(jd_text)
        
        # Step 2: Extract from required sections
        for section_text in sections.get("required", []):
            skills = self._extract_skills_from_section(section_text)
            result["raw_required_skills"].extend(skills)
        
        # Step 3: Extract from optional sections
        for section_text in sections.get("optional", []):
            skills = self._extract_skills_from_section(section_text)
            result["raw_optional_skills"].extend(skills)
        
        # Step 4: Extract from generic sections
        for section_text in sections.get("general", []):
            skills = self._extract_skills_from_section(section_text)
            # Default to required if in main body
            result["raw_required_skills"].extend(skills)
        
        # Step 5: Fallback - keyword matching on full text
        if not result["raw_required_skills"]:
            logger.warning("No skills found via sections, using keyword fallback")
            keyword_skills = self._keyword_match(jd_text)
            result["raw_required_skills"] = keyword_skills
            result["extraction_metadata"]["method"] = "keyword_fallback"
        
        # Deduplicate
        result["raw_required_skills"] = list(dict.fromkeys(result["raw_required_skills"]))
        result["raw_optional_skills"] = list(dict.fromkeys(result["raw_optional_skills"]))
        
        # Remove any required skills that appear in optional
        optional_set = set(s.lower() for s in result["raw_optional_skills"])
        result["raw_required_skills"] = [
            s for s in result["raw_required_skills"] 
            if s.lower() not in optional_set
        ]
        
        result["extraction_metadata"]["required_count"] = len(result["raw_required_skills"])
        result["extraction_metadata"]["optional_count"] = len(result["raw_optional_skills"])
        
        logger.info(
            f"Extracted {len(result['raw_required_skills'])} required, "
            f"{len(result['raw_optional_skills'])} optional skills"
        )
        
        return result
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title from beginning of JD."""
        # Look for common title patterns
        patterns = [
            r"(?i)(?:job\s+)?title[\s:]+(.+?)(?:\n|$)",
            r"(?i)position[\s:]+(.+?)(?:\n|$)",
            r"(?i)^(.+?(?:engineer|developer|scientist|analyst|manager|architect|lead|specialist|consultant).+?)(?:\n|$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:500])
            if match:
                title = match.group(1).strip()
                if len(title) < 100:  # Sanity check
                    return title
        
        # Fallback: first line
        first_line = text.split('\n')[0].strip()
        if len(first_line) < 100:
            return first_line
        return ""
    
    def _identify_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Split text into required, optional, and general sections.
        
        Returns:
            {"required": [...], "optional": [...], "general": [...]}
        """
        sections = {"required": [], "optional": [], "general": []}
        
        # Find section boundaries
        lines = text.split('\n')
        current_section = "general"
        current_text = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Check for section headers
            is_required = any(re.search(p, line) for p in REQUIRED_PATTERNS)
            is_optional = any(re.search(p, line) for p in OPTIONAL_PATTERNS)
            
            if is_required:
                # Save previous section
                if current_text:
                    sections[current_section].append('\n'.join(current_text))
                current_section = "required"
                current_text = [line]
            elif is_optional:
                if current_text:
                    sections[current_section].append('\n'.join(current_text))
                current_section = "optional"
                current_text = [line]
            else:
                current_text.append(line)
        
        # Save last section
        if current_text:
            sections[current_section].append('\n'.join(current_text))
        
        return sections
    
    def _extract_skills_from_section(self, section_text: str) -> List[str]:
        """Extract skill names from a section of text."""
        skills = []
        
        # Method 1: Bullet points and list items
        for pattern in SKILL_ITEM_PATTERNS:
            matches = re.findall(pattern, section_text)
            for match in matches:
                skill = self._clean_skill_text(match)
                if skill and self._is_valid_skill(skill):
                    skills.append(skill)
        
        # Method 2: Keyword matching within the section
        section_lower = section_text.lower()
        for keyword in self.tech_keywords:
            # Word boundary matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, section_lower, re.IGNORECASE):
                # Format skill name properly
                formatted_skill = self._format_skill_name(keyword)
                if self._is_valid_skill(formatted_skill):
                    skills.append(formatted_skill)
        
        return skills
    
    def _keyword_match(self, text: str) -> List[str]:
        """Fallback: match known keywords in full text."""
        skills = []
        text_lower = text.lower()
        
        for keyword in self.tech_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                formatted_skill = self._format_skill_name(keyword)
                if self._is_valid_skill(formatted_skill):
                    skills.append(formatted_skill)
        
        return skills
    
    def _clean_skill_text(self, text: str) -> str:
        """Clean extracted skill text."""
        if not text:
            return ""
        
        # Remove common noise
        cleaned = text.strip()
        cleaned = re.sub(r'^[\s\-•·\d\.\)]+', '', cleaned)  # Remove leading markers
        cleaned = re.sub(r'[\s\-•·]+$', '', cleaned)  # Remove trailing markers
        
        # Remove years of experience patterns
        cleaned = re.sub(r'\d+\+?\s*(?:years?|yrs?)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove "experience with/in" and similar prefixes
        cleaned = re.sub(r'(?i)^(?:experience\s+(?:with|in)\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:knowledge\s+of\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:familiarity\s+with\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:proficiency\s+in\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:strong\s+(?:knowledge|understanding|skills?)\s+(?:of|in|with)\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:hands?-on\s+(?:experience\s+)?(?:with|in)\s+)', '', cleaned)
        
        # Remove common sentence starters that got captured
        cleaned = re.sub(r'(?i)^(?:we\s+are\s+looking\s+for\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:calling\s+)', '', cleaned)
        cleaned = re.sub(r'(?i)^(?:to\s+join\s+)', '', cleaned)
        
        # Take only the first skill if comma-separated
        if ',' in cleaned:
            cleaned = cleaned.split(',')[0].strip()
        
        # Trim to reasonable length (skills shouldn't be full sentences)
        if len(cleaned) > 40:
            # Take first meaningful phrase
            parts = re.split(r'[,;:]', cleaned)
            if parts:
                cleaned = parts[0].strip()
        
        return cleaned.strip()
    
    def _is_valid_skill(self, skill: str) -> bool:
        """Check if extracted text is a valid skill."""
        if not skill or len(skill) < 2:
            return False
        
        # Too long (likely a sentence or paragraph)
        if len(skill) > 40:
            return False
        
        # Check if it's a generic term
        skill_lower = skill.lower().strip()
        if skill_lower in GENERIC_TERMS:
            return False
        
        # Contains too many words (likely a sentence)
        word_count = len(skill.split())
        if word_count > 5:
            return False
        
        # Contains common sentence patterns or non-skill phrases
        sentence_patterns = [
            r'\bto\s+join\b',
            r'\bwe\s+are\b',
            r'\bwe\s+want\b',
            r'\bwe\s+expect\b',
            r'\blooking\s+for\b',
            r'\bcalling\b',
            r'\bwith\s+hands\b',
            r'\bin\s+order\s+to\b',
            r'\bwill\s+be\b',
            r'\bhave\s+good\b',
            r'\bpossess\s+a\b',
            r'\byou\s+to\b',
            r'\byou\s+will\b',
            r'\bidentify$',  # Just the word "Identify" alone
            r'\bassemble$',  # Just the word "Assemble" alone
            r'\bbuild$',     # Just the word "Build" alone
            r'\bwork$',      # Just the word "Work" alone
            r'\bmonitor$',   # Just the word "Monitor" alone
        ]
        for pattern in sentence_patterns:
            if re.search(pattern, skill_lower):
                return False
        
        # Single generic action verbs (not skills)
        generic_verbs = {'identify', 'assemble', 'build', 'monitor', 'work', 
                        'develop', 'implement', 'ensure', 'gather', 'provide'}
        if skill_lower in generic_verbs:
            return False
        
        # Must start with alphanumeric (not punctuation)
        if not skill[0].isalnum():
            return False
        
        # Check if it's mostly just verbs (common sentence starters)
        first_word = skill_lower.split()[0] if skill.split() else ''
        starter_verbs = {'have', 'possess', 'we', 'you', 'identify', 'build',
                        'work', 'develop', 'ensure', 'monitor', 'assemble'}
        if first_word in starter_verbs:
            return False
        
        return True
    
    def _format_skill_name(self, keyword: str) -> str:
        """Format skill name for consistency."""
        # Special cases for proper casing
        special_cases = {
            'sql': 'SQL',
            'nosql': 'NoSQL',
            'mysql': 'MySQL',
            'postgresql': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'c++': 'C++',
            'c#': 'C#',
            'r': 'R',
            'aws': 'AWS',
            'gcp': 'GCP',
            'ci/cd': 'CI/CD',
            'rest api': 'REST API',
            'graphql': 'GraphQL',
            'neo4j': 'Neo4j',
            'pytorch': 'PyTorch',
            'tensorflow': 'TensorFlow',
            'scikit-learn': 'Scikit-Learn',
            'numpy': 'NumPy',
            'pandas': 'Pandas',
            'power bi': 'Power BI',
            'tableau': 'Tableau',
            'docker': 'Docker',
            'kubernetes': 'Kubernetes',
            'jenkins': 'Jenkins',
            'git': 'Git',
            'linux': 'Linux',
            'unix': 'Unix',
            'oracle': 'Oracle',
            'nlp': 'NLP',
            'llm': 'LLM',
            'gpt': 'GPT',
            'bert': 'BERT',
            'etl': 'ETL',
            'jwt': 'JWT',
            'oauth': 'OAuth',
        }
        
        keyword_lower = keyword.lower()
        if keyword_lower in special_cases:
            return special_cases[keyword_lower]
        
        # Default: title case
        return keyword.title()
    
    def load_kg_skills(self, session) -> None:
        """
        Load canonical skill names from Neo4j KG.
        
        Args:
            session: Neo4j session
        """
        logger.info("Loading canonical skills from KG")
        
        query = "MATCH (s:Skill) RETURN s.name AS name LIMIT 10000"
        result = session.run(query)
        
        self.kg_skills = {record["name"] for record in result}
        self.tech_keywords.update(s.lower() for s in self.kg_skills)
        
        logger.info(f"Loaded {len(self.kg_skills)} skills from KG")


# Module-level singleton
_extract_service = None

def get_skill_extract_service(kg_session=None) -> SkillExtractService:
    """Get or create extraction service singleton."""
    global _extract_service
    if _extract_service is None:
        _extract_service = SkillExtractService()
        if kg_session:
            _extract_service.load_kg_skills(kg_session)
    return _extract_service
