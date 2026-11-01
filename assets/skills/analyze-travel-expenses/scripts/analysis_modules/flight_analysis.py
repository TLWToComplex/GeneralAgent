"""机票/住宿财务深度分析模块。

由原独立脚本 analyze_finance.py 原样整合而来：各聚合函数的统计逻辑保持不变，
仅将按列号的字段访问适配为按项目字段名访问，并把硬编码路径的 run_all()
替换为标准模块入口 analyze(records, config)。本模块不读写任何固定路径。
"""
from collections import defaultdict
from datetime import datetime

from .common import num

MODULE_NAME = "flight_analysis"
RECORD_TYPES = ("flight", "hotel")

# 原脚本按列号取字段；这里改为按项目字段名取字段（含常见候选名回退）。
# 数值类字段统一经 num() 转换，兼容 CSV 读入的字符串单元格（与 pandas 自动转数值一致）。
FIELD = {
    '人': ('乘机人',),
    '部门': ('报账部门', '费用承担部门'),
    '类型': ('消费类型',),
    '出发地': ('出发地',),
    '到达地': ('到达地',),
    '标准': ('住宿标准',),
    '天数': ('住宿天数',),
    '等级': ('等级',),
    '价格': ('票面价', '实收实付', '企业支付金额'),
    '服务费': ('服务费',),
    '折扣率': ('折扣率(%)', '折扣率'),
    '预订时间': ('预订时间',),
    '出发时间': ('出发时间',),
}

NUMERIC = {'标准', '天数', '价格', '服务费', '折扣率'}


def g(row, key):
    for name in FIELD[key]:
        if name in row and row[name] not in (None, ""):
            value = row[name]
            if key in NUMERIC:
                return num(value)
            return value
    return None


def valid_room(row):
    p = g(row, '价格')
    d = g(row, '天数')
    s = g(row, '标准')
    try:
        ok = p and p > 0 and d and d > 0 and s and s > 0
    except TypeError:
        return False
    return bool(ok and g(row, '部门'))


def valid_cons(row):
    p = g(row, '价格')
    try:
        return g(row, '类型') in ('机票', '火车票') and p and p > 0 and bool(g(row, '部门'))
    except TypeError:
        return False


def amt(row):
    p = g(row, '价格')
    total = abs(p) if p else 0.0
    fee = g(row, '服务费')
    if fee and fee > 0:
        total += abs(fee)
    return total


def pd_row(row):
    nights = g(row, '天数')
    return amt(row) / nights if nights else 0.0


def ratio(row):
    std = g(row, '标准')
    return pd_row(row) / std if std else 0.0


def ratio_cat(r):
    if r >= 0.95: return '95%以上'
    if r >= 0.90: return '90%-95%'
    if r >= 0.80: return '80%-90%'
    if r >= 0.70: return '70%-80%'
    return '70%以下'


def disc_cat(d):
    if d is None:
        return '8折以上'
    d = num(d)
    if d is None:
        return '8折以上'
    if d == 0:
        return '8折以上'
    if d < 0.4:
        return '4折以下'
    if d < 0.8:
        return '4-8折'
    return '8折以上'


# ========== 1. 住宿按部门顶格 ==========
def room_by_dept(data):
    cats = ['95%以上', '90%-95%', '80%-90%', '70%-80%', '70%以下']
    valid = [r for r in data if valid_room(r)]
    by_dept = defaultdict(list)
    for r in valid:
        by_dept[g(r, '部门')].append(r)

    result = {}
    for dept in sorted(by_dept.keys()):
        rows = by_dept[dept]
        stats = {c: {'count': 0, 'amount': 0} for c in cats}
        total_amt = 0
        for r in rows:
            c = ratio_cat(ratio(r))
            a = amt(r)
            stats[c]['count'] += 1
            stats[c]['amount'] += a
            total_amt += a
        result[dept] = {'stats': stats, 'total_count': len(rows), 'total_amount': round(total_amt, 2)}
    return result


# ========== 2. 住宿按人 top50 ==========
def room_by_person(data):
    cats = ['95%以上', '90%-95%', '80%-90%', '70%-80%', '70%以下']
    ps = defaultdict(lambda: {c: 0 for c in cats})
    ps_amt = defaultdict(float)
    ps_dept = defaultdict(str)
    valid = [r for r in data if valid_room(r)]

    for r in valid:
        p = g(r, '人')
        ps[p][ratio_cat(ratio(r))] += 1
        ps_amt[p] += amt(r)
        ps_dept[p] = g(r, '部门')

    results = []
    for p in ps:
        results.append({
            'person': p, 'dept': ps_dept[p], 'total': sum(ps[p].values()),
            'amount': round(ps_amt[p], 2), **ps[p]
        })
    results.sort(key=lambda x: x['amount'], reverse=True)
    return results[:50]


