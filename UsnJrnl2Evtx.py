import subprocess
from calendar import weekheader

import pyuac
from collections import deque

def main():
    raw = journal_capture(True)
    parse_journal(raw)

def journal_capture(first_run=False):
    if first_run:
        print("Capturing and parsing UsnJrnl, this first capture may take a while...")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return subprocess.check_output("fsutil usn readJournal C:", startupinfo=si)

def parse_journal(raw_journal):
    decoded = raw_journal.decode("ascii")
    list_of_entries = [entry.split("\r\n") for entry in decoded.split("\r\n\r\n")]
    del list_of_entries[0] #removes the journal header
    del list_of_entries[-1][-1] #removes empty element on last entry
    for entry in list_of_entries:
        usn, file_name, file_name_length, reason, time_stamp, file_attributes, file_id, parent_file_id, source_info, security_id, major_version, minor_version, record_length = entry
        usn = [e.strip() for e in usn.split(":")]
        file_name = [e.strip() for e in file_name.split(":")]
        file_name_length = [e.strip() for e in file_name_length.split(":")]
        reason = [e.strip() for e, k in reason.split(":", 1)]
    print(list_of_entries[0])

def parse_journal_header(raw_journal):
    decoded = raw_journal.decode("ascii")
    list_of_entries = [entry.split("\r\n") for entry in decoded.split("\r\n\r\n")]
    return list_of_entries[0]

if __name__ == '__main__':
    if not pyuac.isUserAdmin():
        pyuac.runAsAdmin()
    else:
        main()