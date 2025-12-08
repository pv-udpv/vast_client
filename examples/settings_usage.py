"""Example: Using VAST Client Settings"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import get_settings

settings = get_settings()
print(f"Environment: {settings.environment}")
print(f"Tracking: {settings.vast_client.enable_tracking}")
