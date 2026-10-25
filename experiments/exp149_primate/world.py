import os, struct
NSLOT=8
PATH=None
def init(path):
    global PATH
    PATH=path
    with open(path,'wb') as f: f.write(struct.pack('<8i',*[0]*NSLOT))
def read():
    with open(PATH,'rb') as f: return list(struct.unpack('<8i',f.read(32)))
def bump(slot):
    """真 RMW：read-modify-write，两个进程同槽会真实 race"""
    fd=os.open(PATH,os.O_RDWR)
    try:
        os.lseek(fd,slot*4,os.SEEK_SET)
        v=struct.unpack('<i',os.read(fd,4))[0]
        os.lseek(fd,slot*4,os.SEEK_SET)
        os.write(fd,struct.pack('<i',v+1))
    finally:
        os.close(fd)
