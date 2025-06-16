import os
import sys
import signal
import subprocess
import argparse
import json
import win32evtlogutil
import win32evtlog
import win32event
import win32con
import win32api
from threading import Thread, Event
from queue import Queue, Empty

journal_queue = Queue()
stop_event = Event()

EVENT_SOURCE = "USNJournalLogger"
EVENT_LOG = "USNJournalLog"
EVENT_CATEGORY = 0
EVENT_ID = 1000
EVENT_TYPE = win32evtlog.EVENTLOG_INFORMATION_TYPE

header_keys = [
    b'USN Journal ID',
    b'First USN',
    b'Next USN',
    b'Start USN',
    b'Min major version',
    b'Max major version'
]

entry_keys_v3p0 = [
    b'Usn',
    b'File name',
    b'File name length',
    b'Reason',
    b'Time stamp',
    b'File attributes',
    b'File ID',
    b'Parent file ID',
    b'Source info',
    b'Security ID',
    b'Major version',
    b'Minor version',
    b'Record length'
]

USN_STATE_FILE = 'last_usn.txt'

def signal_handler(signum, frame):
    print("\nCtrl+C received. Shutting down gracefully...")
    stop_event.set()

def load_last_usn() -> str:
    if os.path.exists(USN_STATE_FILE):
        with open(USN_STATE_FILE, 'r') as f:
            return f.read().strip()
    return "0"

def save_next_usn(usn: str):
    with open(USN_STATE_FILE, 'w') as f:
        f.write(usn)

def fsutil_capture(args):
    print('Thread spawned: Beginning journal capture')
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            while not stop_event.is_set():
                line = proc.stdout.readline()
                if not line:
                    break
                journal_queue.put(line)
            proc.terminate()
            proc.wait(timeout=2)
    except Exception as e:
        print(f"Error in fsutil_capture: {e}")
    finally:
        journal_queue.put(None)

def log_entry(entry):
    """
    Serialize each USN entry as JSON for Winlogbeat ingestion and write to custom Event Log.
    """
    try:
        msg_json = json.dumps(entry, ensure_ascii=False)
    except Exception as e:
        print(f"Error serializing entry to JSON: {e}")
        msg_json = str(entry)
    print(msg_json)
    try:
        win32evtlogutil.ReportEvent(
            EVENT_SOURCE,
            EVENT_ID,
            eventCategory=EVENT_CATEGORY,
            eventType=EVENT_TYPE,
            strings=[msg_json],
            eventLogType=EVENT_LOG
        )
    except Exception as e:
        print(f"Failed to log event: {e}")

def entry_to_dict(entry, keys):
    result = {}
    for k, line in zip(keys, entry):
        parts = line.split(b":", 1)
        if len(parts) == 2:
            result[k.decode()] = parts[1].strip().decode(errors='ignore')
    return result

def parse_header(header):
    print('Parsing header...')
    header_dict = entry_to_dict(header, header_keys)
    if header_dict.get('USN Journal ID') == 'Access is denied':
        print('Access is denied, Administrator privileges required.')
        stop_event.set()
    next_usn = header_dict.get('Next USN')
    if next_usn:
        save_next_usn(next_usn)
    print(header_dict)
    return header_dict

def parse_entry(entry, header):
    entry_dict = entry_to_dict(entry, entry_keys_v3p0)
    entry_dict.update(header)
    log_entry(entry_dict)

def parse_journal_queue(args):
    print('Thread spawned: Beginning journal parse queue')
    try:
        header = []
        while not stop_event.is_set():
            try:
                line = journal_queue.get(timeout=1)
            except Empty:
                continue
            if line is None or line == b'\r\n':
                break
            header.append(line)

        if stop_event.is_set():
            return

        header_dict = parse_header(header)

        while not stop_event.is_set():
            entry = []
            while not stop_event.is_set():
                try:
                    line = journal_queue.get(timeout=1)
                except Empty:
                    continue
                if line is None or line == b'\r\n':
                    break
                entry.append(line)
            if entry:
                parse_entry(entry, header_dict)
    except Exception as e:
        print(f"Error in parse_journal_queue: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--volume', '-vol', default='C:', help='Volume drive letter (Default: "C:")')
    parser.add_argument('--interval', '-i', type=int, default=6, help='Interval in hours (Default: 6)')
    args = parser.parse_args()

    try:
        # Register a custom event source/log under USNJournalLog
        win32evtlogutil.AddSourceToRegistry(
            EVENT_SOURCE,
            sys.executable,
            EVENT_LOG
        )
    except Exception:
        pass

    last_usn = load_last_usn()
    cmd_args = ['fsutil', 'usn', 'readJournal', args.volume, f'startusn={last_usn}']

    capture_thread = Thread(target=fsutil_capture, args=(cmd_args,))
    parse_thread = Thread(target=parse_journal_queue, args=(args,))

    signal.signal(signal.SIGINT, signal_handler)

    capture_thread.start()
    parse_thread.start()
    capture_thread.join()
    parse_thread.join()

if __name__ == '__main__':
    main()
