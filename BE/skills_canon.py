"""
Skill canonicalization (Layer 0).

The LLM extraction is high-recall but noisy: the same concept shows up as
'rag' / 'RAG' / 'Retrieval-Augmented Generation' / 'graphrag', and the same
skill lands in different buckets across jobs. This module collapses surface
forms into ONE canonical name and pins each canonical skill to ONE bucket, so
per-skill counts become "unique jobs that mention this concept" — the number a
human can actually trust.

Deterministic and grounded: an explicit alias map (built from the real terms in
the data) plus a few guarded family rules. Unknown terms pass through lightly
normalized and keep their data-derived bucket (majority vote, done in agg).
"""
import re

BUCKETS = ["skills_concepts", "frameworks", "methodologies", "cloud",
           "languages", "tools_platforms", "databases"]

# canonical name -> bucket (the ONE bucket this skill belongs in)
BUCKET_OF = {
    # --- skills / concepts ---
    "RAG": "skills_concepts", "LLMs": "skills_concepts", "Generative AI": "skills_concepts",
    "AI Agents": "skills_concepts", "Prompt Engineering": "skills_concepts",
    "Embeddings": "skills_concepts", "Fine-tuning": "skills_concepts", "LoRA": "skills_concepts",
    "NLP": "skills_concepts", "Machine Learning": "skills_concepts", "Deep Learning": "skills_concepts",
    "Computer Vision": "skills_concepts", "Semantic Search": "skills_concepts",
    "Responsible AI": "skills_concepts", "Guardrails": "skills_concepts", "Evaluation": "skills_concepts",
    "Artificial Intelligence": "skills_concepts", "Tool Use": "skills_concepts",
    "Model Context Protocol (MCP)": "skills_concepts", "Vector Search": "skills_concepts",
    "Recommendation Systems": "skills_concepts", "Data Science": "skills_concepts",
    "Reinforcement Learning": "skills_concepts", "Knowledge Graphs": "skills_concepts",
    "REST APIs": "skills_concepts", "API Development": "skills_concepts",
    # --- frameworks ---
    "LangChain": "frameworks", "LangGraph": "frameworks", "LlamaIndex": "frameworks",
    "FastAPI": "frameworks", "Django": "frameworks", "Django REST Framework": "frameworks",
    "Flask": "frameworks", "PyTorch": "frameworks", "TensorFlow": "frameworks",
    "Hugging Face": "frameworks", "Pandas": "frameworks", "NumPy": "frameworks",
    "Streamlit": "frameworks", "Chainlit": "frameworks", "Gradio": "frameworks",
    "Scikit-learn": "frameworks", "CrewAI": "frameworks", "AutoGen": "frameworks",
    "Semantic Kernel": "frameworks", "Keras": "frameworks", "OpenCV": "frameworks",
    "spaCy": "frameworks", "Transformers": "frameworks", "Sentence Transformers": "frameworks",
    # --- methodologies ---
    "CI/CD": "methodologies", "MLOps": "methodologies", "LLMOps": "methodologies",
    "Microservices": "methodologies", "Agile": "methodologies", "DevOps": "methodologies",
    "TDD": "methodologies", "System Design": "methodologies", "Data Pipelines": "methodologies",
    # --- cloud ---
    "AWS": "cloud", "Azure": "cloud", "GCP": "cloud", "AWS SageMaker": "cloud",
    "AWS Bedrock": "cloud", "Azure OpenAI": "cloud", "Vertex AI": "cloud",
    # --- languages ---
    "Python": "languages", "SQL": "languages", "JavaScript": "languages", "Java": "languages",
    "TypeScript": "languages", "C++": "languages", "Go": "languages", "HTML": "languages",
    "CSS": "languages", "R": "languages", "Scala": "languages",
    # --- tools / platforms ---
    "Docker": "tools_platforms", "Kubernetes": "tools_platforms", "Git": "tools_platforms",
    "MLflow": "tools_platforms", "Airflow": "tools_platforms", "Kafka": "tools_platforms",
    "Power BI": "tools_platforms", "Spark": "tools_platforms", "Databricks": "tools_platforms",
    "Jenkins": "tools_platforms", "Terraform": "tools_platforms",
    # --- databases / vector ---
    "PostgreSQL": "databases", "MongoDB": "databases", "Redis": "databases",
    "Pinecone": "databases", "FAISS": "databases", "ChromaDB": "databases",
    "Vector Databases": "databases", "MySQL": "databases", "Elasticsearch": "databases",
    "BigQuery": "databases", "Neo4j": "databases", "pgvector": "databases",
    "NoSQL": "databases", "Qdrant": "databases", "Weaviate": "databases",
}

# surface form (lowercased) -> canonical name
ALIASES = {}
def _alias(canon, *forms):
    ALIASES[canon.lower()] = canon
    for f in forms:
        ALIASES[f.lower()] = canon

