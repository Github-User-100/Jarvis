import sys
import glob
import os

for _d in glob.glob(r'C:\Temp\ClaudeStuff\shared\*\python'):
    sys.path.insert(0, _d)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from AppLogger import AppLogger
from Jarvis import Jarvis

AppLogger.configure(app_name='Jarvis', level='INFO', log_file=r'C:\Temp\ClaudeStuff\Jarvis\jarvis.log')

if __name__ == '__main__':
    Jarvis().run()
