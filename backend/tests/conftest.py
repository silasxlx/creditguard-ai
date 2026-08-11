import os

os.environ.setdefault("CREDIT_REVIEW_BUSINESS_DB", "data/test-business.db")
os.environ.setdefault("CREDIT_REVIEW_CHECKPOINT_DB", "data/test-checkpoints.db")
os.environ.setdefault("CREDIT_REVIEW_STORAGE_ROOT", "data/test-storage")
os.environ.setdefault("CREDIT_REVIEW_ALLOW_MEMORY_CHECKPOINT", "true")