# ========== 3. 酒店等级 ==========
def hotel_level(data):
    dl = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'amount': 0, 'pds': 0}))
    ls = defaultdict(lambda: {'count': 0, 'amount': 0, 'pds': 0, 'depts': set()})
    valid = [r for r in data if valid_room(r)]

    for r in valid:
        dept = g(r, '部门')
        lv = g(r, '等级') or '未指定/电科商城'
        a = amt(r)
        pd = pd_row(r)
        dl[dept][lv]['count'] += 1
        dl[dept][lv]['amount'] += a
        dl[dept][lv]['pds'] += pd
        ls[lv]['count'] += 1
        ls[lv]['amount'] += a
        ls[lv]['pds'] += pd
        ls[lv]['depts'].add(dept)
    return dl, ls


# ========== 5. 价格偏离 ==========
def price_deviation(data):
    dd = defaultdict(lambda: {'ds': 0, 'n': 0, 'amt': 0, 'st': 0})
    pd2 = defaultdict(lambda: {'ps': 0, 'n': 0, 'amt': 0, 'dept': ''})
    valid = [r for r in data if valid_room(r)]

    for r in valid:
        dept = g(r, '部门')
        person = g(r, '人')
        pd_val = pd_row(r)
        st = g(r, '标准')
        a = amt(r)
        d = (pd_val - st) / st if st > 0 else 0
        dd[dept]['ds'] += d
        dd[dept]['n'] += 1
        dd[dept]['amt'] += a
        dd[dept]['st'] += st * g(r, '天数')
        pd2[person]['ps'] += pd_val
        pd2[person]['n'] += 1
        pd2[person]['amt'] += a
        pd2[person]['dept'] = dept

    dr = []
    for dept, v in dd.items():
        avg_d = round(v['ds'] / v['n'] * 100, 2) if v['n'] else 0
        dr.append({'dept': dept, 'n': v['n'], 'amount': round(v['amt'], 2),
                   'standard': round(v['st'], 2), 'savings': round(v['st'] - v['amt'], 2),
                   'dev_pct': avg_d})
    dr.sort(key=lambda x: x['dev_pct'])

    pr = []
    for p, v in pd2.items():
        avg_p = round(v['ps'] / v['n'], 2) if v['n'] else 0
        pr.append({'person': p, 'dept': v['dept'], 'n': v['n'],
                   'amount': round(v['amt'], 2), 'avg_price': avg_p})
    pr.sort(key=lambda x: x['avg_price'], reverse=True)
    return dr, pr[:50]


# ========== 消费明细: 按部门折扣 ==========
def cons_by_dept(data):
    cats = ['4折以下', '4-8折', '8折以上']
    valid = [r for r in data if valid_cons(r)]
    by_dept = defaultdict(list)
    for r in valid:
        by_dept[g(r, '部门')].append(r)

    result = {}
    for dept in sorted(by_dept.keys()):
        rows = by_dept[dept]
        stats = {c: {'count': 0, 'amount': 0} for c in cats}
        ta = 0
        for r in rows:
            c = disc_cat(g(r, '折扣率'))
            a = abs(g(r, '价格'))
            stats[c]['count'] += 1
            stats[c]['amount'] += a
            ta += a
        result[dept] = {'stats': stats, 'total_count': len(rows), 'total_amount': round(ta, 2)}
    return result


# ========== 消费明细: 按人折扣 top50 ==========
def cons_by_person(data):
    cats = ['4折以下', '4-8折', '8折以上']
    ps = defaultdict(lambda: {c: 0 for c in cats})
    ps_amt = defaultdict(lambda: {c: 0.0 for c in cats})
    pa = defaultdict(float)
    pd3 = defaultdict(str)
    valid = [r for r in data if valid_cons(r)]

    for r in valid:
        p = g(r, '人')
        c = disc_cat(g(r, '折扣率'))
        a = abs(g(r, '价格'))
        ps[p][c] += 1
        ps_amt[p][c] += a
        pa[p] += a
        pd3[p] = g(r, '部门')

    results = []
    for p in ps:
        total_cnt = sum(ps[p].values())
        total_amt = pa[p]
        item = {
            'person': p, 'dept': pd3[p], 'total': total_cnt,
            'amount': round(total_amt, 2)
        }
        for c in cats:
            cnt = ps[p][c]
            amt = ps_amt[p][c]
            item[c] = cnt  # 兼容旧字段: 各档次数
            item[f'{c}_amount'] = round(amt, 2)  # 各档金额
            item[f'{c}_cnt_pct'] = round(cnt / total_cnt, 4) if total_cnt else 0  # 各档次数占比
            item[f'{c}_amt_pct'] = round(amt / total_amt, 4) if total_amt else 0  # 各档金额占比
        results.append(item)
    results.sort(key=lambda x: x['amount'], reverse=True)
    return results[:50]


# ========== 消费明细: 按航线 ==========
def cons_by_route(data):
    rs = defaultdict(lambda: {'count': 0, 'amount': 0})
    valid = [r for r in data if valid_cons(r)]
    tc = 0
    ta = 0

    for r in valid:
        dep = g(r, '出发地') or '未知'
        arr = g(r, '到达地') or '未知'
        route = f"{dep} -> {arr}"
        a = abs(g(r, '价格'))
        rs[route]['count'] += 1
        rs[route]['amount'] += a
        tc += 1
        ta += a

    results = []
    for route, s in rs.items():
        results.append({
            'route': route, 'count': s['count'], 'amount': round(s['amount'], 2),
            'count_pct': f"{s['count']/tc*100:.1f}%" if tc else "0%",
            'amount_pct': f"{s['amount']/ta*100:.1f}%" if ta else "0%"
        })
    results.sort(key=lambda x: x['amount'], reverse=True)
    return results


