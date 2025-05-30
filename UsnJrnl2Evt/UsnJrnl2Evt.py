from queue import Queue
import argparse
import subprocess
from argparse import ArgumentParser
import signal
import sys
from threading import Thread, Event

journal_queue = Queue()
stop_event = Event()

header_keys = [
    b'USN Journal ID',
    b'First USN',
    b'Next USN',
    b'Start USN',
    b'Min major version',
    b'Max major version']

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
    b'Record length']


def signal_handler(signum, frame):
    print("\nCtrl+C received. Shutting down gracefully...")
    stop_event.set()


def fsutil_capture(args):
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            while not stop_event.is_set():
                line = proc.stdout.readline
                if not line:
                    break
                journal_queue.put(line)
            proc.terminate()
            proc.wait(timeout=2)
    except Exception as e:
        print(f"Error in fsutil_capture: {e}")
    finally:
        # Put a sentinel value to signal the parser thread
        journal_queue.put(None)


def log_entry(entry):
    # This function is a placeholder for logging the entry.
    # In a real implementation, you would write the entry to a log file or process it further.
    print(entry)  # For demonstration purposes, we just print the entry.


def entry_to_dict(entry: list[bytes], keys: list[bytes]) -> dict:
    return dict(zip(keys, [line.split(b':', 1)[1] for line in entry]))


def parse_header(header: list[bytes]) -> dict:
    entry_dict = entry_to_dict(header, header_keys)
    #Store needed values
    return entry_dict


def parse_entry(entry: list[bytes], header: dict):
    entry_dict = entry_to_dict(entry, entry_keys_v3p0)
    #Throw out any self-referencing entries
    log_entry(entry_dict.update(header))


def parse_journal_queue(args: ArgumentParser):
    try:
        header = []
        while not stop_event.is_set():
            line = journal_queue.get()
            if line is None:  # Check for sentinel value
                break
            if line == b'\r\n':
                break
            header.append(line)

        if stop_event.is_set():
            return

        header_dict = parse_header(header)

        while not stop_event.is_set():
            entry = []
            while not stop_event.is_set():
                line = journal_queue.get()
                if line is None:  # Check for sentinel value
                    return
                if line == b'\r\n':
                    break
                entry.append(line)
            if entry:  # Only parse if we have an entry
                parse_entry(entry, header_dict)
    except Exception as e:
        print(f"Error in parse_journal_queue: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--volume', '-vol', default='C:', help='Volume drive letter (Default: "C:")')
    parser.add_argument('--interval', '-i', type=int, default=6, help='Interval in hours (Default: 6)')
    args = parser.parse_args()

    capture_thread = Thread(target=fsutil_capture, args=(['fsutil', 'usn', 'readJournal', args.volume, 'wait'],))
    parse_thread = Thread(target=parse_journal_queue, args=(args,))
    capture_thread.start()
    parse_thread.start()
    capture_thread.join()
    parse_thread.join()


if __name__ == '__main__':
    main()