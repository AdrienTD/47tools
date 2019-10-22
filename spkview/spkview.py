# spkview - Hitman C47 SPK viewer / explorer, for research purposes
# (C) 2018 AdrienTD
# Licensed under the MIT license.
# See LICENSE file at the root of the repository.

import ctypes, io, os, struct, sys, wx

#ctypes.windll.user32.SetProcessDPIAware()

def readpack(inputfile, fmt):
    return struct.unpack("<" + fmt, inputfile.read(struct.calcsize("<" + fmt)))

def hexline(f, data, o):
    f.write("%08X " % o)
    for i in range(16):
        if i < len(data):
            f.write("%02X " % data[i])
        else:
            f.write("   ")
    for i in range(16):
        if i < len(data):
            #if data[i:i+1].isalnum():
            if 0x20 <= data[i] <= 0x7E:
                f.write(chr(data[i]))
            else:
                f.write(".")
    f.write("\n")

def hexdump(f, data):
    siz = len(data)
    lines = (siz // 16) + (1 if (siz & 15) else 0)
    for i in range(siz // 16):
        hexline(f, data[i*16:i*16+16], i*16)
    if siz & 15:
        hexline(f, data[(siz//16)*16:siz], (siz//16)*16)

class Chunk:
    def __init__(self):
        self.tag = b"No:("
        self.haschildren = False
        self.hasmultidata = False
        self.children = []
    def FindSubchunk(self, tagtofind):
        for c in self.children:
            if c.tag == tagtofind:
                return c
        return None
    def Read(self):
        # Assuming chunk has no child nor multidata
        self.file.seek(self.offset+8, os.SEEK_SET)
        return self.file.read(self.size-8)

objtypenames = {
0x01: "ZGROUP",
0x02: "ZSTDOBJ",
0x03: "ZCAMERA",
0x12: "ZSNDOBJ",
0x1A: "ZLIST",
0x21: "ZROOM",
0x23: "ZSPOTLIGHT",
0x27: "ZIKLNKOBJ",
0x2C: "ZWINOBJ",
0x2D: "ZCHAROBJ",
0x2E: "ZWINGROUP",
0x30: "ZWINDOWS",
0x31: "ZWINDOW",
0x3A: "ZTTFONT"}

defaultfilename = "C:\\Users\\Adrien\\Downloads\\47mod\\C1_1_HitmanArrive\\Pack.SPK"
#defaultfilename = "C:\\Users\\Adrien\\Downloads\\47mod\\C1_1\\old\\Pack.SPK"
spkfile = open(defaultfilename if (len(sys.argv) <= 1) else sys.argv[1], "rb")

def EnumChunk(chk):
    o = spkfile.tell()

    chktype, chkinfo = readpack(spkfile, "4sI")
    chktypeint, = struct.unpack("<I", chktype)

    if chktype.isalnum():
        chktypestr = chktype.decode()
    else:
        chktypestr = str(chktype)

    chksize = chkinfo & 0x3FFFFFFF
    hassub = (chkinfo & 0x80000000) != 0
    hasmultidata = (chkinfo & 0x40000000) != 0

    chk.tag = chktype
    chk.string = chktypestr
    chk.offset = o
    chk.size = chksize
    chk.haschildren = hassub
    chk.hasmultidata = hasmultidata
    chk.children = []
    chk.file = spkfile

    #e = None
    #if root == None:
    #    e = tree.AddRoot(chktypestr)
    #else:
    #    e = tree.AppendItem(root, chktypestr)
    #tree.SetItemData(e, o)
    
    if hassub:
            siz2, nchunks = readpack(spkfile, "II")
            if hasmultidata:
                ndatas, = readpack(spkfile, "I")
                spkfile.seek(4*ndatas, os.SEEK_CUR)
            for i in range(nchunks):
                c = Chunk()
                EnumChunk(c)
                chk.children.append(c)
    elif chktype == b"PEXC":
        while spkfile.tell() < (o + chksize):
            c = Chunk()
            EnumChunk(c)
            chk.children.append(c)
    spkfile.seek(o + chksize, os.SEEK_SET)

root = Chunk()
EnumChunk(root)

app = wx.App()

frm = wx.Frame(None, title="SPK Viewer", size=(960,600))
notebook = wx.Notebook(frm)
split1 = wx.SplitterWindow(notebook, style=wx.SP_LIVE_UPDATE|wx.SP_3D)
tree = wx.TreeCtrl(split1)
ebox = wx.TextCtrl(split1, value=":)", style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
ebox.SetFont(wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

e = tree.AddRoot(root.string)
tree.SetItemData(e, root.offset)
def InsertTreeNodes(r, tnode):
    for c in r.children:
        e = tree.AppendItem(tnode, c.string)
        tree.SetItemData(e, c.offset)
        InsertTreeNodes(c, e)
InsertTreeNodes(root, e)

tree.Expand(tree.GetRootItem())
split1.SplitVertically(tree, ebox, 150)

split2 = wx.SplitterWindow(notebook, style=wx.SP_LIVE_UPDATE|wx.SP_3D)
tree2 = wx.TreeCtrl(split2)
prot = root.FindSubchunk(b"PROT")
pclp = root.FindSubchunk(b"PCLP")
if (prot != None) and (pclp != None):
    phea = root.FindSubchunk(b"PHEA").Read()
    pnam = root.FindSubchunk(b"PNAM").Read()
    ppos = root.FindSubchunk(b"PPOS").Read()
    pdbl = root.FindSubchunk(b"PDBL").Read()
    pftx = root.FindSubchunk(b"PFTX").Read()
    pver = root.FindSubchunk(b"PVER").Read()
    pfac = root.FindSubchunk(b"PFAC").Read()
    pmtx = root.FindSubchunk(b"PMTX").Read()
    puvc = root.FindSubchunk(b"PUVC").Read()
    hexdump(sys.stdout, phea[0:32])
    objid = 0
    
    def EnumProt(p, tnode):
        global objid
        objid += 1
        heado, = struct.unpack("<I", p.tag)
        stat = heado >> 24
        heado &= 0xFFFFFF
        #print("%X" % heado)
        nameo, = struct.unpack("<I", phea[(heado+8):(heado+12)])
        #print("%X, %X" % (heado, nameo))
        s = ""
        c = 1
        o = nameo
        while 1:
            c = pnam[o]
            if c == 0: break
            s += chr(c)
            o += 1
        e = tree.AppendItem(tnode, "%s (id %i, fl %i)" % (s,objid,stat)) #"%08X" % heado)
        tree.SetItemData(e, heado)
        for c in p.children:
            EnumProt(c, e)

    trt = tree2.AddRoot("SPK")
    for p in (pclp, prot):
        e = tree2.AppendItem(trt, p.string)
        for c in p.children:
            EnumProt(c, e)

ebox2 = wx.TextCtrl(split2, value=":)", style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
ebox2.SetFont(wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
#tree2.Expand(tree2.GetRootItem())
split2.SplitVertically(tree2, ebox2, 290)

notebook.AddPage(split1, "Chunk explorer")
notebook.AddPage(split2, "Object explorer")

def WriteChunkInfo(f):
    o = spkfile.tell()
    chktype, chkinfo = readpack(spkfile, "4sI")
    chksize = chkinfo & 0x3FFFFFFF
    hassub = (chkinfo & 0x80000000) != 0
    hasmultidata = (chkinfo & 0x40000000) != 0
    f.write("Offset: 0x%08X\n" % o)
    f.write("Format: %s\n" % str(chktype))
    f.write("Size: %u bytes (0x%X)\n" % (chksize, chksize))
    f.write("Flags:")
    if hassub: f.write(" CHILDREN")
    if hasmultidata: f.write(" MULTIDATA")
    f.write("\n")
    if (not hasmultidata):
        f.write("\nData:\n")
        if hassub:
            childsiz, = readpack(spkfile, "I")
            spkfile.seek(o+childsiz, os.SEEK_SET)
            hexdump(f, spkfile.read(chksize - childsiz))
        else:
            hexdump(f, spkfile.read(chksize-8))
    else:
        childsiz, = readpack(spkfile, "I")
        if hassub:
            nchk = readpack(spkfile, "I")
        ndatas, = readpack(spkfile, "I")
        datsiz = []
        for i in range(ndatas):
            datsiz.append(readpack(spkfile, "I")[0])
        spkfile.seek(o+childsiz, os.SEEK_SET)
        for i in range(ndatas):
            f.write("\nData %i\n" % i)
            hexdump(f, spkfile.read(datsiz[i]))

def selchunkchanged(event):
    o = tree.GetItemData(event.GetItem())
    spkfile.seek(o, os.SEEK_SET)
    ebox.Clear()
    t = io.StringIO()
    WriteChunkInfo(t)
    t.seek(0, os.SEEK_SET)
    ebox.SetValue(t.read())

tree.Bind(wx.EVT_TREE_SEL_CHANGED, selchunkchanged)

maxheav = 16 * [0,]
parheav = 16 * [0,]
maxftxv = 3 * [0,]

def selentitychanged(event):
    o = tree2.GetItemData(event.GetItem())
    if o != None:
        t = io.StringIO()
        t.write("Head offset (in PHEA): %08X\n" % o)
        dblo, = struct.unpack("<I", phea[o:o+4])
        t.write("PDBL data offset: %08X\n" % dblo)
        t.write("PEXC data offset: %08X\n" % struct.unpack("<I", phea[o+4:o+8]))
        t.write("Name: %s\n" % tree.GetItemText(event.GetItem()))
        mo,po, = struct.unpack("<II", phea[o+12:o+20])
        mo <<= 4
        cmx = struct.unpack("<4i", pmtx[mo:mo+16])
        t.write("Matrix: (%f, %f, %f, %f) @ 0x%08X\n" % tuple( [x/(2**30) for x in cmx] + [mo,]))
        t.write("Position: (%f, %f, %f)\n" % struct.unpack("<fff", ppos[po:po+12]))
        objtype,objflags = struct.unpack("<HH", phea[o+20:o+24])
        t.write("Type: %s (0x%X)\n" % (objtypenames.get(objtype, "?"), objtype))
        t.write("Flags: 0x%04X\n" % objflags)
        #t.write("\nPHEA dump:\n")
        #hexdump(t, phea[o:o+64])
        t.write("\nPDBL dump:\n")
        dblsiz, = struct.unpack("<I", pdbl[dblo:dblo+4])
        dblsiz &= 0x00FFFFFF
        hexdump(t, pdbl[dblo:dblo+dblsiz])
        t.write("\nPDBL:\n")
        dd = dblo+4
        while dd < dblo+dblsiz:
            dt = pdbl[dd] & 0x3F
            t.write("0x%02X: " % pdbl[dd])
            dd += 1
            if dt == 1:
                t.write("Double: %f\n" % struct.unpack("<d", pdbl[dd:dd+8]))
                dd += 8
            elif dt == 2:
                t.write("Float: %f\n" % struct.unpack("<f", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 3:
                t.write("Integer: %i\n" % struct.unpack("<i", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 4:
                t.write("String: ")
                while pdbl[dd] != 0:
                    t.write(chr(pdbl[dd]))
                    dd += 1
                dd += 1
                t.write("\n")
            elif dt == 5:
                t.write("FN String: ")
                while pdbl[dd] != 0:
                    t.write(chr(pdbl[dd]))
                    dd += 1
                dd += 1
                t.write("\n")
            elif dt == 6:
                t.write("---- Separator ----\n")
            elif dt == 7:
                s, = struct.unpack("<I", pdbl[dd:dd+4])
                t.write("Data: %u bytes\n" % (s-4))
                dd += s
            elif dt == 8:
                t.write("Object: %i\n" % struct.unpack("<i", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 9:
                s, = struct.unpack("<I", pdbl[dd:dd+4])
                t.write("9 Data: %u bytes\n" % (s-4))
                dd += s
            elif dt == 0xA:
                t.write("A Integer: %i\n" % struct.unpack("<i", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 0xB:
                t.write("B Integer: %i\n" % struct.unpack("<i", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 0xC:
                t.write("C Integer: %i\n" % struct.unpack("<i", pdbl[dd:dd+4]))
                dd += 4
            elif dt == 63:
                t.write("-------- End --------\n")
                #break
            else:
                t.write("Unknown type %u\n" % dt)
                
        t.write("\n3x3 rotation matrix:\n")
        dmx = [[0]*3,[0]*3,[0]*3]
        for i in range(2):
            dmx[i][0] = cmx[i*2]   / (2**30)
            dmx[i][1] = cmx[i*2+1] / (2**30)
            dmx[i][2] = 1 - dmx[i][0]**2 - dmx[i][1]**2
            if cmx[i*2] & 1:
                dmx[i][2] = -dmx[i][2]
        def crossproduct(a, b):
            r = [0,0,0]
            r[0] = a[1]*b[2] - a[2]*b[1]
            r[1] = a[2]*b[0] - a[0]*b[2]
            r[2] = a[0]*b[1] - a[1]*b[0]
            return r
        dmx[2] = dmx[0]
        dmx[0] = crossproduct(dmx[1], dmx[2])
        for row in dmx:
            t.write("%s\n" % str(row))
        #if objtype in (2, 0x27): # ZSTDOBJ or ZIKLNKOBJ
        if objflags & 0x0020:
            t.write("\nPHEA Model info:\n")
            vertstart,quadstart,tristart,ftxo,numverts,numquads,numtris = struct.unpack("<7I", phea[o+0x18:o+0x34])
            t.write("Vertex start index: %u\n" % vertstart)
            t.write("Quads start index: %u\n" % quadstart)
            t.write("Tris start index: %u\n" % tristart)
            t.write("Number of vertices: %u\n" % numverts)
            t.write("Number of quads: %u\n" % numquads)
            t.write("Number of tris: %u\n" % numtris)
            if ftxo != 0:
                pass
                t.write("\nPFTX dump:\n")
                hexdump(t, pftx[ftxo-1:ftxo-1+64])
##                t.write("\nPFTX Val,Max:\n")
##                ftxv = struct.unpack("<3I", pftx[ftxo-1:ftxo-1+12])
##                for i in range(3):
##                    if ftxv[i] > maxftxv[i]:
##                        maxftxv[i] = ftxv[i]
##                    t.write("%02X: %08X, %08X\n" % (i*4, ftxv[i], maxftxv[i]))
##                uo,uo2,nfaces, = struct.unpack("<3I", pftx[ftxo-1:ftxo-1+12])
                #t.write("\nPFTX %i faces:\n" % nfaces)
                #for i in range(nfaces):
                #    hexdump(t, pftx[ftxo-1+12+12*i:ftxo-1+12+12*i+12])
##                t.write("\nUV coordinates:\n")
##                for i in range(nfaces):
##                    for j in range(4):
##                        puvcoff = uo*4+(i*4+j)*8
##                        t.write(str(struct.unpack("<2f", puvc[puvcoff:puvcoff+8])))
##                        t.write("\n")
                
##            t.write("\nPHEA Val,Max,Par:\n")
##            heav = struct.unpack("<16I", phea[o:o+16*4])
##            for i in range(16):
##                if heav[i] > maxheav[i]:
##                    maxheav[i] = heav[i]
##                if heav[i] != 0:
##                    if heav[i] & 1: parheav[i] |= 1
##                    else: parheav[i] |= 2
##                t.write("%02X: %08X, %08X, parity: %i\n" % (i*4, heav[i], maxheav[i], parheav[i]))
##            t.write("\nOBJ conversion:\n")
##            for v in range(numverts):
##                crd = struct.unpack("<fff", pver[vertstart*4+v*12:vertstart*4+v*12+12])
##                t.write("v %f %f %f\n" % crd)
##            for i in range(numquads):
##                f = struct.unpack("<4H", pfac[(quadstart+i*4)*2:(quadstart+i*4+4)*2])
##                l = []
##                for j in range(4):
##                    l.append((f[j] // 2) + 1)
##                t.write("f %u %u %u %u\n" % tuple(l))
##            for i in range(numtris):
##                f = struct.unpack("<3H", pfac[(tristart+i*3)*2:(tristart+i*3+3)*2])
##                l = []
##                for j in range(3):
##                    l.append((f[j] // 2) + 1)
##                t.write("f %u %u %u\n" % tuple(l))
        t.seek(0, os.SEEK_SET)
        ebox2.SetValue(t.read())

tree2.Bind(wx.EVT_TREE_SEL_CHANGED, selentitychanged)

def maxIndexClick(event):
    chkpfac = root.FindSubchunk(b"PFAC")
    pfac = chkpfac.Read()
    s = len(pfac) // 2
    a = []
    for i in range(s):
        a.append(struct.unpack("<H", pfac[2*i:2*i+2])[0])
    for i in range(3):
        print(max(a[i::3]))

def getObjHeaSiz(event):
    hos = set()
    szs = set()
    
    def gohs_obj(o):
        nonlocal hos
        #print(hos)
        hos |= {struct.unpack("<I", o.tag)[0] & 0xFFFFFF}
        for c in o.children:
            gohs_obj(c)

    for rt in (prot, pclp):
        for c in rt.children:
            gohs_obj(c)

    sl = sorted(list(hos))
    lnsl = len(sl)
    for i in range(lnsl):
        #print("%08X" % i)
        p = sl[i] #& 0xFFFFFF
        nameo, = struct.unpack("<I", phea[p+8:p+12])
        oty,fl = struct.unpack("<HH", phea[p+20:p+24])
        o = nameo
        s = ""
        while 1:
            c = pnam[o]
            if c == 0: break
            s += chr(c)
            o += 1
        if i < lnsl-1:
            hsz = sl[i+1] - p
        elif i == lnsl-1:
            hsz = len(phea) - p
        szs |= {hsz}
        print("%s(%i)::%s, Flags %04X, @ %08X\nSize: %i" % (objtypenames.get(oty, "?"), oty, s, fl, sl[i], hsz))
    print("Number of headers: %u" % len(sl))
    print("Header sizes found:")
    print(szs)

def countPFTXFaces(event):
    totalfaces = 0
    p = 0
    lg = len(pftx)
    mmin = 6 * [ 32767]
    mmax = 6 * [-32768]
    while p < lg:
        v1,v2,nfaces = struct.unpack("<III", pftx[p:p+12])
        totalfaces += nfaces
        p += 12
        for i in range(nfaces):
            s = struct.unpack("<6h", pftx[p:p+12])
            mmin = [min(mmin[i],s[i]) for i in range(6)]
            mmax = [max(mmax[i],s[i]) for i in range(6)]
            p += 12
    print("Total faces: ", totalfaces)
    print("Value min: ", mmin)
    print("Value max: ", mmax)

def readStrFromPNAM(nameo):
    s = ""
    c = 1
    o = nameo
    while 1:
        c = pnam[o]
        if c == 0: break
        s += chr(c)
        o += 1
    return s

def enumDupObj(event):
    ds = set()
    dups = dict()
    def edo_obj(o):
        u, = struct.unpack("<I", o.tag)
        t = u & 0xFFFFFF
        np, = struct.unpack("<I", phea[t+8:t+12])
        name = readStrFromPNAM(np)
        #print(t, name)
        if(t in ds):
            dups[t] = name
        #    print("Dup found!")
        ds.add(t)
        for c in o.children:
            edo_obj(c)
    for p in (prot,pclp):
        for c in p.children:
            edo_obj(c)
    for d in dups:
        print(hex(d), dups[d])

chunkmenu = wx.Menu()
chunkmenu.Append(0, "Max index")
chunkmenu.Append(1, "Get obj header sizes")
chunkmenu.Append(2, "Count PFTX faces")
chunkmenu.Append(3, "Enumerate duplicate objects")
menubar = wx.MenuBar()
menubar.Append(chunkmenu, "Tools")
frm.SetMenuBar(menubar)

frm.Bind(wx.EVT_MENU, maxIndexClick, id=0)
frm.Bind(wx.EVT_MENU, getObjHeaSiz, id=1)
frm.Bind(wx.EVT_MENU, countPFTXFaces, id=2)
frm.Bind(wx.EVT_MENU, enumDupObj, id=3)

frm.Show()

app.MainLoop()
