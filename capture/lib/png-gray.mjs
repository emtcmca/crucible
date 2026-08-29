// lib/png-gray.mjs — read an 8-bit greyscale PNG into a Uint8Array of pixels.
//
// WHY THIS IS HAND-ROLLED
// The ffmpeg binary Playwright ships is a deliberately stripped build. It has
// exactly two muxers (image2, webm) and two encoders (png, libvpx), and its
// filter list is crop/format/hflip/null/pad/scale/transpose/trim/vflip. There
// is no rawvideo muxer and no fps filter, so the usual "pipe raw RGB out of
// ffmpeg" trick cannot work here. PNG is the only image format this build can
// write, so the verifier has to be able to read one.
//
// Bringing in an image library instead would mean the capture harness depends
// on something the recorder does not. Fifty lines of zlib and unfiltering keeps
// the dependency list at exactly one package.
//
// Scope is deliberately narrow: 8-bit, colour type 0 (greyscale), no interlace.
// That is what `ffmpeg -pix_fmt gray -f image2` writes. Anything else throws
// rather than guessing, because a silently wrong pixel read is worse than no
// pixel read.

import zlib from 'node:zlib';

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

/**
 * @param {Buffer} buf contents of a .png file
 * @returns {{width:number, height:number, pixels:Uint8Array}} one byte per pixel, row-major
 */
export function readGrayPng(buf) {
  if (!buf.subarray(0, 8).equals(PNG_SIGNATURE)) {
    throw new Error('not a PNG: signature mismatch');
  }

  let offset = 8;
  let ihdr = null;
  const idat = [];

  while (offset + 8 <= buf.length) {
    const length = buf.readUInt32BE(offset);
    const type = buf.toString('ascii', offset + 4, offset + 8);
    const dataStart = offset + 8;
    const data = buf.subarray(dataStart, dataStart + length);

    if (type === 'IHDR') {
      ihdr = {
        width: data.readUInt32BE(0),
        height: data.readUInt32BE(4),
        bitDepth: data[8],
        colorType: data[9],
        compression: data[10],
        filter: data[11],
        interlace: data[12],
      };
    } else if (type === 'IDAT') {
      idat.push(Buffer.from(data));
    } else if (type === 'IEND') {
      break;
    }
    offset = dataStart + length + 4; // + CRC
  }

  if (!ihdr) throw new Error('PNG has no IHDR chunk');
  if (ihdr.bitDepth !== 8 || ihdr.colorType !== 0) {
    throw new Error(
      `unsupported PNG: bitDepth ${ihdr.bitDepth}, colorType ${ihdr.colorType}; expected 8 and 0 (greyscale)`,
    );
  }
  if (ihdr.interlace !== 0) throw new Error('unsupported PNG: interlaced');
  if (!idat.length) throw new Error('PNG has no IDAT data');

  const raw = zlib.inflateSync(Buffer.concat(idat));
  const { width, height } = ihdr;
  const stride = width; // one byte per pixel at 8-bit greyscale
  const expected = height * (stride + 1); // each row carries a leading filter byte
  if (raw.length < expected) {
    throw new Error(`PNG data truncated: ${raw.length} bytes, expected ${expected}`);
  }

  const pixels = new Uint8Array(width * height);

  // Undo the per-scanline filter. bpp is 1, so "the byte to the left" is x-1
  // and "the byte above" is the same x on the previous, already-reconstructed row.
  for (let y = 0; y < height; y += 1) {
    const filterType = raw[y * (stride + 1)];
    const rowIn = y * (stride + 1) + 1;
    const rowOut = y * stride;
    for (let x = 0; x < stride; x += 1) {
      const value = raw[rowIn + x];
      const left = x > 0 ? pixels[rowOut + x - 1] : 0;
      const up = y > 0 ? pixels[rowOut - stride + x] : 0;
      const upLeft = x > 0 && y > 0 ? pixels[rowOut - stride + x - 1] : 0;
      let out;
      switch (filterType) {
        case 0: out = value; break;                       // None
        case 1: out = value + left; break;                // Sub
        case 2: out = value + up; break;                  // Up
        case 3: out = value + ((left + up) >> 1); break;  // Average
        case 4: {                                          // Paeth
          const p = left + up - upLeft;
          const pa = Math.abs(p - left);
          const pb = Math.abs(p - up);
          const pc = Math.abs(p - upLeft);
          const pred = pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft;
          out = value + pred;
          break;
        }
        default:
          throw new Error(`unknown PNG filter type ${filterType} on row ${y}`);
      }
      pixels[rowOut + x] = out & 0xff;
    }
  }

  return { width, height, pixels };
}
