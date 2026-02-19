from PIL import Image, ImageChops


def autocrop_bait(path, padding=2):
    """Crop a bait image to its non-background content.

    For RGBA images, crops to non-transparent pixels.
    For RGB images, detects background from the corner pixel and removes it.
    Adds padding back for template matching accuracy.
    """
    img = Image.open(path)

    if img.mode == "RGBA":
        # Use alpha channel — getbbox finds the bounding box of non-zero pixels
        bbox = img.getbbox()
    else:
        img = img.convert("RGB")
        # Detect background color from top-left corner
        bg = Image.new("RGB", img.size, img.getpixel((0, 0)))
        diff = ImageChops.difference(img, bg)
        # Convert to grayscale and threshold to handle near-matches
        diff = diff.convert("L")
        diff = diff.point(lambda x: 255 if x > 10 else 0)
        bbox = diff.getbbox()

    if bbox is None:
        return img

    # Add padding back (clamped to image bounds)
    left = max(0, bbox[0] - padding)
    upper = max(0, bbox[1] - padding)
    right = min(img.width, bbox[2] + padding)
    lower = min(img.height, bbox[3] + padding)

    return img.crop((left, upper, right, lower))
