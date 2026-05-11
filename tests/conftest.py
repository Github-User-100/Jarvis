import sys
import os
import glob

for _d in glob.glob(r'C:\Temp\ClaudeStuff\shared\*\python'):
    sys.path.insert(0, _d)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
