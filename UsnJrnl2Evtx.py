import queue

import subprocess

from threading import Thread

journal_queue = queue.Queue()
header_dict = {
    'USN Journal ID': None,
    'First USN': None,
    'Next USN': None,
    'Start USN': None,
    'Min major version': None,
    'Max major version': None}
entry_dict_v3p0 = {
    'Usn': None,
    'File name': None,
    'File name length': None,
    'Reason': None,
    'Time stamp': None,
    'File attributes': None,
    'File ID': None,
    'Parent file ID': None,
    'Source info': None,
    'Security ID': None,
    'Major version': None,
    'Minor version': None,
    'Record length': None}
reason_code = {
    0x00008000: "A user has either changed one or more file or directory attributes (for example, the read-only, hidden, system, archive, or sparse attribute), or one or more time stamps.",
    0x80000000: "The file or directory is closed.",
    0x00020000: "The compression state of the file or directory is changed from or to compressed.",
    0x00000002: "The file or directory is extended (added to).",
    0x00000001: "The data in the file or directory is overwritten.",
    0x00000004: "The file or directory is truncated.",
    0x00000400: "The user made a change to the extended attributes of a file or directory.",
    0x00040000: "The file or directory is encrypted or decrypted.",
    0x00000100: "The file or directory is created for the first time.",
    0x00000200: "The file or directory is deleted.",
    0x00010000: "An NTFS file system hard link is added to or removed from the file or directory.",
    0x00004000: "A user changes the FILE_ATTRIBUTE_NOT_CONTENT_INDEXED attribute.",
    0x00800000: "A user changed the state of the FILE_ATTRIBUTE_INTEGRITY_STREAM attribute for the given stream.",
    0x00000020: "The one or more named data streams for a file are extended (added to).",
    0x00000010: "The data in one or more named data streams for a file is overwritten.",
    0x00000040: "The one or more named data streams for a file is truncated.",
    0x00080000: "The object identifier of a file or directory is changed.",
    0x00002000: "A file or directory is renamed, and the file name in the USN_RECORD_V4 structure is the new name.",
    0x00001000: "The file or directory is renamed, and the file name in the USN_RECORD_V4 structure is the previous name.",
    0x00100000: "The reparse point that is contained in a file or directory is changed, or a reparse point is added to or deleted from a file or directory.",
    0x00000800: "A change is made in the access rights to a file or directory.",
    0x00200000: "A named stream is added to or removed from a file, or a named stream is renamed.",
    0x00400000: "The given stream is modified through a committed TxF transaction."}


def fsutil_capture(args):
    with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
        for stdout_line in iter(proc.stdout.readline, ""):
            journal_queue.put(stdout_line)


def log_entry(entry):
    return None


def entry_to_dict(entry: list[bytes], dest: dict) -> dict:
    entry_dict = dest.copy()
    for line in entry:
        key, value = line.decode('ascii').split(':', 1)
        entry_dict[key.strip()] = value.strip()
    return entry_dict


def parse_header(header: list[bytes]):
    entry_to_dict(header, header_dict)


def parse_entry(entry: list[bytes]):
    entry_to_dict(entry, entry_dict_v3p0)
    log_entry(entry)


def parse_journal_queue():
    journal_header = []
    while (line := journal_queue.get()) != b'\r\n':
        journal_header.append(line)
    parse_header(journal_header)
    while True:
        entry = []
        while (line := journal_queue.get()) != b'\r\n':
            entry.append(line)
        parse_entry(entry)


def main():
    args = ['fsutil', 'usn', 'readJournal', 'C:', 'wait']
    capture = (Thread(target=fsutil_capture, args=(args,)))
    capture.start()
    parse = Thread(target=parse_journal_queue)
    parse.start()

    capture.join()
    parse.join()


if __name__ == '__main__':
    main()
