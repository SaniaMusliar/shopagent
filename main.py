import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

SPEC = importlib.util.spec_from_file_location('shopagent_backend_main', BACKEND / 'main.py')
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
app = MODULE.app
