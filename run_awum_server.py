import os
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(ROOT, "vendor_pydeps")
BACKEND = os.path.join(ROOT, "backend")

if os.path.isdir(VENDOR):
    sys.path.insert(0, VENDOR)
sys.path.insert(0, BACKEND)

import app as awum_app


if __name__ == "__main__":
    awum_app.initialize_app()
    awum_app.app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
