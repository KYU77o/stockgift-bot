import logging
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, UnfollowEvent
)
from config import Config
from models import db, User
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Setup Logging to Stdout (Critical for Render)
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Initialize LINE Bot API
line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])

@app.route("/health", methods=['GET'])
def health():
    return "OK", 200

@app.route("/debug-log")
def debug_log():
    app.logger.warning("這是一條測試 LOG。如果您看到這行，代表 Log 系統正常。")
    print("這是一條 Print 測試。")
    return "Log test sent. Check your specific logs now."

@app.route("/webhook", methods=['POST'])
def webhook():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body = request.get_data(as_text=True)
    # app.logger.info("Request body: " + body) # Commented out to reduce noise, we have specific logs now

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    line_user_id = event.source.user_id
    
    # Explicit Log for User to find their ID (WARN level to ensure visibility)
    app.logger.warning(f"\n==========\n【您的 USER ID】: {line_user_id}\n==========\n")
    
    # Upsert User
    user = User.query.filter_by(line_user_id=line_user_id).first()
    if user:
        user.is_active = True
    else:
        user = User(line_user_id=line_user_id, is_active=True)
        db.session.add(user)
    
    db.session.commit()
    
    welcome_msg = (
        "歡迎加入股東會紀念品戰情室！🎉\n"
        "我們將於每週一早上 08:30 通知本週消息。\n"
        "如果本週沒有新增任何消息則不會發送，以免打擾您。"
    )
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_msg)
    )

@handler.add(UnfollowEvent)
def handle_unfollow(event):
    line_user_id = event.source.user_id
    user = User.query.filter_by(line_user_id=line_user_id).first()
    if user:
        user.is_active = False
        db.session.commit()

@handler.add(MessageEvent)
def handle_message(event):
    # System Identity: Not a chatbot, but we use this chance to ensure user is in DB.
    line_user_id = event.source.user_id
    
    # Explicit Log here too (WARN level)
    app.logger.warning(f"\n==========\n【您的 USER ID】: {line_user_id}\n==========\n")

    # Check if user exists, if not add them (Self-healing for existing followers)
    user = User.query.filter_by(line_user_id=line_user_id).first()
    if not user:
        user = User(line_user_id=line_user_id, is_active=True)
        db.session.add(user)
        db.session.commit()
        app.logger.info(f"Auto-registered existing user: {line_user_id}")
    elif not user.is_active:
        user.is_active = True
        db.session.commit()

    return

# Initialize Scheduler
scheduler = None
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    # Avoid double run in debug mode reloader
    from services.scheduler import SchedulerService
    scheduler = SchedulerService(app)
    scheduler.start()

# --- 超級修復版秘密通道 ---
from services.scheduler import SchedulerService
from models import db  # 記得引入 db 來建立表格
import traceback

@app.route('/secret-trigger')
def manual_trigger():
    try:
        # 0. 確保資料庫表格存在 (這步最關鍵！)
        with app.app_context():
            db.create_all()
            print("資料庫表格檢查/建立完成。")

        # 0.5 Special Debug: Force Add Test User
        if request.args.get('add_test_user') == 'true':
            test_uid = "U_TEST_USER_12345"
            existing = User.query.filter_by(line_user_id=test_uid).first()
            if not existing:
                u = User(line_user_id=test_uid, is_active=True)
                db.session.add(u)
                db.session.commit()
                print(f"Debug: Added test user {test_uid}")

        # Get Target User ID (Safety Lock)
        target_user_id = request.args.get('user_id')

        # 1. 建立服務
        service = SchedulerService(app)
        
        # 2. 強制執行爬蟲
        print("手動觸發：開始爬蟲...")
        service.scrape_job()
        
        # 3. 強制執行廣播 (Absolute Safety Lock)
        msg_broadcast = ""
        if target_user_id:
            print(f"手動觸發：開始安全廣播... (Target: {target_user_id})")
            service.broadcast_job(is_test=True, target_user_id=target_user_id)
            msg_broadcast = f"✅ 安全廣播成功 (Target: {target_user_id})"
        else:
            print("手動觸發：未指定 user_id，跳過廣播。")
            msg_broadcast = "🔒 安全鎖啟動：未指定 user_id，已跳過廣播 (僅更新資料庫)。"

        from models import Stock, User
        stock_count = Stock.query.count()
        user_count = User.query.count()

        msg = f"執行完成！<br>資料庫股票數量: {stock_count}<br>總訂閱用戶數量: {user_count}<br><br>{msg_broadcast}"

        return msg
        
    except Exception as e:
        # 如果失敗，直接把錯誤原因印在網頁上，不用去翻 Log
        error_msg = f"執行失敗：{str(e)}\n\n詳細錯誤：\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg.replace('\n', '<br>'), 500
# ----------------------------------------

if __name__ == "__main__":
    app.run()
