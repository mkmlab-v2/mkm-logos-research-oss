# Cursor Agent Headless Smoke

- generated_utc: 2026-04-06T12:42:05.2472137+00:00
- cursor_path: C:\Users\PRO\AppData\Local\Programs\cursor\resources\app\bin\cursor.cmd
- decision: NO_GO
- rationale: No non-help command produced reliable stdout text for headless triage.

## Cases
- [help] exit=0 ok=True output_nonempty=True
- [positional_prompt] exit=0 ok=True output_nonempty=False
- [stdin_dash] exit=0 ok=True output_nonempty=True
- [prompt_flag] exit=0 ok=True output_nonempty=True
- [prompt_flag_output_format] exit=0 ok=True output_nonempty=True

## Raw Outputs (trimmed)

### help
command: cursor agent --help
```text
Cursor 3.0.9

Usage: cursor.exe [options][paths...]

To read output from another program, append '-' (e.g. 'echo Hello World | cursor.exe -')

Options
  -d --diff <file> <file>                    Compare two files with each
                                             other.
  -m --merge <path1> <path2> <base> <result> Perform a three-way merge by
                                             providing paths for two modified
                                             versions of a file, the common
                                             origin of both modified versions
                                             and the output file to save merge
                                             results.
  -a --add <folder>                          Add folder(s) to the last active
                                             window.
  --remove <folder>                          Remove folder(s) from the last
                                             active window.
  -g --goto <file:line[:character]>          Open a file at the path on the
                                             specified line and character
                                             po...(truncated)
```

### positional_prompt
command: cursor agent "Say only: OK_HEADLESS_TEST"
(empty)

### stdin_dash
command: echo Say only: OK_HEADLESS_TEST|cursor agent -
```text
Reading from stdin via: C:\Users\PRO\AppData\Local\Temp\code-stdin-BgH
```

### prompt_flag
command: cursor agent -p "Say only: OK_HEADLESS_TEST"
```text
cmd.exe : Warning: 'p' is not in the list of known options, but still passed to Electron/Chromium.
At C:\workspace\scripts\smoke_cursor_agent_headless.ps1:14 char:14
+   $output = (& cmd /c $Command 2>&1 | Out-String)
+              ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Warning: 'p' is...ctron/Chromium.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
```

### prompt_flag_output_format
command: cursor agent -p "Say only: OK_HEADLESS_TEST" --output-format text
```text
cmd.exe : Warning: 'p' is not in the list of known options, but still passed to Electron/Chromium.
At C:\workspace\scripts\smoke_cursor_agent_headless.ps1:14 char:14
+   $output = (& cmd /c $Command 2>&1 | Out-String)
+              ~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (Warning: 'p' is...ctron/Chromium.:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
Warning: 'output-format' is not in the list of known options, but still passed to Electron/Chromium.
```
