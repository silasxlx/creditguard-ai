import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app

output = Path("artifacts/openapi.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(output)
