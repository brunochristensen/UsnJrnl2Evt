import collections
import queue
import argparse
import subprocess

from threading import Thread

journal_queue = queue.Queue()

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

reason_code = collections.OrderedDict()
reason_code[0x00008000] = "A user has either changed one or more file or directory attributes (for example, the " \
                          "read-only, hidden, system, archive, or sparse attribute), or one or more time stamps."
reason_code[0x80000000] = "The file or directory is closed."
reason_code[0x00020000] = "The compression state of the file or directory is changed from or to compressed."
reason_code[0x00000002] = "The file or directory is extended (added to)."
reason_code[0x00000001] = "The data in the file or directory is overwritten."
reason_code[0x00000004] = "The file or directory is truncated."
reason_code[0x00000400] = "The user made a change to the extended attributes of a file or directory."
reason_code[0x00040000] = "The file or directory is encrypted or decrypted."
reason_code[0x00000100] = "The file or directory is created for the first time."
reason_code[0x00000200] = "The file or directory is deleted."
reason_code[0x00010000] = "An NTFS file system hard link is added to or removed from the file or directory."
reason_code[0x00004000] = "A user changes the FILE_ATTRIBUTE_NOT_CONTENT_INDEXED attribute."
reason_code[0x00800000] = "A user changed the state of the FILE_ATTRIBUTE_INTEGRITY_STREAM attribute for the given " \
                          "stream."
reason_code[0x00000020] = "The one or more named data streams for a file are extended (added to)."
reason_code[0x00000010] = "The data in one or more named data streams for a file is overwritten."
reason_code[0x00000040] = "The one or more named data streams for a file is truncated."
reason_code[0x00080000] = "The object identifier of a file or directory is changed."
reason_code[0x00002000] = "A file or directory is renamed, and the file name in the USN_RECORD_V4 structure is the " \
                          "new name."
reason_code[0x00001000] = "The file or directory is renamed, and the file name in the USN_RECORD_V4 structure is the " \
                          "previous name."
reason_code[0x00100000] = "The reparse point that is contained in a file or directory is changed, or a reparse point " \
                          "is added to or deleted from a file or directory."
reason_code[0x00000800] = "A change is made in the access rights to a file or directory."
reason_code[0x00200000] = "A named stream is added to or removed from a file, or a named stream is renamed."
reason_code[0x00400000] = "The given stream is modified through a committed TxF transaction."


def hex_to_dec(s: bytes) -> bytes:
    return bytes(str(int(s, 0)), 'ascii')


def parse_code_reason_pair(reason: bytes, verbose: bool) -> bytes:
    if verbose:
        return reason
    return reason.split(b':')[1].strip()


def fsutil_capture(args):
    with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
        for stdout_line in iter(proc.stdout.readline, ""):
            journal_queue.put(stdout_line)


def log_entry(entry):
    return None


def entry_to_dict(entry: list[bytes], keys: list[bytes]) -> dict:
    values = [line.split(b':', 1)[1] for line in entry]
    return dict(zip(keys, values))


def parse_header(header: list[bytes]) -> dict:
    entry_dict = entry_to_dict(header, header_keys)
    entry_dict[b'USN Journal ID'] = hex_to_dec(entry_dict[b'USN Journal ID'])
    return entry_dict


def parse_entry(entry: list[bytes], header: dict):
    entry_dict = entry_to_dict(entry, entry_keys_v3p0)
    entry_dict[b'Reason'] = parse_code_reason_pair(entry_dict[b'Reason'], g_verbose)
    log_entry(entry_dict)


def parse_journal_queue():
    journal_header = []
    while (line := journal_queue.get()) & b'\r\n':
        journal_header.append(line)
    header_dict = parse_header(journal_header)
    while True:
        entry = []
        while (line := journal_queue.get()) & b'\r\n':
            entry.append(line)
        parse_entry(entry, header_dict)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--verbose', '-v', action='store_true')
    p.add_argument('--reason', '-r', action='store_true')
    p.add_argument('--header', '-h', action='store_true')
    args = ['fsutil', 'usn', 'readJournal', 'C:', 'wait']
    capture = (Thread(target=fsutil_capture, args=(args,)))
    capture.start()
    parse = Thread(target=parse_journal_queue)
    parse.start()

    capture.join()
    parse.join()


if __name__ == '__main__':
    main()
