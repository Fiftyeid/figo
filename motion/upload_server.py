#!/usr/bmedia/env python3
"""Tiny upload page so the voice track can be dropped straight into the sandbox.

Run:  python upload_server.py [port]
Then open the preview URL and drag the mp3 in. File lands in ./media/.
"""
from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
INDIR = os.path.join(HERE, "media")
os.makedirs(INDIR, exist_ok=True)

PAGE = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ارفع الملف الصوتي</title>
<style>
 :root{color-scheme:dark}
 *{box-sizing:border-box}
 body{margin:0;min-height:100vh;display:grid;place-items:center;background:
   radial-gradient(900px 600px at 20% 0%,#171a3a 0%,#080a16 55%,#04050c 100%);
   font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;color:#e8ecf8}
 .wrap{width:min(680px,92vw);text-align:center;padding:34px 0}
 h1{font-size:clamp(24px,4vw,34px);margin:0 0 10px;font-weight:800}
 p{color:#9fb0cc;margin:0 0 26px;font-size:15px;line-height:1.8}
 .drop{position:relative;border:2px dashed #33406b;border-radius:26px;
   background:linear-gradient(180deg,rgba(30,38,70,.55),rgba(12,16,32,.55));
   padding:56px 24px;transition:.2s;cursor:pointer}
 .drop.hot{border-color:#22d3ee;background:rgba(34,211,238,.08);transform:translateY(-2px)}
 .drop b{display:block;font-size:19px;margin-bottom:8px}
 .drop span{color:#7f90ae;font-size:14px}
 .bar{height:8px;border-radius:99px;background:#1b2440;overflow:hidden;margin-top:22px;display:none}
 .bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#22d3ee,#a78bfa);
   transition:width .15s}
 .ok{margin-top:20px;color:#5eead4;font-weight:700;display:none}
 .err{color:#fca5a5;margin-top:14px;display:none}
 .meta{margin-top:26px;color:#64748b;font-size:12.5px;line-height:1.9}
 input{display:none}
</style></head><body><div class="wrap">
 <h1>ارفع الملف الصوتي</h1>
 <p>اسحب الـ MP3 هنا أو اضغط للاختيار — الملف بيتحفظ جوه مساحة العمل عندي على طول.</p>
 <label class="drop" id="drop">
   <input type="file" id="file" accept="audio/*,video/mp4">
   <b>اسحب الملف هنا</b><span>MP3 · WAV · M4A · حتى 200 ميجا</span>
   <div class="bar" id="bar"><i></i></div>
   <div class="ok" id="ok"></div>
   <div class="err" id="err"></div>
 </label>
 <div class="meta">بعد الرفع قول لي في الشات: «رفعت الملف» — وأنا بكمّل التفريغ والموشن على طول.</div>
</div>
<script>
const drop=document.getElementById('drop'), inp=document.getElementById('file');
const bar=document.getElementById('bar'), ok=document.getElementById('ok'), err=document.getElementById('err');
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('hot')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('hot')}));
drop.addEventListener('drop',ev=>{const f=ev.dataTransfer.files[0]; if(f) send(f);});
inp.addEventListener('change',()=>{if(inp.files[0]) send(inp.files[0]);});
function send(f){
  ok.style.display='none'; err.style.display='none'; bar.style.display='block';
  const xhr=new XMLHttpRequest();
  xhr.open('POST','/upload?name='+encodeURIComponent(f.name));
  xhr.upload.onprogress=e=>{ if(e.lengthComputable) bar.firstElementChild.style.width=(100*e.loaded/e.total)+'%'; };
  xhr.onload=()=>{ const r=JSON.parse(xhr.responseText||'{}');
    if(xhr.status===200){ ok.textContent='تم رفع '+r.name+' ('+(r.size/1048576).toFixed(1)+' ميجا) ✓'; ok.style.display='block'; }
    else { err.textContent='حصل خطأ: '+(r.error||xhr.status); err.style.display='block'; } };
  xhr.onerror=()=>{ err.textContent='فشل الاتصال بالسيرفر'; err.style.display='block'; };
  xhr.send(f);
}
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console readable
        sys.stderr.write("%s\n" % (fmt % args))

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/health":
            self._send(200, '{"ok":true}')
        else:
            self._send(404, '{"error":"not found"}')

    def do_POST(self):
        if not self.path.startswith("/upload"):
            return self._send(404, '{"error":"not found"}')
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(self.path).query)
        name = os.path.basename(q.get("name", ["voice.mp3"])[0]) or "voice.mp3"
        if not name.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg", ".mp4", ".opus")):
            return self._send(400, '{"error":"امتداد غير مدعوم"}')
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0:
            return self._send(400, '{"error":"ملف فاضي"}')
        dst = os.path.join(INDIR, name)
        left = n
        with open(dst, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        size = os.path.getsize(dst)
        print(f"[upload] {dst} ({size/1048576:.1f} MB)", flush=True)
        self._send(200, '{"name":%s,"size":%d}' % (__import__("json").dumps(name), size))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"upload page on http://0.0.0.0:{port}", flush=True)
    srv.serve_forever()
