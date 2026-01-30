from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent

def create_stock_report(stocks):
    """
    Creates a Flex Message bubble for the weekly stock report.
    """
    if not stocks:
        return None

    # Sort stocks by meeting date
    stocks.sort(key=lambda x: x.meeting_date)

    contents = []
    
    # Header
    contents.append(TextComponent(text="📅 股東會紀念品速報", weight="bold", size="xl", color="#1DB446"))
    contents.append(TextComponent(text="本週最新資訊", size="xs", color="#aaaaaa", margin="md"))
    
    # Separator
    contents.append(BoxComponent(layout="vertical", margin="lg", spacing="sm", contents=[])) # Spacer

    # Stock List
    for stock in stocks:
        row = BoxComponent(
            layout="vertical",
            margin="md",
            contents=[
                TextComponent(text=f"{stock.stock_id} {stock.name}", weight="bold", size="md"),
                TextComponent(text=f"🎁 {stock.gift_name}", size="sm", color="#555555", wrap=True),
                TextComponent(text=f"🛒 最後買進: {stock.last_buy_date}", size="xs", color="#999999")
            ]
        )
        contents.append(row)

    bubble = BubbleContainer(
        body=BoxComponent(
            layout="vertical",
            contents=contents
        )
    )

    return FlexSendMessage(alt_text="本週股東會紀念品通知", contents=bubble)
