import json
from pathlib import Path
from apps.api.app.models import Scenario
Path('scenarios/scenario.schema.json').write_text(json.dumps(Scenario.model_json_schema(), indent=2)+'\n')
