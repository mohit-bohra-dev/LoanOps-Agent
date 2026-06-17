import json
import urllib.request

try:
    req = urllib.request.Request(
        "http://localhost:8000/chat",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"message": "what was the last pay date for Sam Patel?"}).encode("utf-8"),
    )
    res = urllib.request.urlopen(req)
    print("STATUS:", res.status)
    print("BODY:")
    for line in res:
        print(line.decode("utf-8").strip())
except Exception as e:
    print("ERROR:", str(e))