_alias("RAG", "rag", "graphrag", "graph rag", "retrieval-augmented generation",
       "retrieval augmented generation", "retrieval-augmented generation (rag)",
       "retrieval augmented generation (rag)", "rag pipelines", "rag architecture",
       "rag architectures", "rag systems", "rag-based applications", "rag based applications",
       "retrieval augmentation generative", "rag pipeline", "agentic rag")
_alias("LLMs", "llm", "llms", "large language models", "large language models (llms)",
       "large language model", "llm-large language model", "transformer based llms",
       "llm architectures", "llm application architecture", "llm internals", "llm integrations",
       "llm integration", "ai/llm integration", "llm-powered applications")
_alias("LLMOps", "llmops", "llm orchestration", "llm deployment", "llm ops")
_alias("Generative AI", "generative ai", "genai", "gen ai", "generative artificial intelligence",
       "gen-ai", "generative a.i.")
_alias("AI Agents", "agentic ai", "ai agents", "ai agent", "agentic systems", "agentic workflows",
       "agents", "agent", "multi-agent systems", "multi agent systems", "multi-agent architectures",
       "agentic ai systems", "agentic architectures", "agent-based architectures",
       "autonomous ai agents", "intelligent agents", "agent systems", "agentic",
       "multi-agent coordination", "genai agents", "ai agent frameworks", "agentic ai frameworks",
       "llm-powered agents", "agent-based or agentic systems", "single or multi-agent workflows")
_alias("Prompt Engineering", "prompt engineering", "prompting", "prompts", "prompt optimization",
       "prompt architectures", "prompt engineering frameworks", "prompt design", "prompt flows")
_alias("Embeddings", "embeddings", "embedding models", "embedding", "text embeddings", "vector embeddings")
_alias("Fine-tuning", "fine-tuning", "finetuning", "fine tuning", "model fine-tuning",
       "supervised fine-tuning", "sft")
_alias("LoRA", "lora", "qlora", "peft", "low-rank adaptation")
_alias("NLP", "nlp", "natural language processing")
_alias("Machine Learning", "machine learning", "ml", "ai/ml", "ai ml", "aiml", "ml/ai")
_alias("Deep Learning", "deep learning", "dl", "neural networks")
_alias("Computer Vision", "computer vision", "cv", "image processing")
_alias("Semantic Search", "semantic search", "vector search", "similarity search")
_alias("Vector Search", "vector search")
_alias("Responsible AI", "responsible ai", "ai safety", "ai ethics")
_alias("Guardrails", "guardrails", "guardrail", "safety guardrails")
_alias("Evaluation", "evaluation", "evals", "eval", "llm-as-judge", "llm-as-judge patterns",
       "llm-based evaluators", "model evaluation")
_alias("Artificial Intelligence", "artificial intelligence", "ai")
_alias("Tool Use", "tool use", "tool-use", "function calling", "tool calling")
_alias("Model Context Protocol (MCP)", "mcp", "model context protocol")
_alias("Data Science", "data science", "data scientist")
_alias("Machine Learning", "regression", "classification")  # coarse — fold basic ML tasks
_alias("Recommendation Systems", "recommendation systems", "recommender systems", "recsys")
_alias("Reinforcement Learning", "reinforcement learning", "rl", "rlhf")
_alias("Knowledge Graphs", "knowledge graphs", "knowledge graph")
# frameworks
_alias("LangChain", "langchain", "lang chain")
_alias("LangGraph", "langgraph", "lang graph", "langgraph")
_alias("LlamaIndex", "llamaindex", "llama index", "llama-index")
_alias("FastAPI", "fastapi", "fast api")
_alias("Django", "django")
_alias("Django REST Framework", "django rest framework", "django rest framework (drf)", "drf")
_alias("Flask", "flask")
_alias("PyTorch", "pytorch", "torch")
_alias("TensorFlow", "tensorflow", "tf")
_alias("Hugging Face", "hugging face", "huggingface", "hugging face libraries",
       "hugging face transformers", "hf")
_alias("Transformers", "transformers")
_alias("Sentence Transformers", "sentence transformers", "sentence-transformers")
_alias("Pandas", "pandas")
_alias("NumPy", "numpy", "np")
_alias("Streamlit", "streamlit")
_alias("Chainlit", "chainlit")
_alias("Gradio", "gradio")
_alias("Scikit-learn", "scikit-learn", "sklearn", "scikit learn")
_alias("CrewAI", "crewai", "crew ai")
_alias("AutoGen", "autogen", "auto gen")
_alias("Semantic Kernel", "semantic kernel")
_alias("Keras", "keras")
_alias("OpenCV", "opencv", "open cv")
_alias("spaCy", "spacy")
# methodologies
_alias("CI/CD", "ci/cd", "ci/cd pipelines", "cicd", "continuous integration",
       "continuous integration/continuous deployment", "ci pipelines", "ci/cd pipeline")
