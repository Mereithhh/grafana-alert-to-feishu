import json
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 从环境变量获取飞书Webhook URL，如果没有则使用默认值
FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL', 'https://open.feishu.cn/open-apis/bot/v2/hook/15822684-b440-4129-884c-58045f3e91f7')

# 告警状态对应的颜色
ALERT_COLORS = {
    "firing": "red",
    "resolved": "green",
    "pending": "yellow"
}

def format_time(time_str):
    """格式化时间为更易读的格式"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return time_str

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok"}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """处理Grafana告警Webhook"""
    if not request.json:
        logger.error("接收到的请求体不是JSON格式")
        return jsonify({"status": "error", "message": "请求体必须为JSON格式"}), 400
    
    try:
        grafana_alert = request.json
        logger.info(f"接收到来自Grafana的告警: {json.dumps(grafana_alert, ensure_ascii=False)}")
        
        # 发送飞书消息
        send_to_feishu(grafana_alert)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.exception(f"处理告警时发生错误: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_to_feishu(alert_data):
    """发送告警数据到飞书"""
    import requests
    
    status = alert_data.get('status', '未知')
    alerts = alert_data.get('alerts', [])
    title = alert_data.get('title', '未知告警')
    
    # 创建飞书卡片
    card = create_feishu_card(status, title, alerts, alert_data)
    
    # 发送到飞书
    headers = {'Content-Type': 'application/json'}
    payload = {"msg_type": "interactive", "card": card}
    
    try:
        response = requests.post(FEISHU_WEBHOOK_URL, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info("成功发送告警到飞书")
        else:
            logger.error(f"发送告警到飞书失败: {response.status_code}, {response.text}")
    except Exception as e:
        logger.exception(f"发送告警到飞书时发生错误: {str(e)}")

def get_instance_info(alert_labels):
    """从多种可能的标签中获取实例信息"""
    # 按优先级尝试不同的标签
    for label in ['instance', 'node', 'host', 'method', 'job']:
        if label in alert_labels and alert_labels[label]:
            return alert_labels[label]
    
    # 如果找不到常见的标签，尝试组合非空标签值作为实例标识
    non_empty_labels = {k: v for k, v in alert_labels.items() 
                       if v and k not in ['alertname', 'severity']}
    
    if non_empty_labels:
        return ", ".join([f"{k}={v}" for k, v in non_empty_labels.items()])
    
    return "未知"

def is_valid_url(url):
    """检查URL是否有效"""
    if not url:
        return False
    if url == "":
        return False
    # 简单检查是否是一个网址格式
    return url.startswith(('http://', 'https://'))

def group_alerts_by_name(alerts):
    """按告警名称分组告警"""
    grouped = defaultdict(list)
    for alert in alerts:
        alert_name = alert.get('labels', {}).get('alertname', '未知告警')
        grouped[alert_name].append(alert)
    return grouped

def create_feishu_card(status, title, alerts, alert_data):
    """创建飞书卡片"""
    status_color = ALERT_COLORS.get(status.lower(), "grey")
    
    # 按告警名称分组告警
    grouped_alerts = group_alerts_by_name(alerts)
    
    card = {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": title
            },
            "template": status_color
        },
        "elements": []
    }
    
    # 添加总体摘要
    firing_count = sum(1 for alert in alerts if alert.get('status') == 'firing')
    resolved_count = sum(1 for alert in alerts if alert.get('status') == 'resolved')
    status_summary = []
    if firing_count > 0:
        status_summary.append(f"**告警中**: {firing_count}个")
    if resolved_count > 0:
        status_summary.append(f"**已恢复**: {resolved_count}个")
    
    status_text = "\n".join(status_summary) if status_summary else f"**状态**: {status}"
    
    card["elements"].append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"{status_text}\n**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    })
    
    # 添加分割线
    card["elements"].append({"tag": "hr"})
    
    # 处理分组后的每个告警类型
    for i, (alert_name, alert_group) in enumerate(grouped_alerts.items()):
        first_alert = alert_group[0]
        alert_annotations = first_alert.get('annotations', {})
        
        # 统计该组中的状态数量
        group_firing = sum(1 for a in alert_group if a.get('status') == 'firing')
        group_resolved = sum(1 for a in alert_group if a.get('status') == 'resolved')
        
        # 获取该组中的所有实例，用逗号分隔
        instance_list = [get_instance_info(a.get('labels', {})) for a in alert_group]
        instance_text = ", ".join(instance_list)
        
        # 告警基本信息
        card["elements"].append({
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**告警名称**\n{alert_name}"
                    }
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**状态**\n{'🔥 告警中' if group_firing > 0 else '✅ 已恢复'}"
                    }
                }
            ]
        })
        
        # 添加实例信息
        if len(instance_list) <= 3:
            # 实例较少时，直接显示全部
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**实例**: {instance_text}"
                }
            })
        else:
            # 实例较多时，显示数量和部分示例
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**实例**: 共{len(instance_list)}个，包括: {', '.join(instance_list[:3])}..."
                }
            })
        
        # 添加告警描述和摘要
        if 'description' in alert_annotations or 'summary' in alert_annotations:
            content = ""
            if 'summary' in alert_annotations:
                content += f"**摘要**: {alert_annotations['summary']}\n"
            if 'description' in alert_annotations:
                content += f"**描述**: {alert_annotations['description']}"
                
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content.strip()
                }
            })
        
        # 添加值信息（如果第一条告警有）
        if 'valueString' in first_alert:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**值**: {first_alert.get('valueString', '')}"
                }
            })
        
        # 添加时间范围
        earliest_start = min([a.get('startsAt', '') for a in alert_group if a.get('startsAt')])
        start_time = format_time(earliest_start) if earliest_start else ''
            
        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**开始时间**: {start_time}"
            }
        })
        
        # 添加仪表盘和面板链接
        links = []
        
        dashboard_url = first_alert.get('dashboardURL', '')
        panel_url = first_alert.get('panelURL', '')
        silence_url = first_alert.get('silenceURL', '')
        generator_url = first_alert.get('generatorURL', '')
        
        # 只添加有效的链接
        if is_valid_url(dashboard_url):
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "查看仪表盘"
                },
                "type": "primary",
                "url": dashboard_url
            })
            
        if is_valid_url(panel_url):
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "查看面板"
                },
                "type": "default",
                "url": panel_url
            })
            
        if is_valid_url(silence_url):
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "静默告警"
                },
                "type": "danger",
                "url": silence_url
            })
        
        # 如果没有常规链接但有 generatorURL，添加查看告警详情按钮
        if not links and is_valid_url(generator_url):
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "查看告警详情"
                },
                "type": "primary",
                "url": generator_url
            })
        
        if links:
            card["elements"].append({
                "tag": "action",
                "actions": links
            })
        
        # 如果不是最后一个告警类型，添加分割线
        if i < len(grouped_alerts) - 1:
            card["elements"].append({"tag": "hr"})
    
    # 添加额外的指纹信息
    if 'groupKey' in alert_data:
        card["elements"].append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"告警组: {alert_data.get('groupKey', '')}"
                }
            ]
        })
    
    return card

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5022))
    app.run(host='0.0.0.0', port=port)
