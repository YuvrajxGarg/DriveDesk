"""Read-only, authenticated mount telemetry; never infer idle from errors."""
import base64
import json
import urllib.request


def snapshot(port, password):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    auth = base64.b64encode(f"drivedesk:{password}".encode()).decode()
    def call(method):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/{method}", data=b"{}",
            headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
        with opener.open(request, timeout=3) as response:
            return json.load(response)
    stats, vfs = call("core/stats"), call("vfs/stats")
    cache = vfs.get("diskCache")
    if not isinstance(cache, dict):
        raise ValueError("Cache status unavailable")
    required = ("uploadsQueued", "uploadsInProgress", "erroredFiles", "outOfSpace")
    if any(key not in cache for key in required):
        raise ValueError("Incomplete cache status")
    queue = call("vfs/queue").get("queue")
    if not isinstance(queue, list):
        raise ValueError("Upload queue unavailable")
    queued = max(cache["uploadsQueued"], sum(not x.get("uploading", False) for x in queue))
    active = stats.get("transferring") or []
    if cache["outOfSpace"] or cache["erroredFiles"]:
        state = "Needs attention — cache full or upload errors"
    elif cache["uploadsInProgress"]:
        state = f"Uploading {cache['uploadsInProgress']} · {queued} queued"
    elif queued:
        state = f"{queued} queued / waiting to upload"
    elif active:
        state = "Transferring"
    else:
        state = "No queued uploads reported"
    names = [str(x.get("name", "")) for x in active + queue]
    return {"state": state, "names": names,
            "speed": sum(float(x.get("speedAvg") or 0) for x in active),
            "bytes": int(stats.get("bytes") or 0)}
