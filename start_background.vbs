Set shell = CreateObject("Wscript.Shell")
shell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
shell.Run """" & shell.CurrentDirectory & "\.venv\Scripts\pythonw.exe"" run.py --no-reload", 0, False
