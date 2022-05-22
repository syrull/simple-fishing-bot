import pyautogui
import time
import random
import win32gui

BAIT_IMAGE = "./bait.png"
FISHING_BUTTON = "b"
TUNE_BAIT_MOUSE_UNDER_PX = 35
EDGE_RESET = 10, 10
ACTIVE_AFTER = 2
CONFIDENCE = 0.7


def find_on_screen(image):
    while True:
        try:
            loc = pyautogui.locateOnScreen(image, confidence=CONFIDENCE)
            cp_loc = pyautogui.center(loc)
            return cp_loc
        except Exception:
            pass


time.sleep(ACTIVE_AFTER)

while True:
    time.sleep(0.25 + random.uniform(0, 1.5))

    # 20% Chance to press "space"
    chance = random.randint(0, 100)
    if chance <= 20:
        pyautogui.press("space")
        time.sleep(2)

    pyautogui.write(FISHING_BUTTON)
    fishing = True

    # Resetting the mouse's pos
    pyautogui.moveTo(*EDGE_RESET)
    while fishing:
        bait = find_on_screen(BAIT_IMAGE)
        pyautogui.moveTo(
            bait.x, bait.y + TUNE_BAIT_MOUSE_UNDER_PX + random.randint(1, 4)
        )
        catching = True
        cursor_info = win32gui.GetCursorInfo()
        while catching:
            start_catching_time = time.time()
            curr_cursor_info = win32gui.GetCursorInfo()
            if curr_cursor_info != cursor_info:
                time.sleep(0.25 + random.uniform(0, 0.15))
                pyautogui.click(bait.x, bait.y)
                catching = False
                fishing = False

            # If it didn't catch a fish
            if time.time() - start_catching_time > 22:
                catching = False
                fishing = False
