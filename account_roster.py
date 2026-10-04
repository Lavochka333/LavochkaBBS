"""Account-specific inventory obtained from the game's unlocked cards."""
import json
import re
import threading
import time

import numpy as np
import cv2
import pytesseract

import device_profiles
import trophy_reader  # Configure the bundled OCR executable before using it.
from utils import load_brawlers_info

_jobs = {}
_lock = threading.Lock()


def load(key):
    path = device_profiles.profile_dir(key) / 'active_account.json'
    try:
        tag = json.loads(path.read_text(encoding='utf-8'))['tag']
        return json.loads((path.parent / 'accounts' / tag / 'roster.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError):
        return {'brawlers': [], 'complete': False}


def status(key):
    with _lock:
        return {**load(key), **_jobs.get(key, {})}


def _ocr(frame, region, config='--psm 7'):
    h, w = frame.shape[:2]
    x, y, rw, rh = region
    crop = frame[int(y*h):int((y+rh)*h), int(x*w):int((x+rw)*w)]
    return pytesseract.image_to_string(cv2.resize(cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY), None, fx=3, fy=3), config=config).strip()


def profile_details(frame):
    count = re.search(r'(\d+)\s*/\s*(\d+)', _ocr(frame, (.79, .385, .17, .045)))
    if not count:
        return None
    text = _ocr(frame, (.005, .30, .12, .043), '--psm 7 -c tessedit_char_whitelist=#0289PYLQGRJCUV')
    match = re.fullmatch(r'#([0289PYLQGRJCUV]{5,14})', text.replace(' ', ''))
    if not match:
        raise ValueError('Не удалось прочитать тег аккаунта. Попробуй обновить снова.')
    return match[1], int(count[1])


def identify(wc):
    from state_finder import is_in_lobby
    initial = np.asarray(wc.device.screenshot())
    already_profile = profile_details(initial)
    if not already_profile and not is_in_lobby(initial):
        raise ValueError('Открой главный экран игры перед обновлением бойцов.')
    if not already_profile:
        wc.click(120, 65, already_include_ratio=False)
        time.sleep(.8)
    try:
        frames = [np.asarray(wc.device.screenshot())]
        time.sleep(.25)
        frames.append(np.asarray(wc.device.screenshot()))
        tags = []
        counts = []
        for frame in frames:
            details = profile_details(frame)
            if not details:
                raise ValueError('Не удалось открыть профиль аккаунта.')
            tags.append(details[0])
            counts.append(details[1])
        if tags[0] != tags[1] or counts[0] != counts[1] or counts[0] is None:
            raise ValueError('Не удалось подтвердить аккаунт и количество бойцов.')
        return tags[0], counts[0]
    finally:
        wc.click(84, 45, already_include_ratio=False)
        time.sleep(.7)


def scan(key):
    from window_controller import WindowController
    from lobby_automation import LobbyAutomation
    from brawler_cards import card_boxes, read_card
    wc = None
    try:
        with device_profiles.use_profile(key):
            wc = WindowController(15, serial=key)
            wc.screenshot()  # Initialize the stream dimensions used by clicks.
            tag, expected = identify(wc)
            base = device_profiles.profile_dir(key)
            base.mkdir(parents=True, exist_ok=True)
            (base / 'active_account.json').write_text(json.dumps({'tag': tag}), encoding='utf-8')
            known = load_brawlers_info()
            selector = LobbyAutomation(wc)
            if not selector._open_roster():
                raise ValueError('Не удалось открыть список бойцов.')
            # Clear any previous in-game search before walking the roster.
            wc.press('brawler_search')
            wc.clear_text()
            wc.device.shell(['input', 'keyevent', '111'])
            time.sleep(.6)
            for _ in range(12):
                wc.device.swipe(300, 450, 1450, 450, .25)
                time.sleep(.3)
            found = {}
            unchanged = 0
            for page in range(45):
                time.sleep(.35)
                frame = np.asarray(wc.device.screenshot())
                time.sleep(.15)
                second = np.asarray(wc.device.screenshot())
                before = len(found)
                for i, box in enumerate(card_boxes(frame)):
                    x, y, w, h = box
                    strip = frame[y+int(h*.2):y+int(h*.7), x+int(w*.85):x+int(w*.96)]
                    # Owned cards have the green upgrade strip; locked cards do not.
                    green = (strip[:,:,1] > strip[:,:,0]*1.2) & (strip[:,:,1] > strip[:,:,2]*1.2) & (strip[:,:,1] > 110)
                    if green.mean() < .2:
                        continue
                    card = read_card(frame, i, known, discover=True)
                    check = read_card(second, i, known, discover=True)
                    name = card.get('brawler')
                    if name and name == check.get('brawler'):
                        value = card['trophies'] if card['trophies'] == check['trophies'] else None
                        found[name] = {'name': name, 'trophies': value}
                with _lock:
                    _jobs[key] = {'scanning': True, 'message': f'Найдено {len(found)} из {expected} бойцов'}
                unchanged = unchanged + 1 if len(found) == before else 0
                if len(found) >= expected or unchanged >= 6:
                    break
                wc.device.swipe(1250, 450, 1010, 450, .6)
            result = {'tag': tag, 'expected': expected, 'brawlers': sorted(found.values(), key=lambda b: b['name']),
                      'complete': len(found) == expected, 'updated_at': time.time()}
            path = base / 'accounts' / tag / 'roster.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            # Keep previous confirmed cards if this scan was incomplete.
            if not result['complete'] and path.exists():
                previous = json.loads(path.read_text(encoding='utf-8'))
                for b in previous.get('brawlers', []):
                    found.setdefault(b['name'], b)
                result['brawlers'] = sorted(found.values(), key=lambda b: b['name'])
                result['complete'] = len(found) == expected
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            with _lock:
                _jobs[key] = {'scanning': False, 'message': f'Открытых бойцов: {len(found)} из {expected}.'}
            wc.click(84, 45, already_include_ratio=False)
    except Exception as error:
        with _lock:
            _jobs[key] = {'scanning': False, 'message': str(error)}
    finally:
        if wc:
            wc.close()


def start_scan(key):
    key = device_profiles.sanitize_key(key)
    with _lock:
        if _jobs.get(key, {}).get('scanning'):
            return False
        _jobs[key] = {'scanning': True, 'message': 'Читаю аккаунт и открытых бойцов…'}
    threading.Thread(target=scan, args=(key,), daemon=True).start()
    return True
