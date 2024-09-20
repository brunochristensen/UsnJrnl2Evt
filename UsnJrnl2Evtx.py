import queue

import subprocess

from threading import Thread

journal_queue = queue.Queue()

def fsutil_capture(args):
    with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
        for stdout_line in iter(proc.stdout.readline, ""):
            journal_queue.put(stdout_line)

def log_entry(entry):
    return None

def parse_header(header):
    return None

def parse_entry(entry):
    log_entry(entry)
    return None

def parse_journal_queue():
    journal_header = []
    entry = []
    while True:
        line = journal_queue.get()
        if line != b'\r\n':
            journal_header.append(line.decode('ASCII'))
        else:
            break
    parse_header(journal_header)
    while True:
        line = journal_queue.get()
        if line != b'\r\n':
            entry.append(line.decode('ASCII'))
        else:
            parse_entry(entry)
            entry = []


def main():
    args = ['fsutil', 'usn', 'readJournal', 'C:', 'wait']
    capture = (Thread(target=fsutil_capture, args=(args,), daemon=True))
    capture.start()
    parse = Thread(target=parse_journal_queue, daemon=True)
    parse.start()

    capture.join()
    parse.join()

if __name__ == '__main__':
    main()
