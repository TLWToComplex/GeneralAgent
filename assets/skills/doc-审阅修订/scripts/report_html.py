"""
report_html.py — 格式化报告 HTML 生成器

将校验结果、自审结果、修复记录、差异比对合并为一份
可阅读的 HTML 报告，方便人工审核和存档。
"""
import json
from pathlib import Path
from utils import log


def _severity_label(s):
    return {'error': '错误', 'warning': '警告', 'info': '提示','PASS':'通过','FAIL':'失败','WARN':'警告'}.get(s, s)


def _severity_color(s):
    return {'error':'#E24B4A','warning':'#EF9F27','info':'#85B7EB','PASS':'#639922','FAIL':'#E24B4A','WARN':'#EF9F27'}.get(s,'#888')


def generate_html(report: dict, output_path: str, title: str = "格式校验报告"):
    """生成可视化 HTML 报告。

    Args:
        report: final-report.json 解析后的 dict
        output_path: 输出 .html 文件路径
        title: 报告标题
    """
    summary = report.get('summary', {})
    results = report.get('results', [])
    self_review = report.get('self_review', [])
    sr_summary = report.get('self_review_summary', {})
    filepath = report.get('filepath', '')

    # 统计
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    warned = summary.get('warned', 0)
    total = summary.get('total', 0)
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    # 格式化校验结果行
    rows = []
    for r in results:
        st = r['status']
        ck = r['check_id']
        msg = r['message']
        exp = r.get('expected', '')
        act = r.get('actual', '')
        loc = r.get('location', '')
        color = _severity_color(st)

        detail = ''
        if exp or act:
            detail = '<div class="detail">期望: %s &nbsp;|&nbsp; 实际: %s</div>' % (exp or '-', act or '-')
        if loc:
            detail += '<div class="detail">位置: %s</div>' % loc

        rows.append('''<tr>
            <td><span class="badge" style="background:%s">%s</span></td>
            <td>%s</td>
            <td>%s%s</td>
        </tr>''' % (color, _severity_label(st), ck, msg, detail))

    # 自审结果
    sr_rows = []
    for sr in self_review:
        sev = sr.get('severity', 'info')
        color = _severity_color(sev)
        name = sr.get('name', '')
        pid = sr.get('id', '')
        desc = sr.get('description', '')
        hint = sr.get('fix_hint', '')
        positions = sr.get('positions', [])

        pos_html = ''
        if positions:
            items = []
            for pos, d in positions[:8]:
                items.append('<span class="pos">P[%d]: %s</span>' % (pos, d[:40]))
            pos_html = '<div class="positions">%s</div>' % '<br>'.join(items)
            if len(positions) > 8:
                pos_html += '<div class="detail">... 还有 %d 处</div>' % (len(positions) - 8)

        sr_rows.append('''<tr>
            <td><span class="badge" style="background:%s">%s</span></td>
            <td>%s <span class="id">%s</span></td>
            <td>%s<div class="detail">%s</div></td>
            <td>%s</td>
        </tr>''' % (color, _severity_label(sev), name, pid, desc, hint, pos_html))

    # 构建 HTML
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8">
<title>%s</title>
<style>
body{font-family:-apple-system,sans-serif;margin:0;padding:20px;background:#f5f5f5;color:#333}
.container{max-width:1200px;margin:0 auto}
.header{background:#fff;padding:24px 32px;border-radius:12px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.header h1{margin:0 0 8px;font-size:20px;font-weight:500}
.header .path{color:#888;font-size:13px}
.summary-card{display:inline-block;padding:12px 24px;border-radius:8px;margin-right:12px;margin-top:12px;text-align:center;min-width:80px}
.summary-card .num{font-size:24px;font-weight:500}
.summary-card .label{font-size:12px;color:#666}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
table{width:100%%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:16px}
th{padding:10px 16px;text-align:left;font-weight:500;font-size:13px;background:#f8f8f8;border-bottom:1px solid #eee;position:sticky;top:0}
td{padding:10px 16px;font-size:13px;border-bottom:1px solid #f0f0f0;vertical-align:top}
tr:last-child td{border-bottom:none}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;color:#fff;font-size:11px;font-weight:500;min-width:32px;text-align:center}
.detail{color:#888;font-size:12px;margin-top:4px}
.id{color:#aaa;font-size:11px;font-weight:400}
.positions{margin-top:4px;font-size:12px;color:#555;line-height:1.6}
.pos{display:inline-block;margin-right:8px}
.section-title{font-size:16px;font-weight:500;margin:20px 0 8px}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.stats .item{background:#fff;padding:8px 16px;border-radius:8px;font-size:13px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.stats .item .v{font-weight:500}
</style></head>
<body><div class="container">

<div class="header">
<h1>%s</h1>
<div class="path">%s</div>
<div class="stats">
  <div class="item">通过率 <span class="v" style="color:%s">%s%%</span></div>
  <div class="item">校验项 <span class="v">%s</span></div>
  <div class="item">通过 <span class="v" style="color:#639922">%s</span></div>
  <div class="item">失败 <span class="v" style="color:#E24B4A">%s</span></div>
  <div class="item">警告 <span class="v" style="color:#EF9F27">%s</span></div>
</div>
</div>
''' % (title, title, filepath,
       '#E24B4A' if failed > 0 else '#639922', pass_rate,
       total, passed, failed, warned)

    # 自审概览
    if sr_rows:
        sr_total = sr_summary.get('total', 0)
        sr_err = sr_summary.get('error', 0)
        sr_warn = sr_summary.get('warning', 0)
        sr_info = sr_summary.get('info', 0)
        html += '''<div class="section-title">语义级自审 <span style="font-size:13px;font-weight:400;color:#888">(%d 项, 错误 %d, 警告 %d, 提示 %d)</span></div>
<table><tr><th style="width:60px">级别</th><th style="width:220px">缺陷</th><th>说明</th><th>位置 / 修复建议</th></tr>%s</table>''' % (
            sr_total, sr_err, sr_warn, sr_info, '\n'.join(sr_rows))

    # 校验明细
    html += '''<div class="section-title">格式规则校验 <span style="font-size:13px;font-weight:400;color:#888">(%d 项)</span></div>
<table><tr><th style="width:60px">结果</th><th style="width:200px">检查项</th><th>详情</th></tr>%s</table>''' % (total, '\n'.join(rows))

    # 自审统计卡片
    if sr_rows:
        html += '''<div style="display:flex;gap:12px;margin:16px 0">
          <div class="summary-card" style="border:1px solid #E24B4A"><div class="num" style="color:#E24B4A">%d</div><div class="label">语义错误</div></div>
          <div class="summary-card" style="border:1px solid #EF9F27"><div class="num" style="color:#EF9F27">%d</div><div class="label">语义警告</div></div>
        </div>''' % (sr_err, sr_warn)

    html += '''
<div style="text-align:center;padding:20px;color:#aaa;font-size:12px">
  由 doc-审阅修订 自动生成 &mdash; 生成时间: %s
</div>
</div></body></html>''' % (__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'))

    Path(output_path).write_text(html, encoding='utf-8')
    log.info("HTML 报告已生成: %s" % output_path)
    return output_path


def generate_from_json(json_path: str, output_html: str = None):
    """从 report JSON 文件生成 HTML。"""
    with open(json_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    if not output_html:
        output_html = str(Path(json_path).with_suffix('.html'))
    return generate_html(report, output_html)
