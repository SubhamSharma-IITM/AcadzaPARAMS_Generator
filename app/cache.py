# cache.py  – one-file, zero-dependency helper
import hashlib, json
from functools import lru_cache          # built into Python

def _key(obj: str | dict) -> str:
    """Turn any string/dict into a stable hash key"""
    if isinstance(obj, dict):
        obj = json.dumps(obj, sort_keys=True)
    return hashlib.sha256(obj.encode()).hexdigest()

# ----------- CACHED WRAPPER -------------
@lru_cache(maxsize=2_000)                # keep up to 2 000 distinct texts
def cached_query_checker(text: str, input_type: str):
    # 🔴  IMPORTANT  🔴
    # Import your existing function, *don’t* copy its code here
    from query_checker import query_checker
    return query_checker(
        text=text,
        translate_if_dost_or_mixed=True,
        input_type=input_type
    )
