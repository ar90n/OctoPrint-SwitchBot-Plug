/*
 * View model for OctoPrint-SwitchBot-Plug
 *
 * Author: Masahiro Wada
 * License: AGPLv3
 */

(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(window.OctoPrintClient);
    }
})(window || this, function(OctoPrintClient) {
    var SwitchBotPlug = function(base) {
        this.base = base;
        this.baseUrl = OctoPrint.getBlueprintUrl("switchbot_plug");
    };

    SwitchBotPlug.prototype.turnon = function() {
        const url = `${this.baseUrl}/turnon`;
        return OctoPrint.post(url, {}, {contentType: "application/json"});
    };

    SwitchBotPlug.prototype.turnoff = function() {
        const url = `${this.baseUrl}/turnoff`;
        return OctoPrint.post(url, {}, {contentType: "application/json"});
    };

    SwitchBotPlug.prototype.status = function() {
        const url = `${this.baseUrl}/status`;
        return OctoPrint.get(url)
    };

    OctoPrintClient.registerPluginComponent("switchbot_plug", SwitchBotPlug);
    return SwitchBotPlug;
});

$(function() {
    function SwitchBotPlugViewModel(parameters) {
        var self = this;

        self.power = ko.observable("off");
        self.buttonLabel = ko.pureComputed(function() {
            return self.power() === "on" ? "Turn Off" : "Turn On";
        });

        self.turnOn = function(data) {
            OctoPrint.plugins.switchbot_plug.turnon().then(r => {
                self.power(r.power)
            })
        }

        self.turnOff = function(data) {
            OctoPrint.plugins.switchbot_plug.turnoff().then(r => {
                self.power(r.power)
            })
        }

        self.toggle = function(data) {
            if (self.power() == "on") {
                self.turnOff(data)
            } else {
                self.turnOn(data)
            }
        }

        self.updateStatus = function(data) {
            OctoPrint.plugins.switchbot_plug.status().then(r => {
                self.power(r.power)
            })
        }

        self.updateStatus()
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: SwitchBotPlugViewModel,
        dependencies: [],
        elements: ["#sidebar_plugin_switchbot_plug"]
    });
});
