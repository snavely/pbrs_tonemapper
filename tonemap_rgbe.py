import re
import math
import struct
import numpy as np
import scipy.misc
import png
import sys

from itertools import product
from absl import flags

FLAGS = flags.FLAGS

flags.DEFINE_string('input_image', None, 'Input rgbe image.')
flags.DEFINE_string('output_image', None, 'Output 16-bit tonemapped png image.')
flags.DEFINE_float('percentile', 50, 'Value between 0-100 representing the percentile to which to map to percentile_point.')
flags.DEFINE_float('percentile_point', 0.5, 'Value between 0-1 to map percentile value (across all three RGB channels to.')

HDR_NONE = 0x00
HDR_RLE_RGBE_32 = 0x01

def load(filename):
        """
        Load .hdr format
        """
        img = None
        with open(filename, 'rb') as f:
                bufsize = 4096
                filetype = HDR_NONE
                valid = False
                exposure = 1.0

                # Read header section
                while True:
                        buf = f.readline(bufsize).decode('ascii')
                        if buf[0] == '#' and (buf == '#?RADIANCE\n' or buf == '#?RGBE\n'):
                                valid = True
                        else:
                                p = re.compile('FORMAT=(.*)')
                                m = p.match(buf)
                                if m is not None and m.group(1) == '32-bit_rle_rgbe':
                                        filetype = HDR_RLE_RGBE_32
                                        continue

                                p = re.compile('EXPOSURE=(.*)')
                                m = p.match(buf)
                                if m is not None:
                                        exposure = float(m.group(1))
                                        continue

                        if buf[0] == '\n':
                                # Header section ends
                                break

                if not valid:
                        raise Exception('HDR header is invalid!!')

                # Read body section
                width = 0
                height = 0
                buf = f.readline(bufsize).decode()
                p = re.compile('([\-\+]Y) ([0-9]+) ([\-\+]X) ([0-9]+)')
                m = p.match(buf)
                if m is not None and m.group(1) == '-Y' and m.group(3) == '+X':
                        width = int(m.group(4))
                        height = int(m.group(2))
                else:
                        raise Exception('HDR image size is invalid!!')

                # Check byte array is truly RLE or not
                byte_start = f.tell()
                now = ord(f.read(1))
                now2 = ord(f.read(1))
                if now != 0x02 or now2 != 0x02:
                        filetype = HDR_NONE
                f.seek(byte_start)

                if filetype == HDR_RLE_RGBE_32:
                        # Run length encoded HDR
                        tmpdata = np.zeros((width * height * 4), dtype=np.uint8)
                        nowy = 0
                        while True:
                                now = -1
                                now2 = -1
                                try:
                                        now = ord(f.read(1))
                                        now2 = ord(f.read(1))
                                except:
                                        break

                                if now != 0x02 or now2 != 0x02:
                                        break

                                A = ord(f.read(1))
                                B = ord(f.read(1))
                                width = (A << 8) | B

                                nowx = 0
                                nowv = 0
                                while True:
                                        if nowx >= width:
                                                nowv += 1
                                                nowx = 0
                                                if nowv == 4:
                                                        break

                                        info = ord(f.read(1))
                                        #print info
                                        if info <= 128:
                                                data = f.read(info)
                                                #print len(data)
                                                
                                                for i in range(info):
                                                        #print (nowy * width + nowx) * 4 + nowv
                                                        tmpdata[(nowy * width + nowx) * 4 + nowv] = ord(data[i])#int(data[i].encode('hex'), 16)
                                                        nowx += 1
                                        else:
                                                num = info - 128
                                                data = ord(f.read(1))
                                                for i in range(num):
                                                        tmpdata[(nowy * width + nowx) * 4 + nowv] = data
                                                        nowx += 1

                                nowy += 1
                                

                        tmpdata = tmpdata.reshape((height, width, 4))
                else:
                        # Non-encoded HDR format
                        totsize = width * height * 4
                        tmpdata = struct.unpack('B' * totsize, f.read(totsize))
                        tmpdata = np.asarray(tmpdata, np.uint8).reshape((height, width, 4))
                #print tmpdata[:,:,3]
                return tmpdata
                
def hdr2img(tmpdata):
        expo = np.power(2.0, tmpdata[:,:,3] - 128.0) / 256.0
        img = np.multiply(tmpdata[:,:,0:3], expo[:,:,np.newaxis])

        if img is None:
                raise Exception('Failed to load file "{0}"'.format(filename))

        return img

if __name__ == '__main__':
        FLAGS(sys.argv)
        if FLAGS.input_image == None:
                print 'Error: --input_image must be specified.'
                sys.exit(1)
        if FLAGS.output_image == None:
                print 'Error: --output_image must be specified.'
                sys.exit(1)

        rgbe = load(FLAGS.input_image)
        img = hdr2img(rgbe)

        # Set the median pixel to the median point (default 0.5),
        # (after 2.2).
        # Ideas: Try mapping 90 %-tile to 0.9?
        # Detect overexposure and only underexpose in that case?
        brightness = 0.3 * img[:,:,0] + 0.59 * img[:,:,1] + 0.11 * img[:,:,2]
        median = np.median(brightness)
        percentile = np.percentile(brightness, FLAGS.percentile)
        if median < 1.0e-4:
                scale = 0.0
        else:
                scale = math.exp(math.log(FLAGS.percentile_point) * 2.2 - math.log(percentile))

        z = np.clip((65535 * np.power(scale * img, 1/2.2)), 0, 65535).astype(np.uint16)

        # Use pypng to write z as a color PNG.
        with open(FLAGS.output_image, 'wb') as f:
                writer = png.Writer(width=z.shape[1], height=z.shape[0],
                                    bitdepth=16)
                # Convert z to the Python list of lists expected by
                # the png writer.
                z2list = z.reshape(-1,
                                   z.shape[1]*z.shape[2]).tolist()
                writer.write(f, z2list)
