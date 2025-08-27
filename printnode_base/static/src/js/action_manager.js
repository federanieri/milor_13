odoo.define('printnode_base.ReportActionManager', function (require) {
    "use strict";

    const ActionManager = require('web.ActionManager');
    const core = require('web.core');
    const framework = require('web.framework');
    const session = require('web.session');
    const ajax = require('web.ajax');
    const localStorage = require('web.local_storage');

    const WORKSTATION_DEVICES = require('printnode_base.constants');

    const _t = core._t;

    ActionManager.include({
        _printOrDownload: function (url, download_only) {
            var self = this;
            var type = url.split('/')[2];
            if (type === "pdf" || type === "text") {
                type = 'qweb-' + type;
            }

            // Information about workstation devices
            var workstationDevices = this._getWorkstationDevices();

            var payload = JSON.stringify([url, type, workstationDevices]);
            var def_obj = $.Deferred();

            if (!download_only && session.printnode_enabled) {
                framework.blockUI();

                ajax.post('/report/check', { data: payload }).then(
                    (res) => { def_obj.resolve((res === 'true')) },
                    () => { def_obj.resolve(false) }
                );
            } else {
                def_obj.resolve(false);
            }

            return $.when(def_obj).then(function (res) {
                if (res) {
                    return ajax.post('/report/print', { data: payload }).then(
                        self._printSuccessCallback.bind(self),
                        self._printErrorCallback.bind(self),
                    );
                } else {
                    framework.unblockUI();
                    return self._downloadReport(url);
                }
            });
        },

        _triggerDownload: function (action, options, type) {
            var reportUrls = this._makeReportUrls(action);

            // The first one - from Download menu, the second - from Print Label wizard
            let downloadOnly = options.download || action.context.download;

            if (type === "pdf" || type === "text" || (type === "py3o" && action["py3o_filetype"] === "pdf")) {
                return this._printOrDownload(reportUrls[type], downloadOnly).then(() => {
                    if (action.close_on_report_download) {
                        var closeAction = { type: 'ir.actions.act_window_close' };
                        return this.doAction(closeAction, _.pick(options, 'on_close'));
                    } else {
                        return options.on_close();
                    }
                });
            }

            return this._super.apply(this, arguments);
        },

        _printSuccessCallback: function (print_result) {
            framework.unblockUI();

            try { // Case of a serialized Odoo Exception: It is Json Parsable
                print_result = JSON.parse(print_result);
                if (print_result.notify) {
                    this.displayNotification({
                        type: print_result.success ? 'success' : 'warning',
                        title: print_result.title,
                        message: print_result.message,
                        sticky: false,
                    });
                }
            } catch (e) { // Arbitrary uncaught python side exception
                var error;
                var doc = new DOMParser().parseFromString(print_result, 'text/html');
                var nodes = doc.body.children.length === 0 ? doc.body.childNodes : doc.body.children;

                try { // Case of a serialized Odoo Exception: It is Json Parsable
                    var node = nodes[1] || nodes[0];
                    error = JSON.parse(node.textContent);
                } catch (e) { // Arbitrary uncaught python side exception
                    error = {
                        message: nodes.length > 1 ? nodes[1].textContent : '',
                        data: {
                            name: 'Server Error',
                            title: nodes.length > 0 ? nodes[0].textContent : '',
                        }
                    };
                }

                this.call('crash_manager', 'rpc_error', error);
            }
        },

        _printErrorCallback: function () {
            framework.unblockUI();

            this.do_notify(
                _t('Printing error!'),
                _t('Something went wrong. Report is not printed'),
                false
            );
        },

        _getWorkstationDevices: function () {
            let res = {};

            for (let workstationDevice of WORKSTATION_DEVICES) {
                res[workstationDevice] = localStorage.getItem('printnode_base.' + workstationDevice);
            }

            return res;
        },
    });
});
