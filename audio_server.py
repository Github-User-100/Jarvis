import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_root, 'shared'))
sys.path.insert(0, os.path.join(_root, 'src'))

from AppLogger import AppLogger
from Jarvis import Jarvis

_log_file = os.path.join(_root, 'jarvis.log')
AppLogger.configure(app_name='Jarvis', level='INFO', log_file=_log_file, console_level='WARN')

if __name__ == '__main__':
    Jarvis().run()
