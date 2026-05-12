import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, 'shared'))
sys.path.insert(0, os.path.join(_root, 'src'))
