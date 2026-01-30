import sys
import backend.app as _app

# Alias backend.app as app for backward compatibility
sys.modules["app"] = _app
