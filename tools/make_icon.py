"""Generate app.ico: orange microphone + sound waves on a dark rounded tile."""
from PIL import Image, ImageDraw

ORANGE = (255, 107, 0, 255)
BG = (17, 17, 17, 255)
SS = 4          # supersampling factor
N = 256 * SS    # working size


def draw_icon():
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # dark rounded tile background
    d.rounded_rectangle([0, 0, N - 1, N - 1], radius=56 * SS, fill=BG)

    # microphone capsule (rounded pill)
    cap = [106 * SS, 44 * SS, 150 * SS, 128 * SS]
    d.rounded_rectangle(cap, radius=cap[2] - cap[0] if False else 22 * SS, fill=ORANGE)

    # stand stem
    stem_w = 9 * SS
    sx = 128 * SS
    d.rounded_rectangle([sx - stem_w // 2, 122 * SS, sx + stem_w // 2, 182 * SS],
                        radius=stem_w // 2, fill=ORANGE)

    # base bar
    d.rounded_rectangle([96 * SS, 186 * SS, 160 * SS, 200 * SS],
                        radius=7 * SS, fill=ORANGE)

    # sound waves (two arcs per side)
    for r, w in ((66, 9), (90, 9)):
        cx = 128 * SS
        cy = 86 * SS
        R = r * SS
        bbox = [cx - R, cy - R, cx + R, cy + R]
        d.arc(bbox, start=305, end=55, fill=ORANGE, width=w * SS)
        # mirror on the left: draw full arc then mask right half via re-draw
    # left side arcs
    for r, w in ((66, 9), (90, 9)):
        cx = 128 * SS
        cy = 86 * SS
        R = r * SS
        bbox = [cx - R, cy - R, cx + R, cy + R]
        d.arc(bbox, start=125, end=235, fill=ORANGE, width=w * SS)

    return img


def main():
    icon = draw_icon()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icon.save("app.ico", format="ICO", sizes=[(s, s) for s in sizes])
    # also a 256 preview for reference (not shipped)
    icon.resize((256, 256), Image.LANCZOS).save("app_preview.png")
    print("wrote app.ico with sizes:", sizes)


if __name__ == "__main__":
    main()
