import json
import os
import time
from datetime import datetime, timezone

# Level hierarchy — AUDIT sits between INFO and WARN for security/business events
_LEVELS = {'DEBUG': 10, 'INFO': 20, 'AUDIT': 25, 'WARN': 30, 'WARNING': 30, 'ERROR': 40}
_ABBREV = {'DEBUG': 'DBG', 'INFO': 'INF', 'AUDIT': 'AUD', 'WARN': 'WRN', 'WARNING': 'WRN', 'ERROR': 'ERR'}
_level_cache: dict = {'value': None, 'expires': 0.0}
_CACHE_TTL = 2.0  # seconds between registry reads


def _system_level_num() -> 'int | None':
    """Read APP_LOG_LEVEL from Windows user env (registry) with a 2s TTL cache.

    Reads the registry directly rather than os.environ so changes made by
    set_loglevel.ps1 take effect in running processes without a restart.
    Falls back to os.environ on non-Windows.
    Returns None if APP_LOG_LEVEL is not set.
    """
    now = time.monotonic()
    if now < _level_cache['expires']:
        cached = _level_cache['value']
        return _LEVELS.get(cached) if cached else None
    raw = None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            raw, _ = winreg.QueryValueEx(key, 'APP_LOG_LEVEL')
    except ImportError:
        raw = os.environ.get('APP_LOG_LEVEL')
    except (FileNotFoundError, OSError):
        pass
    value = raw.upper().strip() if isinstance(raw, str) else None
    _level_cache['value'] = value
    _level_cache['expires'] = now + _CACHE_TTL
    return _LEVELS.get(value) if value else None


class _Scope:
    def __init__(self, state: dict, scope: str, correlation_id: str):
        self._state = state
        self._scope = scope
        self._correlation_id = correlation_id

    def log(self, level: str, message: str) -> None:
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
            'level': level,
            'location': self._scope,
            'correlation_id': self._correlation_id,
            'message': message,
        }
        # File always receives every message regardless of level filters
        if self._state['log_file']:
            try:
                with open(self._state['log_file'], 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record) + '\n')
            except OSError:
                pass
        # Console: APP_LOG_LEVEL (live, system-wide) overrides configured console_level
        msg_num = _LEVELS.get(level.upper(), _LEVELS['INFO'])
        sys_num = _system_level_num()
        threshold = sys_num if sys_num is not None else self._state['console_level_num']
        if msg_num >= threshold:
            abbrev = _ABBREV.get(level.upper(), level[:3].upper())
            print(f"*** LOG: {abbrev} * {record['timestamp']} * {self._scope} ***  {message}")

    def __enter__(self):
        self.log('DEBUG', f'Entering {self._scope}...')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.log('ERROR', f'Exiting {self._scope} with exception: {exc_val}')
        else:
            self.log('DEBUG', f'Exiting {self._scope}.')
        return False


class AppLogger:
    _state: dict = {
        'app_name': 'App',
        'log_file': '',
        'console_level_num': _LEVELS['INFO'],
    }

    @classmethod
    def configure(cls, app_name: str, level: str = 'INFO', log_file: str = '',
                  console_level: str = '') -> None:
        cls._state['app_name'] = app_name
        cls._state['log_file'] = log_file
        effective = console_level if console_level else level
        cls._state['console_level_num'] = _LEVELS.get(effective.upper(), _LEVELS['INFO'])

    @classmethod
    def enter(cls, scope: str, correlation_id: str = '') -> _Scope:
        if not correlation_id:
            correlation_id = str(os.getpid())
        return _Scope(cls._state, scope, correlation_id)
