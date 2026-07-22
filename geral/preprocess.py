import os
import sys
import argparse
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

try:
    import cv2
    import numpy as np
    _has_cv2 = True
except Exception:
    _has_cv2 = False


# Pasta padrão para execução rápida (comportamento: `python preprocess.py -d data -o data`)
if sys.platform == "win32":
    PASTA_IMAGENS = r"C:\Users\brunoquaiatti\Documents\GitHub\gazofilacio-scripts\geral"
else:
    PASTA_IMAGENS = "/home/node/data/"


def pil_unsharp(img, radius=2, percent=150, threshold=3):
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def pil_binarize(img, threshold=128):
    if img.mode != 'L':
        img = img.convert('L')
    return img.point(lambda p: 255 if p > threshold else 0)


def cv2_binarize(img_path, out_path, block_size=15, c=8):
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError(f"cv2 couldn't open {img_path}")
    # Adaptive thresholding
    th = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, block_size | 1, c)
    cv2.imwrite(out_path, th)


def enhance_image(in_path, out_path, scale=2, sharpness=1.5, contrast=1.3, binarize=False):
    img = Image.open(in_path)
    # Convert to RGB
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    # Upscale if small
    w, h = img.size
    target_w = int(w * scale)
    target_h = int(h * scale)
    img = img.resize((target_w, target_h), Image.BICUBIC)

    # Slight sharpening via unsharp mask
    img = pil_unsharp(img, radius=1.5, percent=int(100 * sharpness), threshold=2)

    # Improve contrast
    img = ImageEnhance.Contrast(img).enhance(contrast)

    # Autocontrast and remove color roughness
    img = ImageOps.autocontrast(img)

    if binarize:
        if _has_cv2:
            # Save temporary and run cv2 adaptive threshold for better OCR results
            tmp = out_path + ".tmp.png"
            img.convert('L').save(tmp)
            try:
                cv2_binarize(tmp, out_path)
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        else:
            # PIL fallback: Otsu-like simple threshold
            gray = img.convert('L')
            # compute median as adaptive threshold
            hist = gray.histogram()
            pixels = sum(hist)
            csum = 0
            median = 0
            for i, hval in enumerate(hist):
                csum += hval
                if csum >= pixels // 2:
                    median = i
                    break
            bw = pil_binarize(gray, threshold=median)
            bw.save(out_path)
        return

    # Otherwise save enhanced image (PNG to avoid compression artifacts)
    img.save(out_path, format='PNG')


def process_dir(input_dir, output_dir, scale=2, sharpness=1.5, contrast=1.3, binarize=False, overwrite=False, remove_originals=False):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    exts = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
    for fname in os.listdir(input_dir):
        if not fname.lower().endswith(exts):
            continue
        in_path = os.path.join(input_dir, fname)
        out_name = os.path.splitext(fname)[0] + ('.png' if not binarize else '.png')
        out_path = os.path.join(output_dir, out_name)
        if os.path.exists(out_path) and not overwrite:
            print(f"Skipping existing: {out_path}")
            continue
        try:
            print(f"Processing {in_path} -> {out_path}")
            enhance_image(in_path, out_path, scale=scale, sharpness=sharpness, contrast=contrast, binarize=binarize)
            # Se solicitado, remova o arquivo original JPG/JPEG após criação do PNG
            if remove_originals:
                try:
                    ext = os.path.splitext(in_path)[1].lower()
                    if ext in ('.jpg', '.jpeg') and os.path.exists(out_path):
                        os.remove(in_path)
                        print(f"Removed original: {in_path}")
                except Exception as e:
                    print(f"Warning: couldn't remove original {in_path}: {e}")
        except Exception as e:
            print(f"Error processing {in_path}: {e}")


def cli():
    p = argparse.ArgumentParser(description='Preprocess images for OCR: upscale, sharpen, contrast, optional binarize')
    p.add_argument('-d', '--dir', dest='input_dir', default=PASTA_IMAGENS, help='Input directory with images (default: data/)')
    p.add_argument('-o', '--out', dest='output_dir', default=PASTA_IMAGENS, help='Output directory (default: same as input, acts like "-o data" when omitted)')
    p.add_argument('--scale', type=float, default=2.0, help='Upscale factor (default 2.0)')
    p.add_argument('--sharpness', type=float, default=1.5, help='Sharpness multiplier for unsharp mask')
    p.add_argument('--contrast', type=float, default=1.3, help='Contrast multiplier')
    p.add_argument('--binarize', action='store_true', help='Apply adaptive binarization (better for high-contrast OCR)')
    p.add_argument('--overwrite', action='store_true', help='Overwrite existing outputs')
    p.add_argument('--replace', action='store_true', help='Replace originals: delete input JPG/JPEG files after creating PNGs (or use when out==in)')
    args = p.parse_args()

    # decide whether to remove originals: true if --replace set or output_dir equals input_dir
    remove_originals = bool(args.replace) or os.path.abspath(args.input_dir) == os.path.abspath(args.output_dir)

    process_dir(args.input_dir, args.output_dir, scale=args.scale, sharpness=args.sharpness, contrast=args.contrast, binarize=args.binarize, overwrite=args.overwrite, remove_originals=remove_originals)


if __name__ == '__main__':
    cli()
