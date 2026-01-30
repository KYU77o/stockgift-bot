from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FollowEvent, UnfollowEvent
)
from config import Config
from models import db, User

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Initialize LINE Bot API
line_bot_api = LineBotApi(app.config['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(app.config['LINE_CHANNEL_SECRET'])

@app.route("/health", methods=['GET'])
def health():
    return "OK", 200

@app.route("/webhook", methods=['POST'])
def webhook():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

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
    # System Identity: Not a chatbot. Return 200 OK immediately.
    return

# Initialize Scheduler
# Note: In production with multiple workers, this might run multiple times.
# For Render free tier/standard with 1 worker, this is acceptable.
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

        # 1. 建立服務
        service = SchedulerService(app)
        
        # 2. 強制執行爬蟲
        print("手動觸發：開始爬蟲...")
        service.scrape_job()
        
        # Check DB count after scrape
        from models import Stock, User
        stock_count = Stock.query.count()
        user_count = User.query.count()
        
        # 3. 強制執行廣播 (Test Mode: Force Send)
        print(f"手動觸發：開始廣播... (DB Stock Count: {stock_count})")
        service.broadcast_job(is_test=True)
        
        return f"測試成功！<br>資料庫股票數量: {stock_count}<br>訂閱用戶數量: {user_count}<br>請檢查 LINE 訊息！"
        
    except Exception as e:
        # 如果失敗，直接把錯誤原因印在網頁上，不用去翻 Log
        error_msg = f"執行失敗：{str(e)}\n\n詳細錯誤：\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg.replace('\n', '<br>'), 500
# ----------------------------------------

if __name__ == "__main__":
    app.run()
