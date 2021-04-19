import sys
import os


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)
    base_path = base_path.replace('/dist/driver', '')
    return os.path.join(base_path, relative_path)
