"""Real fix from the device's built-in location sensor (GPS / Wi-Fi positioning) -- not the
VPN-skewed IP -- for the weather widget. `locate()` returns (lat, lon), or None on any failure
(sensor off, permission denied, no helper) so weather falls back to IP geolocation.

Per-OS, no Python dependencies -- each OS exposes location only through its own native call:
  * Windows: the Location API via `powershell.exe` (the in-box, frozen PowerShell 5.1 -- NOT the
             separately-updated `pwsh` 7.x -- so its version never drifts), awaiting WinRT.
  * macOS:   CoreLocationCLI (`brew install corelocationcli`), if present.
  * Linux:   the geoclue 'where-am-i' demo, if present.

Self-check: `python gps.py` -- prints the fix (or None on a machine without one)."""
import base64
import platform
import shutil
import subprocess

_TIMEOUT = 12

# in-box Windows PowerShell 5.1 awaits the WinRT Geolocator -> "OK lat,lon" (nothing on failure)
_PS = r'''
$ErrorActionPreference='Stop'
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  $asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
  function Await($op,$t){ $asTask.MakeGenericMethod($t).Invoke($null,@($op)).GetAwaiter().GetResult() }
  [void][Windows.Devices.Geolocation.Geolocator,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
  $p = (Await ((New-Object Windows.Devices.Geolocation.Geolocator).GetGeopositionAsync()) ([Windows.Devices.Geolocation.Geoposition])).Coordinate.Point.Position
  "OK $($p.Latitude),$($p.Longitude)"
} catch {}
'''


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT).stdout.strip()


def _windows():
    enc = base64.b64encode(_PS.encode("utf-16-le")).decode()        # -EncodedCommand dodges all quoting
    out = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc])
    return _pair(out[3:], ",") if out.startswith("OK ") else None


def _macos():
    return _pair(_run(["CoreLocationCLI", "-once", "-format", "%latitude,%longitude"]), ",")


def _linux():
    exe = shutil.which("where-am-i") or "/usr/lib/geoclue-2.0/demos/where-am-i"
    lat = lon = None
    for line in _run([exe, "-t", "5"]).splitlines():
        if "Latitude" in line:
            lat = float(line.split(":")[1].strip().rstrip("°"))
        elif "Longitude" in line:
            lon = float(line.split(":")[1].strip().rstrip("°"))
    return None if lat is None or lon is None else (lat, lon)


def _pair(text, sep):
    lat, lon = text.split(sep)
    return float(lat), float(lon)


_OS = {"Windows": _windows, "Darwin": _macos, "Linux": _linux}


def locate():
    """(lat, lon) from the device's location sensor, or None if unavailable / denied / unsupported."""
    try:
        return _OS.get(platform.system(), lambda: None)()
    except Exception:
        return None                                                 # off / missing helper -> IP fallback


if __name__ == "__main__":
    print("device location:", locate())