_alias("MLOps", "mlops", "mlops workflows", "mlops mindset", "mlops frameworks", "ml ops")
_alias("Microservices", "microservices", "microservice", "microservices architecture")
_alias("Agile", "agile", "agile methodologies", "scrum")
_alias("DevOps", "devops", "dev ops")
_alias("TDD", "tdd", "test-driven development", "test driven development")
_alias("System Design", "system design")
# cloud
_alias("AWS", "aws", "amazon web services", "aws glue", "aws lambda")
_alias("AWS SageMaker", "sagemaker", "aws sagemaker", "amazon sagemaker")
_alias("AWS Bedrock", "bedrock", "aws bedrock", "amazon bedrock")
_alias("Azure", "azure", "microsoft azure", "azure cloud")
_alias("Azure OpenAI", "azure openai", "azure open ai")
_alias("GCP", "gcp", "google cloud", "google cloud platform", "gcp and big query")
_alias("Vertex AI", "vertex ai", "vertexai", "gcp vertex ai")
# languages
_alias("REST APIs", "rest apis", "restful apis", "rest api", "restful api", "apis", "api",
       "api integrations", "api integration", "scalable apis")
_alias("API Development", "api development", "api design")
_alias("NoSQL", "nosql", "no-sql")
_alias("Qdrant", "qdrant")
_alias("Weaviate", "weaviate")
_alias("Python", "python", "python3", "python programming")
_alias("SQL", "sql", "structured query language")
_alias("JavaScript", "javascript", "js")
_alias("Java", "java")
_alias("TypeScript", "typescript", "ts")
_alias("C++", "c++", "cpp")
_alias("Go", "go", "golang")
_alias("HTML", "html", "html5")
_alias("CSS", "css", "css3")
_alias("R", "r language")
_alias("Scala", "scala")
# tools / platforms
_alias("Docker", "docker", "containerization", "containers")
_alias("Kubernetes", "kubernetes", "k8s", "aks", "eks", "gke")
_alias("Git", "git", "git workflows", "github", "gitlab", "version control")
_alias("MLflow", "mlflow", "ml flow")
_alias("Airflow", "airflow", "apache airflow")
_alias("Kafka", "kafka", "apache kafka")
_alias("Power BI", "power bi", "powerbi")
_alias("Spark", "spark", "apache spark", "pyspark")
_alias("Databricks", "databricks")
_alias("Jenkins", "jenkins")
_alias("Terraform", "terraform")
# databases / vector
_alias("PostgreSQL", "postgresql", "postgres", "postgre sql")
_alias("pgvector", "pgvector")
_alias("MongoDB", "mongodb", "mongo")
_alias("Redis", "redis")
_alias("Pinecone", "pinecone")
_alias("FAISS", "faiss")
_alias("ChromaDB", "chromadb", "chroma", "chroma db")
_alias("Vector Databases", "vector databases", "vector database", "vector db", "vector stores",
       "vector store", "vectordb")
_alias("MySQL", "mysql")
_alias("Elasticsearch", "elasticsearch", "elastic search")
_alias("BigQuery", "bigquery", "big query", "google bigquery")
_alias("Neo4j", "neo4j")

# a few guarded family rules for the long tail (applied only if no exact alias)
_RULES = [
    (re.compile(r"\bllm\b|large language model"), "LLMs"),
    (re.compile(r"retrieval.?augmented|graphrag|\brag\b"), "RAG"),
    (re.compile(r"agent"), "AI Agents"),
    (re.compile(r"prompt"), "Prompt Engineering"),
    (re.compile(r"gen(erative)?[ -]?ai"), "Generative AI"),
    (re.compile(r"embedding"), "Embeddings"),
    (re.compile(r"fine.?tun"), "Fine-tuning"),
    (re.compile(r"\bmlops\b"), "MLOps"),
    (re.compile(r"hugging ?face"), "Hugging Face"),
]


def _cleanup(term: str) -> str:
    t = re.sub(r"\s+", " ", (term or "").strip())
    return t


def canonical(term: str) -> str:
    """Return the canonical skill name for a raw term."""
    t = _cleanup(term)
    key = t.lower()
    if key in ALIASES:
        return ALIASES[key]
    for rx, canon in _RULES:
        if rx.search(key):
            return canon
    # unknown: title-case words but keep short acronyms/known casing intact
    if t.isupper() and len(t) <= 5:
        return t
    return t[:1].upper() + t[1:] if t else t


def bucket_for(canon: str, fallback: str = "skills_concepts") -> str:
    return BUCKET_OF.get(canon, fallback)
