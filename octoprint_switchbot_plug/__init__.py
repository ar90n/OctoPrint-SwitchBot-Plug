# coding=utf-8
from __future__ import absolute_import, annotations
from typing import Any
from dataclasses import dataclass, asdict
import json
import time
import base64
import hmac
import hashlib

import requests
import flask
import octoprint.plugin


@dataclass(frozen=True)
class PlugPowerState:
    power: str


@dataclass(frozen=True)
class PlugStatus:
    device_id: str
    device_type: str
    hub_device_id: str
    power: str
    voltage: float
    weight: int
    electricity_of_day: int
    electric_current: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlugStatus:
        return cls(
            data["deviceId"],
            data["deviceType"],
            data["hubDeviceId"],
            data["power"],
            data["voltage"],
            data["weight"],
            data["electricityOfDay"],
            data["electricCurrent"],
        )


class SwitchBotClient:
    API_HOST: str = "https://api.switch-bot.com"

    _token: str
    _secret: str

    def __init__(self, token: str, secret: str) -> None:
        self._token = token
        self._secret = secret

    def _create_header(self) -> dict[str, str]:
        nonce = ""
        t = int(round(time.time() * 1000))
        string_to_sign = bytes(f"{self._token}{t}{nonce}", "utf-8")
        sign = base64.b64encode(
            hmac.new(
                bytes(self._secret, "utf-8"),
                msg=string_to_sign,
                digestmod=hashlib.sha256,
            ).digest()
        )
        return {
            "Authorization": self._token,
            "t": str(t),
            "sign": str(sign, "utf-8"),
            "nonce": nonce,
            "Content-Type": "application/json; charset=utf8",
        }

    def _get_request(self, url) -> dict[str, Any]:
        res = requests.get(url, headers=self._create_header())
        data = res.json()
        if data["message"] == "success":
            return res.json()
        return {}

    def _post_request(self, url, params) -> dict[str, Any]:
        res = requests.post(url, data=json.dumps(params), headers=self._create_header())
        data = res.json()
        print(data)

        if data["message"] == "success":
            return res.json()
        return {}

    def _send_command(self, device_id: str, command: str):
        device_id = device_id.upper()
        url = f"{self.API_HOST}/v1.1/devices/{device_id}/commands"
        params = {"command": command, "parameter": "default", "commandType": "command"}
        return self._post_request(url, params)

    def status(self, device_id: str) -> PlugStatus:
        device_id = device_id.upper()
        url = f"{self.API_HOST}/v1.1/devices/{device_id}/status"
        res = self._get_request(url)
        if res["statusCode"] != 100:
            raise RuntimeError(res["message"])

        return PlugStatus.from_dict(res["body"])

    def turnon(self, device_id: str) -> PlugPowerState:
        res = self._send_command(device_id, "turnOn")
        if res["statusCode"] != 100:
            raise RuntimeError(res["message"])
        status = res["body"]["items"][0]["status"]
        return PlugPowerState(status["power"])

    def turnoff(self, device_id: str) -> PlugPowerState:
        res = self._send_command(device_id, "turnOff")
        if res["statusCode"] != 100:
            raise RuntimeError(res["message"])

        status = res["body"]["items"][0]["status"]
        return PlugPowerState(status["power"])


class SwitchBotPlugPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.BlueprintPlugin,
):

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        self._logger.info("get_settings_defaults")
        return {
            "token": "",
            "secret": "",
            "device_id": "",
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        self._logger.info("get_assets")
        return {
            "js": ["js/switchbot_plug.js"],
            "css": ["css/switchbot_plug.css"],
            "less": ["less/switchbot_plug.less"],
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        self._logger.info("get_update_informations")
        return {
            "switchbot_plug": {
                "displayName": "SwitchBot Plug Plugin",
                "displayVersion": self._plugin_version,
                # version check: github repository
                "type": "github_release",
                "user": "ar90n",
                "repo": "OctoPrint-SwitchBot-Plug",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/ar90n/OctoPrint-SwitchBot-Plug/archive/{target_version}.zip",
            }
        }

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
            dict(type="sidebar", custom_bindings=False),
        ]

    @octoprint.plugin.BlueprintPlugin.route("/turnon", methods=["POST"])
    def turnon(self):
        self._logger.info("turnon")

        device_id = self._settings.get(["device_id"])
        plug_state = self._client.turnon(device_id)
        return flask.jsonify(asdict(plug_state)), 200

    @octoprint.plugin.BlueprintPlugin.route("/turnoff", methods=["POST"])
    def turnoff(self):
        self._logger.info("turnoff")

        device_id = self._settings.get(["device_id"])
        plug_state = self._client.turnoff(device_id)
        return flask.jsonify(asdict(plug_state)), 200

    @octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
    def status(self):
        self._logger.info("status")

        device_id = self._settings.get(["device_id"])
        status = self._client.status(device_id)
        return flask.jsonify(asdict(status)), 200

    @property
    def _client(self) -> SwitchBotClient:
        token = self._settings.get(["token"])
        secret = self._settings.get(["secret"])
        return SwitchBotClient(token, secret)


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "SwitchBot Plug Plugin"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = SwitchBotPlugPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
