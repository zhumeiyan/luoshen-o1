import socket, os, struct, time, sys

# 1) 真实 UDP 高频往返丢包率
def udp_probe(n=400):
    a=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); a.bind(('127.0.0.1',0))
    b=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); b.bind(('127.0.0.1',0))
    pa=a.getsockname(); pb=b.getsockname()
    a.settimeout(0.05); b.settimeout(0.05)
    sent=0; recvb=0
    for i in range(n):
        a.sendto(struct.pack('<Qq',i,time.time_ns()),pb)
        sent+=1
        try:
            b.recvfrom(64); recvb+=1
        except socket.timeout:
            pass
    print('UDP n=%d recv=%d loss=%.4f'%(sent,recvb,1-recvb/sent))
    a.close(); b.close()
    return 1-recvb/sent

# 2) 真实文件同槽竞争：两进程 read-modify-write 同一偏移，看丢失率
def race_probe(n=300):
    path='race_probe.bin'
    with open(path,'wb') as f: f.write(struct.pack('<q',0))
    pid=os.fork()
    if pid==0:
        f=os.open(path,os.O_RDWR)
        for i in range(n):
            os.lseek(f,0,os.SEEK_SET)
            v=struct.unpack('<q',os.read(f,8))[0]
            os.lseek(f,0,os.SEEK_SET); os.write(f,struct.pack('<q',v+1))
        os.close(f); os._exit(0)
    else:
        f=os.open(path,os.O_RDWR)
        for i in range(n):
            os.lseek(f,0,os.SEEK_SET)
            v=struct.unpack('<q',os.read(f,8))[0]
            os.lseek(f,0,os.SEEK_SET); os.write(f,struct.pack('<q',v+1))
        os.close(f)
        os.waitpid(pid,0)
        with open(path,'rb') as g: tot=struct.unpack('<q',g.read(8))[0]
        print('RACE expect=%d got=%d lost=%d rate=%.4f'%(2*n,tot,2*n-tot,(2*n-tot)/(2*n)))
        return (2*n-tot)/(2*n)

if __name__=='__main__':
    l=udp_probe()
    r=race_probe()
    print('PROBE loss=%.5f race=%.5f'%(l,r))
