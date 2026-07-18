import os
import sys
from datetime import datetime
from application.channels.telegram_channel import TelegramChannel
from application.alert_builder import AlertMessage

def main():
    # Read environment variables
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    # Validate environment variables
    if not bot_token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables are not set.")
        sys.exit(1)

    # Create a proper AlertMessage instance
    alert = AlertMessage(
        alert_id="test_alert",
        symbol="TEST",
        market=None,
        recommendation="TEST",
        final_score=1.0,
        confidence_level=1.0,
        risk_level=None,
        summary="Test integration message",
        created_at=datetime.now(),
        formatted_message="ALCHEMIK — test integracyjny Telegrama\nPołączenie działa poprawnie.\nTo jest kontrolowana wiadomość testowa.\nAutomatyczne alerty 24/7 nie są jeszcze uruchomione."
    )

    # Create TelegramChannel and send the message
    try:
        channel = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
        result = channel.send(alert)

        if result.success:
            print(f"Telegram integration OK\nmessage_id: {result.message_id}")
        else:
            print(f"Error: {result.error_message or 'Unknown error'}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
