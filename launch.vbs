' TSXS Polar Alignment v2.0 - Windows launcher stub
' Invoked via: wscript.exe launch.vbs
' Shows a console on first run so uv/package progress is visible;
' runs silently on subsequent launches.

Dim WshShell, fso, thisDir, ps1File, flagFile, cmd
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

thisDir  = fso.GetParentFolderName(WScript.ScriptFullName)
ps1File  = thisDir & "\launch.ps1"
Dim userProfile
userProfile = WshShell.ExpandEnvironmentStrings("%USERPROFILE%")
flagFile = userProfile & "\.tsxpolar_cache\.tsxpolar_ready"

If fso.FileExists(flagFile) Then
    ' Normal run - hidden console
    cmd = "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File " _
        & Chr(34) & ps1File & Chr(34)
    WshShell.Run cmd, 0, False
Else
    ' First run - visible console so the user can see what is happening
    cmd = "powershell.exe -ExecutionPolicy Bypass -File " _
        & Chr(34) & ps1File & Chr(34)
    WshShell.Run cmd, 1, False
End If
