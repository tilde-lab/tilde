
# Bilbao server symmetry XML extractor

import os, sys
import urllib2
from xml.etree import ElementTree as ET

BASE_URL = 'http://cryst.ehu.es/cgi-bin/cryst/xml/nph-get_doc?p=wpos&g='

try: workpath = sys.argv[1]
except IndexError:
    print 'Grabbing Bilbao server...'
    f = open('bilbao.xml', 'w')

    f.write("<?xml version='1.0' encoding='utf8'?>\n<root>\n")

    for i in range(1, 231):
        i = str(i)
        try: xml = urllib2.urlopen(BASE_URL + i).read()
        except urllib2.URLError: print 'Cannot parse SG' + i + ', ' + BASE_URL + i
        else:
            try: tree = ET.ElementTree(ET.fromstring(xml))
            except: print 'Malformed output for SG' + i + ', ' + BASE_URL + i
            else:
                #print xml, "\n\n"
                doc = tree.getroot()
                group = doc.find('group')
                N = group.attrib['number']
                wpos = group.find('wpos')
                wpos.attrib['number'] = N
                xmlstr = ET.tostring(wpos)
                f.write(xmlstr + "\n")
                doc.clear()
                group.clear()
                wpos.clear()
    f.write('</root>\n')
    f.close()

else:
    print 'Working with Bilbao server data...'
    tree = ET.parse(workpath)
    doc = tree.getroot()
    for elem in doc.findall('wpos'):
        print "="*100
        print elem.attrib['number']
        for pos in elem.findall('position'):
            for xyz in pos.findall('xyz'):
                print xyz.text
