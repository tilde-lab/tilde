
# Tilde project: electron structure container
# v301113

# spin account : TODO

import os, sys

class Ebands():
    def __init__(self, obj):
        self.abscissa = obj['abscissa']
        self.stripes = obj['stripes']
        self.ticks = obj['ticks']
        
    def is_metal(self):
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
                    return (bottom - lvb, homok == lumok)
                else:
                    return (0.0, None)
                    
    def todict(self):
        return {'abscissa': self.abscissa, 'ticks': self.ticks, 'stripes': self.stripes}

class Edos():
    def __init__(self, obj):
        self.abscissa = obj['x']
        self.alldos = obj['total']
        self.properties = {}
        for key in obj.keys():
            if key not in ['x', 'total']: self.properties[key] = obj[key]
    
    def get_bandgap(self):
        dim = len(self.abscissa)
        for n in range(1, dim):
            if self.abscissa[n] > 0:
                if self.alldos[n] > 0: return 0.0
                k, t = n, n
                while self.alldos[k] == 0:
                    k += 1                  
                    if k > dim: raise RuntimeError("Unexpected data in band structure!")
                while self.alldos[t] == 0:
                    t -= 1                  
                    if t==0: raise RuntimeError("Unexpected data in band structure!")
                return self.abscissa[k] - self.abscissa[t]
        
    def todict(self):
        rep = {'x': self.abscissa, 'total': self.alldos}
        for prop in self.properties:
            rep.update({prop: self.properties[prop]})
        return rep
