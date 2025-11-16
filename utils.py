import redis
import git
import os
from flask_login import UserMixin

# Redis for caching
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()  # Test connection
except redis.ConnectionError:
    redis_client = None  # Fallback if Redis not running

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def cache_response(key, value, ttl=3600):
    if redis_client:
        redis_client.setex(key, ttl, value)

def get_cached_response(key):
    if redis_client:
        return redis_client.get(key)
    return None

def version_file(filepath, message="Auto-commit"):
    try:
        repo = git.Repo.init(os.path.dirname(filepath))
        repo.index.add([filepath])
        repo.index.commit(message)
    except Exception as e:
        print(f"Git versioning error: {e}")  # Log without crashing

def render_preview(code, language='html'):
    # Simple server-side rendering for previews (extend for other langs)
    if language == 'html':
        return f"<iframe srcdoc='{code}' style='width:100%; height:300px; border:none;'></iframe>"
    return "<p>Preview not available for this language.</p>"