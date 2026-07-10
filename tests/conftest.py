import os

# Safe defaults so the API app can be imported without a real environment.
os.environ.setdefault("HASH_SECRET_KEY", "test-secret")
os.environ.setdefault("HASH_ALGORITHM", "HS256")
os.environ.setdefault("HASH_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/bandit-brain-test")
