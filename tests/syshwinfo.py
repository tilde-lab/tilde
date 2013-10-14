#!/usr/bin/python

"""
Copyright (c) 2006, 2007, 2008, 2009, 2011, 2012 Janne Blomqvist

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


Print out some data about hardware.

"""

version = "2.1.1"

import os, platform, socket, sys, csv, datetime

def meminfo():
    """Get the amount of memory and swap, Mebibytes"""
    f = open("/proc/meminfo")
    hwinfo = {}
    for line in f.readlines():
        meml = line.split()
        if (meml[0] == "MemTotal:"):
            mem = int(meml[1])
            hwinfo["Mem_MiB"] = mem/1024
        elif (meml[0] == "SwapTotal:"):
            swap = int(meml[1])
            hwinfo["Swap_MiB"] = swap/1024
    f.close()
    return hwinfo

def cpuinfo():
    """Get the cpu info"""
    f = open("/proc/cpuinfo")
    hwinfo = {}
    for line in f.readlines():
        cpul = line.split(":")
        name = cpul[0].strip()
        if (len(cpul) > 1):
            val = cpul[1].strip()
        if (name == "model name"):
            hwinfo["CPU"] = val
        elif (name == "cpu MHz"):
            hwinfo["MHz"] = int(round(float(val)))
    f.close()
    return hwinfo

def uname():
    """Get the architecture"""
    uname = os.uname()
    return {"Arch":uname[4], "Kernel":uname[2]}

def vgadata():
    """Get data about the graphics card."""
    if os.path.isfile('/sbin/lspci'):
        lspci = '/sbin/lspci'
    else:
        lspci = '/usr/bin/lspci'
    f = os.popen (lspci + ' -m')
    pdata = {}
    for line in f.readlines():
        p = line.split("\"")
        name = p[1].strip()
        if (name == "VGA compatible controller"):
            pdata["Graphics"] = p[3] + " " + p[5]
    f.close()
    return pdata

def serial_number():
    """Get the serial number. Requires root access"""
    sdata = {}
    if os.getuid() == 0:
        try:
            sdata['Serial'] = open('/sys/class/dmi/id/product_serial') \
                .read().strip()
        except:
            for line in os.popen('/usr/sbin/dmidecode -s system-serial-number'):
                sdata['Serial'] = line.strip()
    return sdata

def system_model():
    """Get manufacturer and model number.

    On older Linux kernel versions without /sys/class/dmi/id this
    requires root access.
    """
    mdata = {}
    man = None
    pn = None
    try:
        # This might be
        # sys_vendor, bios_vendor, board_vendor, or chassis_vendor
        man = open('/sys/class/dmi/id/sys_vendor').read().strip()
    except:
        if os.getuid() == 0:
            for line in os.popen('/usr/sbin/dmidecode -s system-manufacturer'):
                man = line.strip()
    try:
        pn = open('/sys/class/dmi/id/product_name').read().strip()
    except:
        if os.getuid() == 0:
            for line in os.popen('/usr/sbin/dmidecode -s system-product-name'):
                pn = line.strip()
    if man is not None:
        mdata['System_manufacturer'] = man
    if pn is not None:
        mdata['System_product_name'] = pn
    return mdata

def diskdata():
    """Get total disk size in GB."""
    p = os.popen("/bin/df -l -P")
    ddata = {}
    tsize = 0
    for line in p.readlines():
        d = line.split()
        if ("/dev/sd" in d[0] or "/dev/hd" in d[0] or "/dev/mapper" in d[0]):
            tsize = tsize + int(d[1])
    ddata["Disk_GB"] = int(tsize)/1000000
    p.close()
    return ddata

def distro():
    """Get the distro and version."""
    d = platform.dist()
    dv = d[0] + " " + d[1]
    return {"Distro":d[0], "DistroVersion":d[1]}

def hostname():
    """Get hostname. 

    Use the fqdn to get a consistent hostname, otherwise using
    gethostname() might or might not give a fqdn depending on the
    system configuration.
    """
    return {"Hostname":socket.getfqdn()}

def ip_address():
    """Get the IP address used for public connections."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 8.8.8.8 is the google public DNS
    s.connect(("8.8.8.8", 53))
    ip = s.getsockname()[0]
    s.close()
    return ip

def mac_address(ip):
    """Get the MAC address"""
    for line in os.popen('/sbin/ifconfig'):
        s = line.split()
        if len(s) > 3:
            if s[3] == 'HWaddr':
                mac = s[4]
            elif s[2] == ip:
                break
    return {'MAC': mac}

def getallhwinfo():
    """Get all the hw info."""
    hwinfo = meminfo()
    hwinfo.update(cpuinfo())
    hwinfo.update(uname())
    hwinfo.update(vgadata())
    hwinfo.update(distro())
    hwinfo.update(diskdata())
    hwinfo.update(hostname())
    hwinfo.update(serial_number())
    ip = ip_address()
    hwinfo.update(mac_address(ip))
    hwinfo.update({'IP': ip})
    hwinfo.update(system_model())
    return hwinfo

def header_fields(h=None):
    """The order of the fields in the header."""
    hfields = ['Hostname', 'IP', 'Distro', 'DistroVersion', 'Kernel', 'Arch', 'CPU', 'MHz', 'Mem_MiB', 'Swap_MiB', 'Disk_GB', 'Graphics', 'MAC', 'Serial', 'System_manufacturer', 'System_product_name']
    if h != None:
	if h.has_key('Date'):
	    hfields.append('Date')
    return hfields

def printheader(h=None):
    """Print the header for the CSV table."""
    writer = csv.writer(sys.stdout)
    writer.writerow(header_fields(h))

def printtable(h, header):
    """Print as a table."""
    hk = header_fields(h)
    if (header):
        printheader()
    writer = csv.DictWriter(sys.stdout, hk, extrasaction='ignore')
    writer.writerow(h)

def agent(server="http://localhost:8000"):
    """Run in agent mode.

    This gathers data, and sends it to a server given by the server argument.

    """
    import xmlrpclib
    sp = xmlrpclib.ServerProxy(server)
    hw = getallhwinfo()
    fields = header_fields()
    for f in fields:
        if not f in hw:
            hw[f] = ''
    try:
        sp.puthwinfo(xmlrpclib.dumps((hw,)))
    except xmlrpclib.Error, v:
        print "ERROR occured: ", v

if __name__=="__main__":
    import pprint
    from optparse import OptionParser
    parser = OptionParser(version=version)
    parser.add_option("-t", "--table", dest="table",
                      action="store_true",
                      help="Write output as a CSV table")
    parser.add_option("-c", "--ctitles", dest="header",
                      action="store_true",
                      help="Write table column titles. Can be used in conjunction \
with the --table option")
    parser.add_option("-a", "--agent", dest="agent", action="store_true",
            help="Run in agent mode, send data to server.")
    parser.add_option("-s", "--server", dest="server", 
            help="Server to send results to when running in agent mode.")
    (options, args) = parser.parse_args()
    if (options.table):
        printtable(getallhwinfo(), options.header)
    elif (options.header):
        printheader()
    elif (options.agent):
        if (options.server):
            agent(options.server)
        else:
            agent()
    else:
        pp = pprint.PrettyPrinter()
        pp.pprint(getallhwinfo())
