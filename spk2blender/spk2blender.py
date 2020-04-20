import bpy, io, math, mathutils, os, struct, sys

def readpack(inputfile, fmt):
    return struct.unpack("<" + fmt, inputfile.read(struct.calcsize("<" + fmt)))

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

#defaultfilename = "C:\\Users\\Adrien\\Downloads\\47mod\\C1_1_HitmanArrive\\Pack.SPK"
defaultfilename = "C:\\Users\\Adrien\\Downloads\\47mod\\C1_1\\old\\Pack.SPK"
#spkfile = open(defaultfilename if (len(sys.argv) <= 1) else sys.argv[1], "rb")
spkfile = open(defaultfilename, "rb")

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

prot = root.FindSubchunk(b"PROT")
pclp = root.FindSubchunk(b"PCLP")
if (prot != None) and (pclp != None):
    phea = root.FindSubchunk(b"PHEA").Read()
    pnam = root.FindSubchunk(b"PNAM").Read()
    ppos = root.FindSubchunk(b"PPOS").Read()
    #pdbl = root.FindSubchunk(b"PDBL").Read()
    #pftx = root.FindSubchunk(b"PFTX").Read()
    pver = root.FindSubchunk(b"PVER").Read()
    pfac = root.FindSubchunk(b"PFAC").Read()
    pmtx = root.FindSubchunk(b"PMTX").Read()
    
    mshdict = {}
    
    def EnumProt(p, tnode):
        heado, = struct.unpack("<I", p.tag)
        heado &= 0xFFFFFF
        nameo, = struct.unpack("<I", phea[(heado+8):(heado+12)])
        s = ""
        c = 1
        o = nameo
        while 1:
            c = pnam[o]
            if c == 0: break
            s += chr(c)
            o += 1
            
        o = heado
        objtype,objflags = struct.unpack("<HH", phea[o+20:o+24])
        mtxo,po, = struct.unpack("<II", phea[o+12:o+20])
        position = struct.unpack("<fff", ppos[po:po+12])
        bmtx = struct.unpack("<4i", pmtx[mtxo*16:mtxo*16+16])
        
        # Mesh
        mesh = None
        if objflags & 0x0020:
            vertstart,quadstart,tristart,ftxo,numverts,numquads,numtris = struct.unpack("<7I", phea[o+0x18:o+0x34])
            if ((numquads != 0) or (numtris != 0)) and (numverts != 0):
                mdv = mshdict.get((vertstart,quadstart,tristart,numverts))
                if mdv != None:
                    mesh = mdv
                else:
                    lstvert = []
                    lstpoly = []
                    #print(s)
                    assert numverts >= 3
                    for i in range(numverts):
                        a = vertstart*4+i*12
                        u = struct.unpack("<fff", pver[a:a+12])
                        lstvert.append((u[0],u[2],u[1]))
                    for i in range(numquads):
                        a = (quadstart+i*4)*2
                        lstpoly.append([x//2 for x in struct.unpack("<4H", pfac[a:a+8])])
                    for i in range(numtris):
                        a = (tristart+i*3)*2
                        lstpoly.append([x//2 for x in struct.unpack("<3H", pfac[a:a+6])])
                    #print(lstpoly)
                    mesh = bpy.data.meshes.new(s + "_Mesh")
                    #mesh.from_pydata(lstvert, [], [[(b//2) for b in a] for a in lstvert])
                    #mesh.from_pydata(lstvert, [], [[0,1,2]])
                    mesh.from_pydata(lstvert, [], lstpoly)
                    mshdict[(vertstart,quadstart,tristart,numverts)] = mesh

        bobj = bpy.data.objects.new(s, mesh)
        bpy.context.scene.objects.link(bobj)
        if tnode != None:
            bobj.parent = tnode
        
        mx = 3*[None]
        for i in range(2):
            #mx[i] = mathutils.Vector((0, bmtx[i*2+1] / (2**30), bmtx[i*2] / (2**30)))
            mx[i] = mathutils.Vector((bmtx[i*2] / (2**30), bmtx[i*2+1] / (2**30), 0))
            mx[i].z = 1 - (mx[i].x**2) - (mx[i].y**2)
            if bmtx[i*2] & 1:
                mx[i].z = -mx[i].z
        mx[2] = -mx[0].cross(mx[1])
        mx[0],mx[2] = mx[2],mx[0]
        #for i in range(3):
        #    mx[i].xyz = mx[i].xzy
        mb = mathutils.Matrix.Identity(3)
        myz = mathutils.Matrix(((1,0,0),(0,0,1),(0,1,0)))
        for i in range(3):
            mb.row[i] = mx[i]
        mb.transpose()
        bobj.matrix_basis = (myz*mb*myz).to_4x4()
        
        if s in ("Buddha", "Car"):
            print(s, ":\n", mb.to_4x4())
        
        bobj.location.xzy = position
        #bobj.rotation_mode = "XYZ"
        #print(bmtx[3])
        #bobj.rotation_euler.z = bmtx[3] * 2 * math.pi / 255
        for c in p.children:
            EnumProt(c, bobj)

    for p in (prot, pclp):
        e = bpy.data.objects.new(p.tag.decode(), None)
        bpy.context.scene.objects.link(e)
        for c in p.children:
            EnumProt(c, e)

spkfile.close()
