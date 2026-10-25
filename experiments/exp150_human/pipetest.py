import os, json, fcntl
r,w = os.pipe()
fcntl.fcntl(r, fcntl.F_SETFL, os.O_NONBLOCK)
fcntl.fcntl(w, fcntl.F_SETFL, os.O_NONBLOCK)
os.write(w, json.dumps({"kind":"plan","plan":["A","B","C"]}).encode())
print("after write, read ->", os.read(r, 4096))
try:
    os.read(r, 4096)
except BlockingIOError:
    print("second read: BlockingIOError (empty) -> OK, pipe is FIFO not echo")
os.close(r); os.close(w)
print("pipe works as memory channel: write once, read back earlier content")
