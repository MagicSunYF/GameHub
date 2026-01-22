/**
 * 斗地主牌型识别测试
 * 验证需求 13.6: 识别单牌、对子、三张、顺子、炸弹、火箭等牌型
 */

const assert = require('assert');

// 牌型定义（从game.js复制）
const CARD_VALUES = {
    '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 15, 'joker': 16, 'JOKER': 17
};

// 牌型分析函数（从game.js复制）
function analyzeCardType(cards) {
    if (cards.length === 0) return { valid: false };
    
    const values = cards.map(c => CARD_VALUES[c.value]).sort((a, b) => a - b);
    const counts = {};
    values.forEach(v => counts[v] = (counts[v] || 0) + 1);
    const uniqueValues = Object.keys(counts).map(Number).sort((a, b) => a - b);
    const countArr = Object.values(counts).sort((a, b) => b - a);
    
    // 火箭 (Rocket): 小王+大王
    if (cards.length === 2 && values[0] === 16 && values[1] === 17) {
        return { valid: true, type: 'rocket', value: 17 };
    }
    
    // 炸弹 (Bomb): 四张相同
    if (cards.length === 4 && countArr[0] === 4) {
        return { valid: true, type: 'bomb', value: uniqueValues[0] };
    }
    
    // 单张 (Single)
    if (cards.length === 1) {
        return { valid: true, type: 'single', value: values[0] };
    }
    
    // 对子 (Pair)
    if (cards.length === 2 && countArr[0] === 2) {
        return { valid: true, type: 'pair', value: uniqueValues[0] };
    }
    
    // 三张 (Triple)
    if (cards.length === 3 && countArr[0] === 3) {
        return { valid: true, type: 'triple', value: uniqueValues[0] };
    }
    
    // 三带一 (Triple with Single)
    if (cards.length === 4 && countArr[0] === 3 && countArr[1] === 1) {
        const tripleValue = uniqueValues.find(v => counts[v] === 3);
        return { valid: true, type: 'triple_single', value: tripleValue };
    }
    
    // 三带一对 (Triple with Pair)
    if (cards.length === 5 && countArr[0] === 3 && countArr[1] === 2) {
        const tripleValue = uniqueValues.find(v => counts[v] === 3);
        return { valid: true, type: 'triple_pair', value: tripleValue };
    }
    
    // 顺子 (Straight): 至少5张连续单牌，不能包含2和王
    if (cards.length >= 5 && countArr[0] === 1) {
        const maxValue = Math.max(...uniqueValues);
        // 顺子不能包含2(15)和王(16,17)
        if (maxValue <= 14 && isSequence(uniqueValues)) {
            return { valid: true, type: 'straight', value: uniqueValues[0], length: cards.length };
        }
    }
    
    // 连对 (Consecutive Pairs): 至少3对连续对子
    if (cards.length >= 6 && cards.length % 2 === 0) {
        const pairCount = cards.length / 2;
        if (pairCount >= 3 && countArr[0] === 2 && uniqueValues.length === pairCount) {
            const maxValue = Math.max(...uniqueValues);
            // 连对不能包含2(15)和王(16,17)
            if (maxValue <= 14 && isSequence(uniqueValues)) {
                return { valid: true, type: 'consecutive_pairs', value: uniqueValues[0], length: pairCount };
            }
        }
    }
    
    // 飞机 (Plane): 至少2个连续三张
    if (cards.length >= 6) {
        const tripleValues = uniqueValues.filter(v => counts[v] === 3);
        if (tripleValues.length >= 2 && isSequence(tripleValues)) {
            const maxValue = Math.max(...tripleValues);
            // 飞机不能包含2(15)和王(16,17)
            if (maxValue <= 14) {
                // 纯飞机（只有三张）
                if (cards.length === tripleValues.length * 3) {
                    return { valid: true, type: 'plane', value: tripleValues[0], length: tripleValues.length };
                }
                // 飞机带单牌
                if (cards.length === tripleValues.length * 4 && uniqueValues.length === tripleValues.length * 2) {
                    return { valid: true, type: 'plane_single', value: tripleValues[0], length: tripleValues.length };
                }
                // 飞机带对子
                if (cards.length === tripleValues.length * 5) {
                    const pairValues = uniqueValues.filter(v => counts[v] === 2);
                    if (pairValues.length === tripleValues.length) {
                        return { valid: true, type: 'plane_pair', value: tripleValues[0], length: tripleValues.length };
                    }
                }
            }
        }
    }
    
    // 四带二 (Four with Two): 四张+两张单牌或两对
    if (cards.length === 6 && countArr[0] === 4) {
        const quadValue = uniqueValues.find(v => counts[v] === 4);
        return { valid: true, type: 'four_two_single', value: quadValue };
    }
    
    if (cards.length === 8 && countArr[0] === 4 && countArr[1] === 2 && countArr[2] === 2) {
        const quadValue = uniqueValues.find(v => counts[v] === 4);
        return { valid: true, type: 'four_two_pair', value: quadValue };
    }
    
    return { valid: false };
}

