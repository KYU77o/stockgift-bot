from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, CarouselContainer

def _create_single_bubble(stocks_chunk, page=1, total_pages=1):
    contents = []
    
    # Header
    title_text = "📅 股東會紀念品速報"
    if total_pages > 1:
        title_text += f" ({page}/{total_pages})"
        
    contents.append(TextComponent(text=title_text, weight="bold", size="xl", color="#1DB446"))
    contents.append(TextComponent(text="本週最新資訊", size="xs", color="#aaaaaa", margin="md"))
    
    # Separator
    contents.append(BoxComponent(layout="vertical", margin="lg", spacing="sm", contents=[])) # Spacer

    # Stock List
    for stock in stocks_chunk:
        buy_date_str = stock.last_buy_date.strftime("%m/%d") if stock.last_buy_date else "未定"
        meet_date_str = stock.meeting_date.strftime("%m/%d") if stock.meeting_date else "未定"
        
        row = BoxComponent(
            layout="vertical",
            margin="md",
            contents=[
                TextComponent(text=f"{stock.stock_id} {stock.name}", weight="bold", size="md"),
                TextComponent(text=f"🎁 {stock.gift_name}", size="sm", color="#555555", wrap=True),
                TextComponent(text=f"📅 股東會: {meet_date_str} | 🛒 最後買進: {buy_date_str}", size="xs", color="#999999")
            ]
        )
        contents.append(row)

    return BubbleContainer(
        body=BoxComponent(
            layout="vertical",
            contents=contents
        )
    )

def create_stock_report(stocks):
    """
    Creates a Flex Message bubble or carousel for the weekly stock report.
    """
    if not stocks:
        return None

    # Sort stocks by meeting date
    stocks.sort(key=lambda x: x.meeting_date)

    if len(stocks) > 10:
        bubbles = []
        total_pages = (len(stocks) - 1) // 10 + 1
        for i in range(0, len(stocks), 10):
            chunk = stocks[i:i+10]
            bubbles.append(_create_single_bubble(chunk, page=i//10 + 1, total_pages=total_pages))
        container = CarouselContainer(contents=bubbles)
    else:
        container = _create_single_bubble(stocks)

    return FlexSendMessage(alt_text="本週股東會紀念品通知", contents=container)
