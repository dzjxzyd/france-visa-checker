#!/usr/bin/env python3
import subprocess
import time
import os
import re
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ============ 邮件配置 ============
SENDER_EMAIL = "your@gmail.com"
RECEIVER_EMAIL = "your@gmail.com"
APP_PASSWORD = "yourpassword"


# ============ 结论中"无 slot"的关键词（中/英/法） ============
NO_SLOT_KEYWORDS = [
    # 中文
    "暂无",
    "无可用",
    "没有可用",
    "未发现可用",
    "无预约",
    "没有预约",
    "无空位",
    "没有空位",
    "无法预约",
    "不可预约",
    "未找到可用",
    "全部禁用",
    "均不可用",
    "都不可用",
    "没有可以预约",
    "仅今天",           # 仅今天可选 = 无真正 slot
    "只有今天",          # 只有今天可选
    "仅当天",           # 仅当天可选
    "只有当天",          # 只有当天可选
    # 法语
    "aucune réservation disponible",
    "aucun créneau disponible",
    "aucune disponibilité",
    "indisponible",
    # 英语
    "no slot",
    "no available",
    "not available",
    "no availability",
    "no appointment",
    "no reservation",
    "all disabled",
    "only today",
]


# ============ "仅今天可选"误报检测模式 ============
# 网站总是让"今天"可选（不 disabled），但实际无 slot
# 匹配类似："仅今天（3月10日）可选，但无可用预约" 或 "只有今天可选"
ONLY_TODAY_PATTERNS = [
    r"仅.{0,6}今天.{0,10}可选",
    r"只有.{0,6}今天.{0,10}可选",
    r"仅.{0,6}当天.{0,10}可选",
    r"只有.{0,6}当天.{0,10}可选",
    r"today.{0,15}(only|sole|selectable)",
    r"(only|sole).{0,15}today.{0,15}selectable",
    r"可选日期.{0,6}(仅|只有).{0,6}今天",
    r"可选日期.{0,6}(仅|只有).{0,6}当天",
    # 匹配 "其他日期：全部被禁用" + "可选日期：仅...今天" 组合
    r"其他日期.{0,6}(全部|均|都).{0,6}禁用",
]


# ============ 工作目录（用于解析相对路径的图片） ============
WORK_DIR = "/Users/zhenjiao-ucd/Downloads/france"


def extract_image_paths(output):
    """从 LLM 输出中提取图片文件路径（.png / .jpg / .jpeg）"""
    # 匹配类似 xxx.png, /path/to/xxx.png, `xxx.png` 等
    pattern = r'[`"\s:/]([\w./-]*\w+\.(?:png|jpg|jpeg))'
    matches = re.findall(pattern, output, re.IGNORECASE)

    image_paths = []
    for match in matches:
        # 转为绝对路径
        if os.path.isabs(match):
            full_path = match
        else:
            full_path = os.path.join(WORK_DIR, match)

        if os.path.exists(full_path) and full_path not in image_paths:
            image_paths.append(full_path)
            print(f"  📎 找到图片: {full_path}")

    return image_paths


def send_email(subject, body, image_paths=None):
    """发送邮件通知，可附带图片附件"""
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # 添加图片附件
    for path in (image_paths or []):
        try:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
            print(f"  📎 已附加图片: {filename}")
        except Exception as e:
            print(f"  ⚠️ 无法附加图片 {path}: {e}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("✅ 邮件发送成功！")
    except smtplib.SMTPAuthenticationError:
        print("❌ 认证失败！请检查 App Password 是否正确。")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")


def is_only_today_selectable(output):
    """
    检测 LLM 输出中是否包含"仅今天可选"的模式。
    网站总是让今天的日期可选（不 disabled），但这不代表有真正的 slot。
    如果输出描述了"仅今天可选"或"其他日期全部禁用"，则认为无可用 slot。
    """
    text = output.lower()
    for pattern in ONLY_TODAY_PATTERNS:
        if re.search(pattern, text):
            print(f"  🔍 检测到'仅今天可选'模式: \"{pattern}\"")
            return True
    return False


def has_available_slot(output):
    """
    判断 LLM 输出中是否有可用 slot。
    提取"结论"或"结果"部分来判断，避免被中间描述误导。
    支持结论在同一行或下一行的情况。

    新增：检测"仅今天可选"模式——网站总是让今天可选但实际无 slot。
    """
    # === 第一步：检测"仅今天可选"误报（全文检测） ===
    if is_only_today_selectable(output):
        print("  ℹ️  判定为'仅今天可选'误报，视为无可用 slot")
        return False

    lines = output.split("\n")
    conclusion_text = ""

    # 提取"结论"和"结果"相关行及其后续内容
    for i, line in enumerate(lines):
        if "结论" in line or "结果" in line:
            # 收集当前行 + 后续内容（跳过空行，直到遇到分隔符或新段落）
            conclusion_text += line + " "
            collected = 0
            for j in range(i + 1, min(i + 15, len(lines))):
                stripped = lines[j].strip()
                if stripped.startswith("截图") or stripped.startswith("---"):
                    break
                if stripped == "":
                    continue  # 跳过空行，不停止收集
                conclusion_text += lines[j] + " "
                collected += 1
                if collected >= 8:
                    break

    if conclusion_text.strip():
        print(f"  📋 提取到结论/结果: {conclusion_text.strip()}")
        check_text = conclusion_text.lower()
    else:
        print("  ⚠️ 未找到结论/结果行，使用全文检测")
        check_text = output.lower()

    for keyword in NO_SLOT_KEYWORDS:
        if keyword in check_text:
            print(f"  ℹ️  匹配到无 slot 关键词: \"{keyword}\"")
            return False

    return True


def run_opencode():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"\n[{timestamp}] Running opencode...")

    try:
        cmd = [
            "opencode",
            "run",
            "--model",
            "zai-coding-plan/glm-5",
            "运行 check-visa-slot.md",
        ]
        print(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10 * 60)
        print(result.stdout)
        if result.returncode == 0:
            print(f"[{timestamp}] Success")
            # 智能检测是否有可用 slot
            if has_available_slot(result.stdout):
                print(f"[{timestamp}] 🎉 未检测到'无可用'关键词，可能有 slot！正在发送邮件通知...")
                images = extract_image_paths(result.stdout)
                send_email(
                    subject=f"🇫🇷 签证 Slot 提醒 - {timestamp}",
                    body=f"可能检测到可用的签证 slot！\n\n以下是完整结果：\n\n{result.stdout}",
                    image_paths=images,
                )
            else:
                print(f"[{timestamp}] 😔 当前无可用 slot，不发送邮件。")
        else:
            print(f"[{timestamp}] Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print(f"[{timestamp}] Timeout")
    except Exception as e:
        print(f"[{timestamp}] Exception: {e}")


def main():
    print(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Will run every 5 minutes for 1 hour (12 iterations)")

    for i in range(12):
        run_opencode()

        if i < 11:
            print(f"\nWaiting 5 minutes before next run... (Iteration {i + 1}/12)")
            time.sleep(300)

    print(f"\nCompleted at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
