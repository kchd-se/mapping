"""Script to generate openapi.json from the FastAPI app."""
import sys, json
sys.path.insert(0, ".")
from apps.api.main import app
spec = app.openapi()
with open("apps/api/openapi.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
paths = list(spec.get("paths", {}).keys())
print(f"OpenAPI spec written — {len(paths)} paths:")
for p in paths:
    print(" ", p)