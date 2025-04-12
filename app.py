import json
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify

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

def create_feishu_card(status, title, alerts, alert_data):
    """创建飞书卡片"""
    status_color = ALERT_COLORS.get(status.lower(), "grey")
    
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
    card["elements"].append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**状态**: {status}\n**告警时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    })
    
    # 添加分割线
    card["elements"].append({"tag": "hr"})
    
    # 处理每个告警
    for i, alert in enumerate(alerts):
        alert_status = alert.get('status', '未知')
        alert_labels = alert.get('labels', {})
        alert_annotations = alert.get('annotations', {})
        
        # 告警基本信息
        card["elements"].append({
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**告警名称**\n{alert_labels.get('alertname', '未知')}"
                    }
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**实例**\n{alert_labels.get('instance', '未知')}"
                    }
                }
            ]
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
        
        # 添加时间范围
        start_time = format_time(alert.get('startsAt', ''))
        end_time = alert.get('endsAt', '')
        if end_time and end_time != "0001-01-01T00:00:00Z":
            end_time = format_time(end_time)
            time_range = f"**开始时间**: {start_time}\n**结束时间**: {end_time}"
        else:
            time_range = f"**开始时间**: {start_time}"
            
        card["elements"].append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": time_range
            }
        })
        
        # 添加仪表盘和面板链接
        links = []
        
        if 'dashboardURL' in alert:
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "查看仪表盘"
                },
                "type": "primary",
                "url": alert.get('dashboardURL', '')
            })
            
        if 'panelURL' in alert:
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "查看面板"
                },
                "type": "default",
                "url": alert.get('panelURL', '')
            })
            
        if 'silenceURL' in alert:
            links.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "静默告警"
                },
                "type": "danger",
                "url": alert.get('silenceURL', '')
            })
        
        if links:
            card["elements"].append({
                "tag": "action",
                "actions": links
            })
        
        # 如果不是最后一个告警，添加分割线
        if i < len(alerts) - 1:
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
