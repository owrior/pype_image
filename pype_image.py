import subprocess
import os
import sys
import warnings
import json

indicator = b"{ready}"
block_size = 4096


class PypeImage:
    def __init__(self, executable="exiftool", meta_loc="iptc"):
        """meta_loc: iptc or xmp,
           executable: location of exiftool.exe (if in path exiftool fine)"""
        self.executable = executable
        self.running = False
        if meta_loc is "iptc":
            self.meta_loc = "-iptc:Keywords"
            self.getter_loc = "IPTC:Keywords"
        elif meta_loc is "xmp":
            self.meta_loc = "-xmp:Subject"
            self.getter_loc = "XMP:Subject"
        else:
            self.meta_loc = "-iptc:Keywords"
            self.getter_loc = "IPTC:Keywords"

    def start(self):
        if self.running:
            warnings.warn("Pypline already running.")
        with open(os.devnull, 'w') as devnull:
            self._process = subprocess.Popen([self.executable, '-stay_open', 'True',
                                              '-@', '-', '-common_args', '-G', '-n'],
                                             stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE,
                                             stderr=devnull)
        self.running = True

    def terminate(self):
        if not self.running:
            return

        self._process.stdin.write(b"-stay_open\nFalse\n")
        self._process.stdin.flush()
        self._process.communicate()
        del self._process
        self.running = False

    def execute(self, args):
        if not self.running:
            raise ValueError("No pypline running.")
        self._process.stdin.write(b"\n".join(args + [b'-execute\n'])) # Changed so could cause error
        self._process.stdin.flush()
        output = b""
        fd = self._process.stdout.fileno()
        while not output[-32:].strip().endswith(indicator):
            output += os.read(fd, block_size)
        return output.strip()[:-len(indicator)]

    def addKeywords(self, metadata, fpath):
        kws = [bytes("{0}+={1}".format(self.meta_loc, kw.replace(" ", r" ")), 'utf8') for kw in metadata]
        cmd = [b'-overwrite_original_in_place'] + kws + [fpath]
        self.execute(cmd)

    def clearKeywords(self, fpath):
        cmd = [b'-overwrite_original_in_place', bytes('{0}='''.format(self.meta_loc), 'utf8'), fpath]
        self.execute(cmd)

    def getKeywords(self, fpath):
        cmd = [b'-j', bytes('{0}'.format(self.meta_loc), 'utf8'), fpath]
        out = self.execute(cmd)
        info = json.loads(out)[0]
        try:
            return info[self.getter_loc]
        except KeyError:
            print(fpath, ' contains no ' + self.getter_loc + ' metadata.')
            return ""

