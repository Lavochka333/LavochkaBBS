"""Find selectable roster cards from their borders, including Russian names."""
import re

import cv2
import pytesseract

# Canonical IDs used by the playstyles and queue.
RUSSIAN_NAMES = {
    'шелли': 'shelly', 'кольт': 'colt', 'булл': 'bull', 'брок': 'brock',
    'барли': 'barley', 'нита': 'nita', 'джесси': 'jessie', 'динам айк': 'dynamike',
    'динамaйк': 'dynamike', 'динамайк': 'dynamike', 'эльпримо': 'elprimo', 'поко': 'poco',
    'роза': 'rosa', 'рико': 'rico', 'дэррил': 'darryl', 'пенни': 'penny',
    'карл': 'carl', 'джэки': 'jacky', 'гас': 'gus',
    'бо': 'bo', 'эмз': 'emz', 'гейл': 'gale',
    'грифф': 'griff', 'колетт': 'colette', 'биби': 'bibi', 'бэа': 'bea',
    'эдгар': 'edgar', 'пэм': 'pam', 'пайпер': 'piper', 'фрэнк': 'frank',
    'мэйси': 'maisie', 'белль': 'belle', 'бонни': 'bonnie', 'мэнди': 'mandy',
    'эш': 'ash', 'гром': 'grom', 'хенк': 'hank', 'перл': 'pearl',
    'анджело': 'angelo', 'берри': 'berry', 'шэйд': 'shade', 'сту': 'stu',
    'мортис': 'mortis', 'тара': 'tara', 'джин': 'gene', 'макс': 'max',
    'мистерпи': 'mrp', 'спраут': 'sprout', 'байрон': 'byron', 'скуик': 'squeak',
    'раффс': 'ruffs', 'лу': 'lou', 'базз': 'buzz', 'фэнг': 'fang',
    'эвa': 'eve', 'ева': 'eve', 'джанет': 'janet', 'отис': 'otis',
    'бастер': 'buster', 'грэй': 'gray', 'р-т': 'rt', 'виллоу': 'willow',
    'даг': 'doug', 'чак': 'chuck', 'чарли': 'charlie', 'мико': 'mico',
    'мелоди': 'melodie', 'лили': 'lily', 'кленси': 'clancy', 'мо': 'moe',
    'джуджу': 'juju', 'олли': 'ollie', 'лола': 'lola', '8бит': '8bit',
    'спайк': 'spike', 'ворон': 'crow', 'леон': 'leon', 'сэнди': 'sandy',
    'амбер': 'amber', 'мэг': 'meg', 'вольт': 'surge', 'честер': 'chester',
    'корделиус': 'cordelius', 'кит': 'kit', 'драко': 'draco', 'кенджи': 'kenji',
}


def letters(text):
    return re.sub(r'[^a-zа-яё0-9]', '', str(text).lower())


def match_name(text, known):
    value = letters(text)
    if not value:
        return None
    # Short noise must never be expanded into a real character's name.
    aliases = {letters(name): name for name in known}
    aliases.update({letters(alias): name for alias, name in RUSSIAN_NAMES.items() if name in known})
    if value in aliases:
        return aliases[value]
    # Portrait details can create isolated noise before the right-aligned label.
    words = str(text).split()
    for count in range(1, min(3, len(words)) + 1):
        suffix = letters(''.join(words[-count:]))
        if suffix in aliases:
            return aliases[suffix]
        # One substitution is allowed for long labels, only with one match.
        matches = [name for alias, name in aliases.items()
                   if len(alias) >= 5 and len(alias) == len(suffix)
                   and sum(a != b for a, b in zip(alias, suffix)) == 1]
        if len(set(matches)) == 1:
            return matches[0]
    return None


def card_boxes(frame):
    height, width = frame.shape[:2]
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(cv2.inRange(grey, 0, 45), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (0.19 * width < w < 0.26 * width and 0.22 * height < h < 0.29 * height):
            continue
        if y < height * 0.1 or x < 5 or x + w >= width - 5:
            continue
        if any(abs(x - a) < 12 and abs(y - b) < 12 for a, b, _, _ in boxes):
            continue
        boxes.append((x, y, w, h))
    return sorted(boxes, key=lambda box: (round(box[1] / (height * 0.13)), box[0]))


def read_card(frame, index, known):
    result = {'brawler': None, 'trophies': None}
    boxes = card_boxes(frame)
    if index >= len(boxes):
        return result
    x, y, w, h = boxes[index]
    # The green upgrade strip is outside the portrait and name.
    crop = frame[y + int(h * .70):y + int(h * .86), x + int(w * .30):x + int(w * .82)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, 190), (180, 90, 255))
    grey = 255 - cv2.resize(white, None, fx=3, fy=3)
    try:
        name = None
        tight = frame[y + int(h * .70):y + int(h * .86), x + int(w * .48):x + int(w * .82)]
        variants = [cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), None, fx=3, fy=3),
                    cv2.resize(cv2.cvtColor(tight, cv2.COLOR_BGR2GRAY), None, fx=3, fy=3), grey]
        for variant in variants:
            for language in ('eng', 'rus'):
                text = pytesseract.image_to_string(variant, lang=language, config='--psm 7')
                name = match_name(text, known)
                if name:
                    break
            if name:
                break
        if not name:
            return result
        trophy_crop = frame[y + int(h * .82):y + int(h * .99), x + int(w * .12):x + int(w * .31)]
        trophy_crop = cv2.resize(cv2.cvtColor(trophy_crop, cv2.COLOR_BGR2GRAY), None, fx=4, fy=4)
        digits = pytesseract.image_to_string(trophy_crop, config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
    except pytesseract.TesseractError:
        return result
    result['brawler'] = name
    result['trophies'] = int(digits) if re.fullmatch(r'\d{1,5}', digits) else None
    height, width = frame.shape[:2]
    result['click'] = ((x + w * .4) * 1920 / width, (y + h * .45) * 1080 / height)
    return result
