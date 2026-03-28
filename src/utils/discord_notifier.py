import requests
import json
import logging

logger = logging.getLogger(__name__)

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, content: str = None, embeds: list = None):
        """
        Send a message to Discord.
        content: The message text.
        embeds: List of embed dictionaries.
        """
        if not self.webhook_url:
            logger.warning("Discord Webhook URL not configured.")
            return False

        payload = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds

        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False

    def send_digest_post(self, post_number: int, text: str, images: list):
        """
        Specialized method for weekly digest posts with copy-paste formatting.
        """
        # Format text in a code block for easy one-tap copy on mobile
        formatted_text = f"**[Weekly Digest Post #{post_number}]**\n```\n{text}\n```"
        
        embeds = []
        if images:
            # Discord only allows one image per embed in a basic way, 
            # but we can send multiple embeds or just list them.
            # For simplicity, we'll put the first image in the main embed 
            # and list others or create a carousel-like effect with multiple embeds.
            for i, img_url in enumerate(images[:10]): # Discord limit is 10 embeds per message
                embeds.append({
                    "url": "https://threads.net", # Placeholder
                    "image": {"url": img_url}
                })

        return self.send_message(content=formatted_text, embeds=embeds)

    def send_standard_post(self, title: str, text: str, images: list = None):
        """
        Unified method for sending formatted posts to Discord.
        """
        # Format text in a code block for easy copy-pasting
        formatted_text = f"**[{title}]**\n```\n{text}\n```"
        
        embeds = []
        if images:
            # Discord limit is 10 embeds per message
            for img_url in images[:10]:
                if img_url and str(img_url).startswith('http'):
                    # Clean StreetVoice resizing for highest available quality
                    clean_url = str(img_url).split('?x-oss-process=')[0]
                    embeds.append({
                        "image": {"url": clean_url}
                    })

        return self.send_message(content=formatted_text, embeds=embeds)

    def send_file(self, file_path: str, content: str = None):
        """
        Upload a file to Discord.
        """
        import os
        if not self.webhook_url:
            logger.warning("Discord Webhook URL not configured.")
            return False

        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False

        payload = {}
        if content:
            payload["payload_json"] = json.dumps({"content": content})

        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(file_path), f)
                }
                response = requests.post(
                    self.webhook_url,
                    data=payload,
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to upload file to Discord: {e}")
            return False
