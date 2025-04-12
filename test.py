#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import argparse
from pprint import pprint

# 示例Grafana告警JSON
SAMPLE_ALERT = {
    "receiver": "test",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "TestAlert",
                "instance": "Grafana"
            },
            "annotations": {
                "description": "这是一条测试告警描述",
                "summary": "这是一条测试告警摘要"
            },
            "startsAt": "2025-04-12T17:01:57.158364661Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "",
            "fingerprint": "57c6d9296de2ad39",
            "silenceURL": "https://grafana.chatglm.site/alerting/silence/new?alertmanager=grafana&matcher=alertname%3DTestAlert&matcher=instance%3DGrafana",
            "dashboardURL": "https://grafana.chatglm.site/d/artifacts-proxy",
            "panelURL": "https://grafana.chatglm.site/d/artifacts-proxy?viewPanel=2",
            "values": None,
            "valueString": "[ metric='foo' labels={instance=bar} value=10 ]"
        }
    ],
    "groupLabels": {
        "alertname": "TestAlert",
        "instance": "Grafana"
    },
    "commonLabels": {
        "alertname": "TestAlert",
        "instance": "Grafana"
    },
    "commonAnnotations": {
        "description": "这是一条测试告警描述",
        "summary": "这是一条测试告警摘要"
    },
    "externalURL": "https://grafana.chatglm.site/",
    "version": "1",
    "groupKey": "test-57c6d9296de2ad39-1744477317",
    "truncatedAlerts": 0,
    "orgId": 1,
    "title": "[FIRING:1] TestAlert Grafana ",
    "state": "alerting",
    "message": "**Firing**\n\nValue: [no value]\nLabels:\n - alertname = TestAlert\n - instance = Grafana\nAnnotations:\n - description = 这是一条测试告警描述\n - summary = 这是一条测试告警摘要\nSilence: https://grafana.chatglm.site/alerting/silence/new?alertmanager=grafana&matcher=alertname%3DTestAlert&matcher=instance%3DGrafana\nDashboard: https://grafana.chatglm.site/d/artifacts-proxy\nPanel: https://grafana.chatglm.site/d/artifacts-proxy?viewPanel=2\n"
}

# 测试已解决的告警
RESOLVED_ALERT = {
    "receiver": "test",
    "status": "resolved",
    "alerts": [
        {
            "status": "resolved",
            "labels": {
                "alertname": "TestAlert",
                "instance": "Grafana"
            },
            "annotations": {
                "description": "这是一条已解决的告警描述",
                "summary": "这是一条已解决的告警摘要"
            },
            "startsAt": "2025-04-12T17:01:57.158364661Z",
            "endsAt": "2025-04-12T17:10:57.158364661Z",
            "generatorURL": "",
            "fingerprint": "57c6d9296de2ad39",
            "silenceURL": "https://grafana.chatglm.site/alerting/silence/new?alertmanager=grafana&matcher=alertname%3DTestAlert&matcher=instance%3DGrafana",
            "dashboardURL": "https://grafana.chatglm.site/d/artifacts-proxy",
            "panelURL": "https://grafana.chatglm.site/d/artifacts-proxy?viewPanel=2",
            "values": None,
            "valueString": "[ metric='foo' labels={instance=bar} value=10 ]"
        }
    ],
    "groupLabels": {
        "alertname": "TestAlert",
        "instance": "Grafana"
    },
    "commonLabels": {
        "alertname": "TestAlert",
        "instance": "Grafana"
    },
    "commonAnnotations": {
        "description": "这是一条已解决的告警描述",
        "summary": "这是一条已解决的告警摘要"
    },
    "externalURL": "https://grafana.chatglm.site/",
    "version": "1",
    "groupKey": "test-57c6d9296de2ad39-1744477317",
    "truncatedAlerts": 0,
    "orgId": 1,
    "title": "[RESOLVED] TestAlert Grafana ",
    "state": "resolved",
    "message": "**Resolved**\n\nValue: [no value]\nLabels:\n - alertname = TestAlert\n - instance = Grafana\nAnnotations:\n - description = 这是一条已解决的告警描述\n - summary = 这是一条已解决的告警摘要\nSilence: https://grafana.chatglm.site/alerting/silence/new?alertmanager=grafana&matcher=alertname%3DTestAlert&matcher=instance%3DGrafana\nDashboard: https://grafana.chatglm.site/d/artifacts-proxy\nPanel: https://grafana.chatglm.site/d/artifacts-proxy?viewPanel=2\n"
}

# 多告警示例
MULTI_ALERTS = {
    "receiver": "test",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "高CPU使用率",
                "instance": "server1.example.com"
            },
            "annotations": {
                "description": "服务器CPU使用率超过90%已持续5分钟",
                "summary": "服务器CPU告警"
            },
            "startsAt": "2025-04-12T17:01:57.158364661Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "dashboardURL": "https://grafana.chatglm.site/d/server-metrics",
            "panelURL": "https://grafana.chatglm.site/d/server-metrics?viewPanel=1"
        },
        {
            "status": "firing",
            "labels": {
                "alertname": "内存不足",
                "instance": "server1.example.com"
            },
            "annotations": {
                "description": "服务器内存使用率超过95%",
                "summary": "服务器内存告警"
            },
            "startsAt": "2025-04-12T17:05:57.158364661Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "dashboardURL": "https://grafana.chatglm.site/d/server-metrics",
            "panelURL": "https://grafana.chatglm.site/d/server-metrics?viewPanel=2"
        }
    ],
    "groupLabels": {
        "instance": "server1.example.com"
    },
    "commonLabels": {
        "instance": "server1.example.com"
    },
    "externalURL": "https://grafana.chatglm.site/",
    "version": "1",
    "groupKey": "instance-server1-1744477317",
    "truncatedAlerts": 0,
    "orgId": 1,
    "title": "[FIRING:2] 服务器告警 server1.example.com",
    "state": "alerting"
}

def send_test_alert(url, alert_type='firing'):
    """发送测试告警到指定URL"""
    
    if alert_type == 'firing':
        data = SAMPLE_ALERT
    elif alert_type == 'resolved':
        data = RESOLVED_ALERT
    elif alert_type == 'multi':
        data = MULTI_ALERTS
    else:
        raise ValueError(f"不支持的告警类型: {alert_type}")
    
    headers = {'Content-Type': 'application/json'}
    
    print(f"发送 {alert_type} 类型的告警到 {url}")
    response = requests.post(url, headers=headers, json=data)
    
    print(f"状态码: {response.status_code}")
    try:
        print("响应:")
        pprint(response.json())
    except:
        print(f"响应内容: {response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='测试Grafana告警到飞书的转换服务')
    parser.add_argument('--url', default='http://localhost:5022/webhook',
                        help='webhook服务的URL (默认: http://localhost:5022/webhook)')
    parser.add_argument('--type', choices=['firing', 'resolved', 'multi'],
                        default='firing',
                        help='告警类型: firing(触发中), resolved(已解决), multi(多告警) (默认: firing)')
    
    args = parser.parse_args()
    
    send_test_alert(args.url, args.type) 