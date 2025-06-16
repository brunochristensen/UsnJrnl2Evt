import os
import sys
import signal
import subprocess
import argparse
import json
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import win32evtlogutil
import win32evtlog

# Configuration for custom event log
EVENT_SOURCE = "USNJournalLogger"
EVENT_LOG = "USNJournalLog"
EVENT_CATEGORY = 0
EVENT_ID = 1000
EVENT_TYPE = win32evtlog.EVENTLOG_INFORMATION_TYPE
USN_STATE_FILE = 'last_usn.txt'
LOG_FILE = 'usn_journal_logger.log'

# Setup Python logging with rotation
logger = logging.getLogger('USNJournalLogger')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# Rotating log: 5MB per file, keep 3 backups
handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
handler.setFormatter(formatter)
logger.addHandler(handler)
# Also log to console
console = logging.StreamHandler()
console.setFormatter(formatter)
logger.addHandler(console)

# Parsing keys for fsutil output
header_keys = [
    b'USN Journal ID', b'First USN', b'Next USN', b'Start USN',
    b'Min major version', b'Max major version'
]
entry_keys = [
    b'Usn', b'File name', b'File name length', b'Reason',
    b'Time stamp', b'File attributes', b'File ID', b'Parent file ID',
    b'Source info', b'Security ID', b'Major version', b'Minor version',
    b'Record length'
]


def is_admin():
    """Return True if running with administrative privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()  # type: ignore
    except Exception:
        return False


def elevate():
    """Relaunch the script with admin privileges"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join(f'"{arg}"' for arg in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                        f'"{script}" {params}', None, 1)
    sys.exit(0)


def signal_handler(signum, frame):
    logger.info("Signal %s received, exiting", signum)
    sys.exit(0)


def load_last_usn():
    logger.debug("Loading last USN from %s", USN_STATE_FILE)
    if os.path.exists(USN_STATE_FILE):
        with open(USN_STATE_FILE, 'r') as f:
            usn = f.read().strip()
        logger.debug("Found last_usn: %s", usn)
        return usn
    logger.debug("No state file, defaulting last_usn to '0'")
    return '0'


def save_next_usn(usn):
    logger.debug("Saving next_usn %s to %s", usn, USN_STATE_FILE)
    with open(USN_STATE_FILE, 'w') as f:
        f.write(usn)


def entry_to_dict(lines, keys):
    logger.debug("Parsing %d lines into dict", len(lines))
    data = {}
    for key, line in zip(keys, lines):
        parts = line.split(b":", 1)
        if len(parts) == 2:
            val = parts[1].strip().decode(errors='ignore')
            data[key.decode()] = val
            logger.debug("Parsed %s: %s", key.decode(), val)
    return data


def report_event(entry):
    """Serialize entry as JSON and write to the Windows event log"""
    logger.debug("Reporting entry: %s", entry)
    try:
        msg = json.dumps(entry, ensure_ascii=False)
    except Exception as e:
        logger.error("JSON serialization error: %s", e)
        msg = str(entry)
    try:
        # Use ReportEvent without eventLogType; event log determined by registration
        win32evtlogutil.ReportEvent(
            EVENT_SOURCE,
            EVENT_ID,
            eventCategory=EVENT_CATEGORY,
            eventType=EVENT_TYPE,
            strings=[msg]
        )
        logger.debug("Windows event logged successfully")
    except Exception as e:
        logger.error("Failed to log event: %s", e)


def parse_journal(cmd):
    logger.debug("Executing fsutil with cmd: %s", cmd)
    header_lines, entry_lines = [], []
    header_parsed = False
    header = {}
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    for raw in proc.stdout:
        line = raw.strip()
        logger.debug("fsutil output: %s", line)
        if line == b'':
            if not header_parsed:
                logger.debug("Parsing header block")
                header = entry_to_dict(header_lines, header_keys)
                nxt = header.get('Next USN')
                if nxt:
                    save_next_usn(nxt)
                header_parsed = True
                header_lines.clear()
                logger.debug("Header parsed: %s", header)
            else:
                logger.debug("Parsing entry block of %d lines", len(entry_lines))
                entry = entry_to_dict(entry_lines, entry_keys)
                entry.update(header)
                report_event(entry)
                entry_lines.clear()
        else:
            if not header_parsed:
                header_lines.append(raw)
            else:
                entry_lines.append(raw)
    proc.wait()
    logger.debug("fsutil process exited with code %d", proc.returncode)


def main():
    if not is_admin():
        logger.info("Not running as admin, requesting elevation")
        elevate()

    logger.info("Starting USN Journal Logger script")
    parser = argparse.ArgumentParser()
    parser.add_argument('--volume', '-vol', default='C:', help='Volume letter')
    args = parser.parse_args()
    logger.debug("Parsed arguments: %s", args)

    try:
        win32evtlogutil.AddSourceToRegistry(EVENT_SOURCE, sys.executable, EVENT_LOG)
        logger.debug("Event source registered in registry")
    except Exception as e:
        logger.warning("Registry registration may require elevation: %s", e)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    last = load_last_usn()
    logger.info("Starting journal read at USN %s", last)
    cmd = ['fsutil', 'usn', 'readJournal', args.volume, f'startusn={last}']
    parse_journal(cmd)
    logger.info("USN Journal Logger script complete")


if __name__ == '__main__':
    main()
