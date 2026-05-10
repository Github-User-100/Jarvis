import sys
import glob

for _d in glob.glob(r'C:\Temp\ClaudeStuff\shared\*\python'):
    sys.path.insert(0, _d)
