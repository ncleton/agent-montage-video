"""Lance l'API du studio avec la configuration ClassroomIO du studio."""
from pathlib import Path

import uvicorn
from leadgenerator.platform import learning


data = Path(__file__).resolve().parent / "data"
learning.SECRET = data / "learning.json"
uvicorn.run("leadgenerator.platform.app:app", host="127.0.0.1", port=55823, access_log=False)
