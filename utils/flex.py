from linebot.models import FlexSendMessage, BubbleContainer, BoxComponent, TextComponent

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

def create_stock_reports(stocks):
    """
    Creates a list of Flex Messages, 5 stocks per message.
    """
    if not stocks:
        return []

    # Sort stocks by meeting date
    stocks.sort(key=lambda x: x.meeting_date)

    messages = []
    chunk_size = 5
    total_pages = (len(stocks) - 1) // chunk_size + 1
    
    for i in range(0, len(stocks), chunk_size):
        chunk = stocks[i:i+chunk_size]
        bubble = _create_single_bubble(chunk, page=i//chunk_size + 1, total_pages=total_pages)
        messages.append(FlexSendMessage(alt_text=f"股東會紀念品速報 ({i//chunk_size + 1}/{total_pages})", contents=bubble))

    return messages
