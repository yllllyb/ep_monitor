import time, requests, logging


def send_message(group, message: str, push=True):
    message = message.strip().strip("\n")

    if not push:
        with open("log.txt", "a", encoding="utf-8") as f:
            f.write(message + "\n")
        return

    payload = {"msg_type": "text", "content": {"text": message}}
    response = None
    for _ in range(3):
        try:
            resp = requests.post(group, json=payload)
            if resp.status_code != 200:
                logging.warning(f"Failed to send message to webhook. Status code: {resp.status_code}")
                time.sleep(3)
                continue
            response = resp
            break
        except requests.exceptions.RequestException as e:
            logging.error("Error sending message to webhook. Retrying...", exc_info=True)
            time.sleep(3)
    if response is None:
        logging.error("Failed to send message to lark after 3 retries")
        return