# ========== 消费明细: 按部门统计机票/火车票次数 ==========
def cons_by_dept_type(data):
    by_dept = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'amount': 0}))
    valid = [r for r in data if valid_cons(r)]

    for r in valid:
        dept = g(r, '部门')
        tp = g(r, '类型')
        a = abs(g(r, '价格'))
        by_dept[dept][tp]['count'] += 1
        by_dept[dept][tp]['amount'] += a

    result = {}
    for dept in sorted(by_dept.keys()):
        types = by_dept[dept]
        tc = sum(v['count'] for v in types.values())
        ta = sum(v['amount'] for v in types.values())
        result[dept] = {
            'types': {tp: {'count': v['count'], 'amount': round(v['amount'], 2)}
                      for tp, v in types.items()},
            'total_count': tc,
            'total_amount': round(ta, 2)
        }
    return result


# ========== 消费明细: 机票提前预定统计(全局) ==========
def flight_advance(data):
    cats = ['当天订', '提前1天', '提前2天', '提前3天及以上']
    stats = {c: {'count': 0, 'amount': 0} for c in cats}
    tc = 0
    ta = 0.0
    invalid = 0

    def to_dt(v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str) and v.strip():
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
                        '%Y/%m/%d %H:%M:%S', '%Y/%m/%d %H:%M', '%Y/%m/%d'):
                try:
                    return datetime.strptime(v.strip(), fmt)
                except ValueError:
                    continue
        return None

    for r in data:
        if g(r, '类型') != '机票':
            continue
        p = g(r, '价格')
        if not p or p <= 0:
            continue
        bt = to_dt(g(r, '预订时间'))
        dt = to_dt(g(r, '出发时间'))
        if bt is None or dt is None:
            invalid += 1
            continue
        days = (dt.date() - bt.date()).days  # 按自然日计算提前天数
        if days < 0:
            invalid += 1
            continue
        if days == 0:
            cat = '当天订'
        elif days == 1:
            cat = '提前1天'
        elif days == 2:
            cat = '提前2天'
        else:
            cat = '提前3天及以上'
        a = abs(p)
        stats[cat]['count'] += 1
        stats[cat]['amount'] += a
        tc += 1
        ta += a

    return {
        'stats': {c: {'count': v['count'], 'amount': round(v['amount'], 2),
                      'cnt_pct': round(v['count'] / tc, 4) if tc else 0,
                      'amt_pct': round(v['amount'] / ta, 4) if ta else 0}
                  for c, v in stats.items()},
        'total_count': tc,
        'total_amount': round(ta, 2),
        'invalid': invalid
    }


def _analyze_flight(cons):
    """cons: 机票/火车票记录列表；统计口径与原脚本一致。"""
    results = {}
    results['cons_dept'] = cons_by_dept(cons)
    results['cons_person'] = cons_by_person(cons)
    results['cons_route'] = cons_by_route(cons)
    results['cons_dept_type'] = cons_by_dept_type(cons)
    results['flight_advance'] = flight_advance(cons)
    # 校验：明细口径总金额与总体平衡
    valid = [r for r in cons if valid_cons(r)]
    results['_validation'] = {
        'cons_total_count': len(valid),
        'cons_total_amount': round(sum(abs(g(r, '价格')) for r in valid), 2),
    }
    return results


def _analyze_room(room):
    """room: 住宿记录列表；统计口径与原脚本一致。"""
    results = {}
    results['room_dept'] = room_by_dept(room)
    results['room_person'] = room_by_person(room)
    dl, ls = hotel_level(room)
    results['hotel_level_dept'] = dl
    # depts 为 set，转为列表以便 JSON 序列化
    results['hotel_level_summary'] = {
        lv: {'count': v['count'], 'amount': round(v['amount'], 2),
             'avg_pd': round(v['pds'] / v['count'], 2) if v['count'] else 0,
             'depts': sorted(v['depts'])}
        for lv, v in ls.items()
    }
    dd, dr = price_deviation(room)
    results['room_dev_dept'] = dd
    results['room_dev_person'] = dr
    results['_validation'] = {
        'room_total_count': sum(d['total_count'] for d in results['room_dept'].values()),
        'room_total_amount': round(sum(d['total_amount'] for d in results['room_dept'].values()), 2),
    }
    return results


def analyze(records, config):
    if isinstance(records, dict):
        cons = records.get('flight', [])
        room = records.get('hotel', [])
        results = _analyze_flight(cons)
        results.update(_analyze_room(room))
        results['status'] = 'ok'
        results['source'] = 'module'
        results['cons_count'] = len(cons)
        results['room_count'] = len(room)
        return results
    # 兼容：直接传入住宿记录列表（仅住宿口径）
    return _analyze_room(records)