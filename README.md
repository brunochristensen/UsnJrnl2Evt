# UsnJrnl2Evtx

Shoutout to SANS FOR508 course instructor [Mr. Carlos Cajigas](https://www.linkedin.com/in/carloscajigas/) for the inspiration to develop this tool.

## Description

Windows NTFS' USN Change Journal provide excellent insight into file metadata and volume specific file activity. UsnJrnl2Evtx utilizes Windows' fsutil.exe to continuouly fetch USN Journal entries and log them with other Windows event logs. These logs can then be analysed or ingested into a SIEM.

## Usage

Execution of usnjrnl2evtx.py will log USN Journal entries as they appear via ```fsutil usn readJournal C:```, with associated headers and journal information. Usnjrnl2Evtx will target the C:\ drive by default. 
```
python usnjrnl2evtx.py 
```
### Command-Line Options 

```
```
