"""
斗地主牌型识别和比较模块
验证需求 13.5: 实现牌型比较逻辑
验证需求 13.6: 识别单牌、对子、三张、顺子、连对、飞机、炸弹、火箭等牌型
"""

# 牌型定义
CARD_VALUES = {
    '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 15, 'joker': 16, 'JOKER': 17
}


def analyze_card_type(cards):
    """
    分析牌型
    
    Args:
        cards: 牌列表，每张牌是 {'value': str, 'suit': str}
    
    Returns:
        dict: {
            'valid': bool,           # 是否是合法牌型
            'type': str,             # 牌型类型
            'value': int,            # 主牌值（用于比较）
            'length': int (可选)     # 长度（顺子、连对、飞机等）
        }
    """
    if len(cards) == 0:
        return {'valid': False}
    
    values = sorted([CARD_VALUES[c['value']] for c in cards])
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    
    unique_values = sorted(counts.keys())
    count_arr = sorted(counts.values(), reverse=True)
    
    # 火箭 (Rocket): 小王+大王
    if len(cards) == 2 and values[0] == 16 and values[1] == 17:
        return {'valid': True, 'type': 'rocket', 'value': 17}
    
    # 炸弹 (Bomb): 四张相同
    if len(cards) == 4 and count_arr[0] == 4:
        return {'valid': True, 'type': 'bomb', 'value': unique_values[0]}
    
    # 单张 (Single)
    if len(cards) == 1:
        return {'valid': True, 'type': 'single', 'value': values[0]}
    
    # 对子 (Pair)
    if len(cards) == 2 and count_arr[0] == 2:
        return {'valid': True, 'type': 'pair', 'value': unique_values[0]}
    
    # 三张 (Triple)
    if len(cards) == 3 and count_arr[0] == 3:
        return {'valid': True, 'type': 'triple', 'value': unique_values[0]}
    
    # 三带一 (Triple with Single)
    if len(cards) == 4 and count_arr[0] == 3 and count_arr[1] == 1:
        triple_value = [v for v in unique_values if counts[v] == 3][0]
        return {'valid': True, 'type': 'triple_single', 'value': triple_value}
    
    # 三带一对 (Triple with Pair)
    if len(cards) == 5 and count_arr[0] == 3 and count_arr[1] == 2:
        triple_value = [v for v in unique_values if counts[v] == 3][0]
        return {'valid': True, 'type': 'triple_pair', 'value': triple_value}
    
    # 顺子 (Straight): 至少5张连续单牌，不能包含2和王
    if len(cards) >= 5 and count_arr[0] == 1:
        max_value = max(unique_values)
        # 顺子不能包含2(15)和王(16,17)
        if max_value <= 14 and is_sequence(unique_values):
            return {'valid': True, 'type': 'straight', 'value': unique_values[0], 'length': len(cards)}
    
    # 连对 (Consecutive Pairs): 至少3对连续对子
    if len(cards) >= 6 and len(cards) % 2 == 0:
        pair_count = len(cards) // 2
        if pair_count >= 3 and count_arr[0] == 2 and len(unique_values) == pair_count:
            max_value = max(unique_values)
            # 连对不能包含2(15)和王(16,17)
            if max_value <= 14 and is_sequence(unique_values):
                return {'valid': True, 'type': 'consecutive_pairs', 'value': unique_values[0], 'length': pair_count}
    
    # 飞机 (Plane): 至少2个连续三张
    if len(cards) >= 6:
        triple_values = [v for v in unique_values if counts[v] == 3]
        if len(triple_values) >= 2 and is_sequence(triple_values):
            max_value = max(triple_values)
            # 飞机不能包含2(15)和王(16,17)
            if max_value <= 14:
                # 纯飞机（只有三张）
                if len(cards) == len(triple_values) * 3:
                    return {'valid': True, 'type': 'plane', 'value': triple_values[0], 'length': len(triple_values)}
                # 飞机带单牌
                if len(cards) == len(triple_values) * 4 and len(unique_values) == len(triple_values) * 2:
                    return {'valid': True, 'type': 'plane_single', 'value': triple_values[0], 'length': len(triple_values)}
                # 飞机带对子
                if len(cards) == len(triple_values) * 5:
                    pair_values = [v for v in unique_values if counts[v] == 2]
                    if len(pair_values) == len(triple_values):
                        return {'valid': True, 'type': 'plane_pair', 'value': triple_values[0], 'length': len(triple_values)}
    
    # 四带二 (Four with Two): 四张+两张单牌或两对
    if len(cards) == 6 and count_arr[0] == 4:
        quad_value = [v for v in unique_values if counts[v] == 4][0]
        return {'valid': True, 'type': 'four_two_single', 'value': quad_value}
    
    if len(cards) == 8 and count_arr[0] == 4 and count_arr[1] == 2 and count_arr[2] == 2:
        quad_value = [v for v in unique_values if counts[v] == 4][0]
        return {'valid': True, 'type': 'four_two_pair', 'value': quad_value}
    
    return {'valid': False}


def is_sequence(values):
    """检查是否连续"""
    if len(values) < 2:
        return False
    for i in range(1, len(values)):
        if values[i] != values[i-1] + 1:
            return False
    return True


def can_beat(current_cards, last_cards):
    """
    判断当前出牌是否能压过上一手牌
    
    Args:
        current_cards: 当前出的牌
        last_cards: 上一手牌（如果为空，表示首次出牌）
    
    Returns:
        bool: True表示可以出，False表示不能出
    """
    # 首次出牌，任何合法牌型都可以
    if not last_cards:
        current_type = analyze_card_type(current_cards)
        return current_type['valid']
    
    current_type = analyze_card_type(current_cards)
    last_type = analyze_card_type(last_cards)
    
    # 当前牌型无效
    if not current_type['valid']:
        return False
    
    # 上一手牌型无效（理论上不应该发生）
    if not last_type['valid']:
        return True
    
    # 火箭可以压任何牌
    if current_type['type'] == 'rocket':
        return True
    
    # 炸弹可以压除火箭外的任何牌
    if current_type['type'] == 'bomb':
        if last_type['type'] == 'rocket':
            return False
        if last_type['type'] == 'bomb':
            # 炸弹比大小
            return current_type['value'] > last_type['value']
        # 炸弹可以压其他任何牌型
        return True
    
    # 非炸弹/火箭不能压炸弹和火箭
    if last_type['type'] in ['bomb', 'rocket']:
        return False
    
    # 同类型牌型比较
    if current_type['type'] != last_type['type']:
        return False
    
    # 对于有长度的牌型（顺子、连对、飞机），长度必须相同
    if 'length' in current_type and 'length' in last_type:
        if current_type['length'] != last_type['length']:
            return False
    
    # 比较主牌值
    return current_type['value'] > last_type['value']


def validate_play(cards, last_play):
    """
    验证出牌是否合法
    
    Args:
        cards: 要出的牌
        last_play: 上一手牌
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not cards:
        return False, "出牌不能为空"
    
    card_type = analyze_card_type(cards)
    
    if not card_type['valid']:
        return False, "不是合法的牌型"
    
    if not can_beat(cards, last_play):
        if last_play:
            return False, "无法压过上一手牌"
        else:
            return False, "牌型无效"
    
    return True, "出牌合法"
