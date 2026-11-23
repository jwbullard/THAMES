---
name: Bug report
about: Something in THAMES did not work as expected
title: ''
labels: bug
assignees: ''
---

**What happened**
A short description of the problem, and what you expected instead.

**Steps to reproduce**
1.
2.
3.

**Version and system**
- THAMES version (Help -> About), e.g. 1.0.0-alpha.4.4:
- Operating system and version (e.g. Windows 11 24H2, or macOS 15 with chip type from Apple menu -> About This Mac):

**Logs**
On the Operations page, select the operation that went wrong, open the **Logs**
tab, click **Export Logs...**, and attach the zip file here. It contains the
operation's logs, its input file and run summary (`Result/run_metadata.json`),
and the application logs (`thames.log`, `thames-crash.log`). It does not include
images or result files.

If THAMES crashed before you could export, attach these instead:
- Windows: `%LOCALAPPDATA%\THAMES\logs\thames.log` and `thames-crash.log`
- macOS: `~/Library/Application Support/THAMES/logs/thames.log` and `thames-crash.log`
