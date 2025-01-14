import logging as log
import argparse

import requests
import json
import base64

from time import sleep
from datetime import datetime

log_levels = {
    "DEBUG": log.DEBUG,
    "INFO": log.INFO,
    "WARNING": log.WARNING,
    "ERROR": log.ERROR,
    "CRITICAL": log.CRITICAL
}

# Converts Nextcloud's notification buttons to ntfy.sh notification actions
def parse_actions(actions: list) -> list:
    parsed_actions = []

    for action in actions:
        action_parsed = {
            "action": "http",
            "label": f"{action['label']}",
            "url": f"{action['link']}",
            "method": f"{action['type']}",
            "clear": True
        }

        # The `action['type']` is documented to be a HTTP request.
        # But a value of `WEB` is also used
        # which is used for opening links in the browser.
        if action_parsed["method"] == "WEB":
            del action_parsed["method"]
            action_parsed["action"] = "view"

        parsed_actions.append(action_parsed)

    return parsed_actions

def push_to_ntfy(url: str, token: str, topic: str, title: str, click = "", message = "", actions = []) -> requests.Response:
    jsonData = {
        "topic": f"{topic}",
        "title": f"{title}",
        "message": f"{message}",
        "click": f"{click}",
        "actions": actions
    }

    response = requests.post(url, 
        data=json.dumps(jsonData),
        headers={
            "Authorization": f"Bearer {token}"
        })

    return response

# Nextcloud apps have quite often internal names differing from the UI names.
#  - Eg. `spreed` is `Talk`
# This is the place to track the differences
def translate_app_name(app = str):
    if app == "spreed":
        return "Talk"
    elif app == "event_update_notification":
        return "Calendar"
    else:
        return app

def arg_parser():
    parser = argparse.ArgumentParser(description ='Nextcloud to ntfy.sh notification bridge.')

    parser.add_argument(
        "--log_level", 
        type=str, 
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)"
    )
    parser.add_argument(
        "-c",
        "--config-file", 
        type=str, 
        default="./config.json", 
        required=True,
        help="Path to the configuration file"
    )

    return parser.parse_args()

def load_config(config_file: str) -> dict:
    # Default values for the configuration
    default_config = {
        "ntfy_base_url": "https://ntfy.example.com",
        "ntfy_topic": "nextcloud",
        "ntfy_token": "default_token",
        
        "nextcloud_base_url": "https://nextcloud.example.com",
        "nextcloud_notification_path": "/ocs/v2.php/apps/notifications/api/v1/notifications",
        
        "nextcloud_username": "user",
        "nextcloud_password": "application_password",
        
        "nextcloud_poll_interval_seconds": 10,
        "nextcloud_error_sleep_seconds": 300,
        "nextcloud_204_sleep_seconds": 3600,
        
        "rate_limit_sleep_seconds": 600
    }

    try:
        # Attempt to load the JSON config file
        with open(config_file, "r") as file:
            config_data = json.load(file)
        
        # Check and fill missing values with defaults
        for key, value in default_config.items():
            if key not in config_data:
                config_data[key] = value
        
        return config_data

    except FileNotFoundError:
        print(f"Configuration file {config_file} not found. Using default values.")
        return default_config

    except json.JSONDecodeError:
        print(f"Error decoding JSON from {config_file}. Using default values.")
        return default_config

def main():
    args = arg_parser()
    config = load_config(args.config_file)

    log.basicConfig(
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%d-%m-%Y %H:%M:%S",
        level=log_levels[args.log_level]
    )
    log.info("Started Nextcloud to ntfy.sh notification bridge.")

    last_datetime = datetime.fromisoformat("1970-01-01T00:00:00Z")
    nextcloud_auth_header = f"Basic {base64.b64encode(f"{config["nextcloud_username"]}:{config["nextcloud_password"]}".encode("utf-8")).decode("utf-8")}"
    nextcloud_request_headers = {
        "Authorization": f"{nextcloud_auth_header}",
        "OCS-APIREQUEST": "true",
        "Accept": "application/json"
    }
    while True:
        log.debug("Fetching notifications.")
        response = requests.get(f"{config["nextcloud_base_url"]}{config["nextcloud_notification_path"]}", headers = nextcloud_request_headers)
        if not response.ok:
            log.error(f"Error while fetching notifications. Response code: {response.status_code}.")
            log.warning(f"Sleeping for {config["nextcloud_error_sleep_seconds"]} seconds.")
            sleep(config["nextcloud_error_sleep_seconds"])
            continue

        elif response.status_code == 204:
            log.debug(f"Got code 204 while fetching notifications. Sleeping for {config["nextcloud_204_sleep_seconds"]/60/60} hour(s).")

        log.debug(f"Got resonse code: {response.status_code}")

        log.debug(f"Received data:\n{response.text}")
        data = json.loads(response.text)

        for notification in reversed(data["ocs"]["data"]):

            if datetime.fromisoformat(notification["datetime"]) <= last_datetime:
                log.debug("No new notifications.")
                continue
            last_datetime = datetime.fromisoformat(notification["datetime"])
            log.info("New notifications received.")

            title = ""
            if notification["app"] == "admin_notifications":
                title = f"Nextcloud: {notification["subject"]}"
            else:
                title = f"Nextcloud - {translate_app_name(notification["app"])}: {notification["subject"]}"
            log.debug(f"Notification title: {title}")

            message = notification["message"]
            log.debug(f"Notification message:\n{message}")

            actions = parse_actions(notification["actions"])
            actions.append({
                "action": "http",
                "label": "Dismiss",
                "url": f"{config["nextcloud_base_url"]}{config["nextcloud_notification_path"]}/{notification["notification_id"]}",
                "method": "DELETE",
                "headers": {
                    "Authorization": f"{nextcloud_auth_header}",
                    "OCS-APIREQUEST": "true"
                },
                "clear": True
            })
            log.debug(f"Notification actions:\n{actions}")
            
            log.info(f"Pushing notification to ntfy.")

            response = push_to_ntfy(config["ntfy_base_url"], config["ntfy_token"], config["ntfy_topic"], title, notification["link"], message, actions)
            if response.status_code == 429:
                log.error(f"Error pushing notification to {config["ntfy_base_url"]}: Too Many Requests.")
                log.warning(f"Sleeping for {config["rate_limit_sleep_seconds"]} seconds.")
            elif not response.ok:
                log.critical(f"Unknown erroro while pushing notification to {config["ntfy_base_url"]}. Error code: {response.status_code}.")
                log.critical(f"Response: {response.text}")
                log.error("Stopping.")
                exit(1)

        sleep(config["nextcloud_poll_interval_seconds"])

if __name__ == "__main__":
  main()
