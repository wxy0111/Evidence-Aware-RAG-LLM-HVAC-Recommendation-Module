from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / 'data'
KNOWLEDGE_DIR = DATA_DIR / 'knowledge'
FEEDBACK_DIR = DATA_DIR / 'feedback'
HISTORY_DIR = DATA_DIR / 'history'
EXAMPLES_DIR = DATA_DIR / 'examples'

DEFAULT_KB_PATH = KNOWLEDGE_DIR / 'recommendation_knowledge_base.json'
DEFAULT_FEEDBACK_PATH = FEEDBACK_DIR / 'user_feedback_examples.csv'
DEFAULT_HISTORY_PATH = HISTORY_DIR / 'optimization_results_sample.csv'