function isSequence(values) {
    if (values.length < 2) return false;
    for (let i = 1; i < values.length; i++) {
        if (values[i] !== values[i-1] + 1) return false;
    }
    return true;
}

// 辅助函数：创建牌
function card(value, suit = '♠') {
    return { value, suit };
}

// 测试运行器
function runTests() {
    let passed = 0;
    let failed = 0;
    const failures = [];

    function test(name, fn) {
        try {
            fn();
            passed++;
            console.log(`✓ ${name}`);
        } catch (e) {
            failed++;
            failures.push({ name, error: e.message });
            console.log(`✗ ${name}: ${e.message}`);
        }
    }

    console.log('\n=== 斗地主牌型识别测试 ===\n');

    // 单牌测试
    console.log('单牌 (Single):');
    test('识别单张3', () => {
        const result = analyzeCardType([card('3')]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'single');
        assert.strictEqual(result.value, 3);
    });
    
    test('识别单张A', () => {
        const result = analyzeCardType([card('A')]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'single');
        assert.strictEqual(result.value, 14);
    });

    // 对子测试
    console.log('\n对子 (Pair):');
    test('识别对子', () => {
        const result = analyzeCardType([card('5', '♠'), card('5', '♥')]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'pair');
        assert.strictEqual(result.value, 5);
    });

    // 三张测试
    console.log('\n三张 (Triple):');
    test('识别三张', () => {
        const result = analyzeCardType([card('7', '♠'), card('7', '♥'), card('7', '♣')]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'triple');
        assert.strictEqual(result.value, 7);
    });

    // 三带一测试
    console.log('\n三带一 (Triple with Single):');
    test('识别三带一', () => {
        const result = analyzeCardType([
            card('8', '♠'), card('8', '♥'), card('8', '♣'), card('3')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'triple_single');
        assert.strictEqual(result.value, 8);
    });

    // 三带一对测试
    console.log('\n三带一对 (Triple with Pair):');
    test('识别三带一对', () => {
        const result = analyzeCardType([
            card('9', '♠'), card('9', '♥'), card('9', '♣'),
            card('4', '♠'), card('4', '♥')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'triple_pair');
        assert.strictEqual(result.value, 9);
    });

    // 顺子测试
    console.log('\n顺子 (Straight):');
    test('识别5张顺子', () => {
        const result = analyzeCardType([
            card('3'), card('4'), card('5'), card('6'), card('7')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'straight');
        assert.strictEqual(result.value, 3);
        assert.strictEqual(result.length, 5);
    });
    
    test('识别12张顺子', () => {
        const result = analyzeCardType([
            card('3'), card('4'), card('5'), card('6'), card('7'),
            card('8'), card('9'), card('10'), card('J'), card('Q'),
            card('K'), card('A')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'straight');
        assert.strictEqual(result.length, 12);
    });
    
    test('顺子不能包含2', () => {
        const result = analyzeCardType([
            card('A'), card('2'), card('3'), card('4'), card('5')
        ]);
        assert.strictEqual(result.valid, false);
    });
    
    test('少于5张不是顺子', () => {
        const result = analyzeCardType([
            card('3'), card('4'), card('5'), card('6')
        ]);
        assert.strictEqual(result.valid, false);
    });

    // 连对测试
    console.log('\n连对 (Consecutive Pairs):');
    test('识别3连对', () => {
        const result = analyzeCardType([
            card('3', '♠'), card('3', '♥'),
            card('4', '♠'), card('4', '♥'),
            card('5', '♠'), card('5', '♥')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'consecutive_pairs');
        assert.strictEqual(result.value, 3);
        assert.strictEqual(result.length, 3);
    });
    
    test('识别10连对', () => {
        const result = analyzeCardType([
            card('3', '♠'), card('3', '♥'),
            card('4', '♠'), card('4', '♥'),
            card('5', '♠'), card('5', '♥'),
            card('6', '♠'), card('6', '♥'),
            card('7', '♠'), card('7', '♥'),
            card('8', '♠'), card('8', '♥'),
            card('9', '♠'), card('9', '♥'),
            card('10', '♠'), card('10', '♥'),
            card('J', '♠'), card('J', '♥'),
            card('Q', '♠'), card('Q', '♥')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'consecutive_pairs');
        assert.strictEqual(result.length, 10);
    });
    
    test('连对不能包含2', () => {
        const result = analyzeCardType([
            card('A', '♠'), card('A', '♥'),
            card('2', '♠'), card('2', '♥'),
            card('3', '♠'), card('3', '♥')
        ]);
        assert.strictEqual(result.valid, false);
    });
    
    test('少于3连对无效', () => {
        const result = analyzeCardType([
            card('5', '♠'), card('5', '♥'),
            card('6', '♠'), card('6', '♥')
        ]);
        assert.strictEqual(result.valid, false);
    });

    // 飞机测试
    console.log('\n飞机 (Plane):');
    test('识别纯飞机（2个三张）', () => {
        const result = analyzeCardType([
            card('5', '♠'), card('5', '♥'), card('5', '♣'),
            card('6', '♠'), card('6', '♥'), card('6', '♣')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'plane');
        assert.strictEqual(result.value, 5);
        assert.strictEqual(result.length, 2);
    });
    
    test('识别飞机带单牌', () => {
        const result = analyzeCardType([
            card('7', '♠'), card('7', '♥'), card('7', '♣'),
            card('8', '♠'), card('8', '♥'), card('8', '♣'),
            card('3'), card('4')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'plane_single');
        assert.strictEqual(result.value, 7);
        assert.strictEqual(result.length, 2);
    });
    
    test('识别飞机带对子', () => {
        const result = analyzeCardType([
            card('9', '♠'), card('9', '♥'), card('9', '♣'),
            card('10', '♠'), card('10', '♥'), card('10', '♣'),
            card('3', '♠'), card('3', '♥'),
            card('4', '♠'), card('4', '♥')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'plane_pair');
        assert.strictEqual(result.value, 9);
        assert.strictEqual(result.length, 2);
    });
    
    test('飞机不能包含2', () => {
        const result = analyzeCardType([
            card('A', '♠'), card('A', '♥'), card('A', '♣'),
            card('2', '♠'), card('2', '♥'), card('2', '♣')
        ]);
        assert.strictEqual(result.valid, false);
    });

    // 炸弹测试
    console.log('\n炸弹 (Bomb):');
    test('识别炸弹', () => {
        const result = analyzeCardType([
            card('6', '♠'), card('6', '♥'), card('6', '♣'), card('6', '♦')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'bomb');
        assert.strictEqual(result.value, 6);
    });
    
    test('识别2炸弹', () => {
        const result = analyzeCardType([
            card('2', '♠'), card('2', '♥'), card('2', '♣'), card('2', '♦')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'bomb');
        assert.strictEqual(result.value, 15);
    });

    // 火箭测试
    console.log('\n火箭 (Rocket):');
    test('识别火箭', () => {
        const result = analyzeCardType([
            card('joker', ''), card('JOKER', '')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'rocket');
        assert.strictEqual(result.value, 17);
    });

    // 四带二测试
    console.log('\n四带二:');
    test('识别四带二单牌', () => {
        const result = analyzeCardType([
            card('8', '♠'), card('8', '♥'), card('8', '♣'), card('8', '♦'),
            card('3'), card('4')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'four_two_single');
        assert.strictEqual(result.value, 8);
    });
    
    test('识别四带二对', () => {
        const result = analyzeCardType([
            card('K', '♠'), card('K', '♥'), card('K', '♣'), card('K', '♦'),
            card('5', '♠'), card('5', '♥'),
            card('6', '♠'), card('6', '♥')
        ]);
        assert.strictEqual(result.valid, true);
        assert.strictEqual(result.type, 'four_two_pair');
        assert.strictEqual(result.value, 13);
    });

    // 无效牌型测试
    console.log('\n无效牌型:');
    test('空牌组无效', () => {
        const result = analyzeCardType([]);
        assert.strictEqual(result.valid, false);
    });
    
    test('不连续的牌无效', () => {
        const result = analyzeCardType([
            card('3'), card('5'), card('7')
        ]);
        assert.strictEqual(result.valid, false);
    });

    // 输出结果
    console.log('\n=== 测试结果 ===');
    console.log(`通过: ${passed}`);
    console.log(`失败: ${failed}`);
    console.log(`总计: ${passed + failed}`);
    
    if (failed > 0) {
        console.log('\n失败的测试:');
        failures.forEach(f => console.log(`  - ${f.name}: ${f.error}`));
        process.exit(1);
    } else {
        console.log('\n✓ 所有测试通过!');
        process.exit(0);
    }
}

// 运行测试
if (require.main === module) {
    runTests();
}

module.exports = { analyzeCardType, isSequence, CARD_VALUES };
