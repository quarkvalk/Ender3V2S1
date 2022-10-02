#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# Prusa / Super Slicer post-processor script for the Professional Firmware
# URL: https://github.com/mriscoc/Ender3V2S1
# Miguel A. Risco-Castillo
# version: 1.5
# date: 2022/05/29
#
# Contains code from the jpg re-encoder thumbnail post processor script:
# github.com/alexqzd/Marlin/blob/Gcode-preview/Display%20firmware/gcode_thumb_to_jpg.py
# ------------------------------------------------------------------------------

import sys
import re
import os
import base64 
import io
import subprocess

try:
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip3", "install", "Pillow"])
    from PIL import Image
    
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip3", "install", package])

# Get the g-code source file name
sourceFile = sys.argv[1]

# Read the ENTIRE g-code file into memory
with open(sourceFile, "r") as f:
    lines = f.read()

thumb_expresion = '; thumbnail begin.*?\n((.|\n)*?); thumbnail end'
size_expresion = '; thumbnail begin [0-9]+x[0-9]+ [0-9]+'
size_expresion_group = '; thumbnail begin [0-9]+x[0-9]+ ([0-9]+)'

thumb_matches = re.findall(thumb_expresion, lines)
size_matches = re.findall(size_expresion, lines)

def encodedStringToGcodeComment(encodedString):
    n = 78
    return '; ' + '\n; '.join(encodedString[i:i+n] for i in range(0, len(encodedString), n)) + '\n'


for idx, match in enumerate(thumb_matches):
    original = match[0]
    encoded = original.replace("; ", "")
    encoded = encoded.replace("\n", "")
    encoded = encoded.replace("\r", "")
    decoded = base64.b64decode(encoded)
    img_png = Image.open(io.BytesIO(decoded))
    img_png_rgb = img_png.convert('RGB')
    img_byte_arr = io.BytesIO()
    img_png_rgb.save(img_byte_arr, format='jpeg')
    img_byte_arr = img_byte_arr.getvalue()
    encodedjpg = base64.b64encode(img_byte_arr).decode("utf-8")
    encodedjpg_gcode = encodedStringToGcodeComment(encodedjpg)
    lines = lines.replace(original, encodedjpg_gcode)

    size_match = size_matches[idx]
    size = re.findall(size_expresion_group, size_match)
    new_size = size_match.replace(size[0], str(len(encodedjpg)))
    lines = lines.replace(size_match, new_size)

#Prepare header values
ph = re.search('; generated by (.*)\n', lines)
if ph is not None : lines = lines.replace(ph[0], "")

time = 0
match = re.search('; estimated printing time \(normal mode\) = (.*)\n', lines)
if match is not None :
  h = re.search('(\d+)h',match[1])
  h = int(h[1]) if h is not None else 0
  m = re.search('(\d+)m',match[1])
  m = int(m[1]) if m is not None else 0
  s = re.search('(\d+)s',match[1])
  s = int(s[1]) if s is not None else 0
  time = h*3600+m*60+s

match = re.search('; filament used \[mm\] = (.*)\n', lines)
filament = float(match[1])/1000 if match is not None else 0

match = os.getenv('SLIC3R_LAYER_HEIGHT')
layer = float(match) if match is not None else 0

minx = 0
miny = 0
minz = 0
maxx = 0
maxy = 0
maxz = 0

try:
    with open(sourceFile, "w+") as of:
    # Write header values
        if ph is not None : of.write(ph[0])
        of.write(';FLAVOR:Marlin\n')
        of.write(';TIME:{:d}\n'.format(time))
        of.write(';Filament used: {:.6f}\n'.format(filament))
        of.write(';Layer height: {:.2f}\n'.format(layer))
        of.write(';MINX:{:.3f}\n'.format(minx))
        of.write(';MINY:{:.3f}\n'.format(miny))
        of.write(';MINZ:{:.3f}\n'.format(minz))
        of.write(';MAXX:{:.3f}\n'.format(maxx))
        of.write(';MAXY:{:.3f}\n'.format(maxy))
        of.write(';MAXZ:{:.3f}\n'.format(maxz))
        of.write(';POSTPROCESSED\n')
        of.write(';Header generated for The Ender3v2 Professional Firmware\n')
        of.write(';https://github.com/mriscoc/Marlin_Ender3v2\n\n')
        of.write(lines)
except:
    print('Error writing output file')
    input()
finally:
    of.close()
    f.close()
