"""Что на самом деле отдают разделы, которые выглядят пустыми."""
import json
import urllib.request

B = "http://127.0.0.1:5195"
page = urllib.request.urlopen(B + "/", timeout=30).read().decode()
m = 'name="xlam-ui-token" content="'
at = page.find(m) + len(m)
token = page[at:page.find('"', at)]


def get(path):
    r = urllib.request.Request(B + path)
    r.add_header("X-Xlam-UI-Token", token)
    return json.loads(urllib.request.urlopen(r, timeout=120).read().decode())


print("=== /api/queue ===")
d = get("/api/queue")
print("  ключи:", list(d))
for k, v in d.items():
    print(f"   {k}: {type(v).__name__} len={len(v) if hasattr(v, '__len__') else '-'}")

print()
print("=== /api/devices/emulator-5554/queue ===")
d2 = get("/api/devices/emulator-5554/queue")
print("  ключи:", list(d2))
q2 = d2.get("queue") or d2.get("items") or []
print("  записей:", len(q2))
if q2:
    print("  пример:", json.dumps(q2[0], ensure_ascii=False)[:200])

print()
print("=== /api/history ===")
d3 = get("/api/history")
print("  ключи:", list(d3))
items = d3.get("items") or []
print("  записей:", len(items))
print("  summary:", json.dumps(d3.get("summary", {}), ensure_ascii=False)[:300])
if items:
    print("  пример:", json.dumps(items[0], ensure_ascii=False)[:220])

print()
print("=== /api/devices/emulator-5554/logs ===")
d4 = get("/api/devices/emulator-5554/logs?limit=50")
print("  ключи:", list(d4))
logs = d4.get("logs")
print("  тип:", type(logs).__name__, "len:", len(logs) if hasattr(logs, "__len__") else "-")
if isinstance(logs, list) and logs:
    print("  пример:", str(logs[0])[:160])
elif isinstance(logs, str):
    print("  текст:", logs[:160])