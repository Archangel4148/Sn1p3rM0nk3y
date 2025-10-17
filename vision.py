from data.enums import BloonsScreen, PAGE_IDENTIFIER_POINTS, MAP_SELECT_PAGE_POINTS, SELECTED_MAP_SELECT_TAB_COLOR
from system_flags import vprint


def color_close(a, b, tol=5):
    return all(abs(a[i] - b[i]) <= tol for i in range(3))


def identify_screen(capture) -> tuple[BloonsScreen | None, int | None]:
    """Identify the screen using constant identifier points"""
    # Find the first page where all points match
    for page_name, points in PAGE_IDENTIFIER_POINTS.items():
        found_page = True
        vprint(page_name.value)
        # Check each identifier point
        for (w_fraction, h_fraction), color in points:
            point_color = capture.getpixel((int(capture.width * w_fraction), int(capture.height * h_fraction)))
            vprint(point_color, color)
            # If any point fails, the screen is not a match
            if not color_close(point_color, color):
                found_page = False
                break
        if found_page:
            # For the map select page, also try to identify the tab
            if page_name == BloonsScreen.MAP_SELECT:
                # Check each tab dot
                for i, (w_fraction, h_fraction) in enumerate(MAP_SELECT_PAGE_POINTS):
                    point_color = capture.getpixel(
                        (int(capture.width * w_fraction), int(capture.height * h_fraction)))
                    # Find the selected map select tab
                    if color_close(point_color, SELECTED_MAP_SELECT_TAB_COLOR):
                        vprint(f"Found page: {page_name} (Tab {i + 1})")
                        return page_name, i + 1
                vprint("Could not identify selected map tab.")
                return page_name, None
            else:
                vprint(f"Found page: {page_name}")
                return page_name, None
    vprint("Could not identify current screen.")
    return None, None
