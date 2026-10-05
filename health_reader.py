"""Conservative RGB health-bar estimate. Unknown readings return None."""
import cv2
import numpy as np


def estimate_player_health(frame, player_box, tile_size):
    if frame is None or tile_size <= 0:
        return None
    cx = (player_box[0] + player_box[2]) / 2
    top = player_box[1]
    h, w = frame.shape[:2]
    x0, x1 = max(0, int(cx - tile_size * 1.5)), min(w, int(cx + tile_size * 1.5))
    y0, y1 = max(0, int(top - tile_size * 2)), min(h, int(top + tile_size * .25))
    crop = frame[y0:y1, x0:x1, :3]
    if crop.size == 0:
        return None
    # Require a long dark outline enclosing a green fill, not green scenery.
    dark = (np.max(crop, axis=2) < 150).astype(np.uint8) * 255
    contours, _ = cv2.findContours(dark, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        x, y, bw, bh = cv2.boundingRect(contour)
        if not (.8 * tile_size <= bw <= 2.6 * tile_size and 4 <= bh <= .55 * tile_size and bw / bh >= 4):
            continue
        if abs(x0 + x + bw / 2 - cx) > tile_size * .4:
            continue
        region = crop[y:y + bh, x:x + bw]
        rgb = region.astype(np.int16)
        green = (rgb[:, :, 1] > 115) & (rgb[:, :, 1] > rgb[:, :, 0] * 1.25) & (rgb[:, :, 1] > rgb[:, :, 2] * 1.15)
        occupied = np.flatnonzero(np.sum(green, axis=0) >= max(2, bh * .25))
        if len(occupied) < 2 or occupied[0] > max(4, bw * .1):
            continue
        if len(occupied) / (occupied[-1] - occupied[0] + 1) < .9:
            continue
        # The unfilled portion must also be dark; reject mottled map objects.
        empty = region[1:-1, occupied[-1] + 2:-1]
        if empty.size and np.mean(np.max(empty, axis=2) < 150) < .85:
            continue
        ratio = min(1., (occupied[-1] - occupied[0] + 1) / max(1, bw - 4))
        candidates.append(ratio)
    return min(candidates) if candidates else None
