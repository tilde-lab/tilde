
# Electron structure container
# Author: Evgeny Blokhin
# spin account : TODO

BAND_GAP_BOUNDARY = 50 # all values are in eV

class ElectronStructureError(Exception):
    def __init__(self, value):
        self.value = value

class Ebands():
    def __init__(self, obj):
        self.abscissa = obj['abscissa']
        self.stripes = obj['stripes']
        self.ticks = obj['ticks']

    def is_conductor(self):
        for s in self.stripes:
            top, bottom = max(s), min(s)
            if bottom < 0 and top > 0: return True
            elif bottom > 0: break
        return False

    def get_bandgap(self):
        for n in range(1, len(self.stripes)):
            top, bottom = max(self.stripes[n]), min(self.stripes[n])
            if bottom > 0:
                lvb = max(self.stripes[n-1])
                if lvb < bottom:
                    homok = self.abscissa[ self.stripes[n-1].index(lvb) ]
                    lumok = self.abscissa[ self.stripes[n].index(bottom)]
                    gap = bottom - lvb
                    if gap > BAND_GAP_BOUNDARY: raise ElectronStructureError("Unphysical band gap occured!")
                    return gap, homok == lumok
                else:
                    return (0.0, None)
        raise ElectronStructureError("Unexpected data in band structure: no bands above zero found!")

    def todict(self):
        return {'abscissa': self.abscissa, 'ticks': self.ticks, 'stripes': self.stripes}

class Edos():
    def __init__(self, obj):
        self.abscissa = obj['x']
        self.alldos = obj['total']
        self.properties = {}
        for key in list(obj.keys()):
            if key not in ['x', 'total']: self.properties[key] = obj[key]

    def get_bandgap(self):
        dim = len(self.abscissa)
        for n in range(1, dim):
            if self.abscissa[n] > 0:
                if self.alldos[n] > 0: return 0.0
                k, t = n, n
                while self.alldos[k] == 0:
                    k += 1
                    if k > dim-1: raise ElectronStructureError("Unexpected data in band structure: no values above zero found!")
                while self.alldos[t] == 0:
                    t -= 1
                    if t==0: raise ElectronStructureError("Unexpected data in band structure: not enough eigenvalues to determine the band gap!")
                gap = self.abscissa[k] - self.abscissa[t]
                if gap > BAND_GAP_BOUNDARY: raise ElectronStructureError("Unphysical band gap occured!")
                return gap

    def todict(self):
        rep = {'x': self.abscissa, 'total': self.alldos}
        for prop in self.properties:
            rep.update({prop: self.properties[prop]})
        return rep
