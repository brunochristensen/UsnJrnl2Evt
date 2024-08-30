# UsnJrnl2Evtx

I was a SANS FOR508 course when [Mr. Carlos Cajigas](https://www.linkedin.com/in/carloscajigas/) said something to the effect of: "No one has made something like this".

Looking back I'm not sure if that was a challenge, but that's how it seemed at the time. So here we are.

## What it does

UsnJrnl2Evtx utilizes the Windows fsutil.exe to periodically grab USN Journal entries and log them with other windows event logs. From there they can be exported to a SIEM or whatever makes you&mdash;the user&mdash;happy. :)
