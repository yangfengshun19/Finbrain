"""Single-process local startup; optional workspace-local dependencies."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.deps'))
sys.path.insert(0, str(ROOT))
env = ROOT / '.env'
if env.exists():
    for line in env.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

if __name__ == '__main__':
    import uvicorn
    from backend.app.main import create_app
    uvicorn.run(create_app(), host='127.0.0.1', port=int(os.getenv('FINBRAIN_PORT', '8765')), access_log=False)
