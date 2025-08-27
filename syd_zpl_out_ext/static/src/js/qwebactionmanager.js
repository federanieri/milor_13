odoo.define("report_zpl.report", function (require) {
    "use strict";

    var core = require("web.core");
    var ActionManager = require("web.ActionManager");
    // var crash_manager = require("web.crash_manager");
    var framework = require("web.framework");
    var session = require("web.session");
    var _t = core._t;

    ActionManager.include({

        _downloadReportZPL: function (url, actions) {
            framework.blockUI();
            var def = $.Deferred();
            var type = "zpl";
            var cloned_action = _.clone(actions);

            if (_.isUndefined(cloned_action.data) ||
                _.isNull(cloned_action.data) ||
                (_.isObject(cloned_action.data) && _.isEmpty(cloned_action.data)))
            {
                if (cloned_action.context.active_ids) {
                    url += "/" + cloned_action.context.active_ids.join(',');
                }
            } else {
                url += "?options=" + encodeURIComponent(JSON.stringify(cloned_action.data));
                url += "&context=" + encodeURIComponent(JSON.stringify(cloned_action.context));
            }

            var blocked = !session.get_file({
                url: url,
                data: {
                    data: JSON.stringify([url, type]),
                },
                success: def.resolve.bind(def),
                error: function () {
                    // crash_manager.rpc_error.apply(crash_manager, arguments);
                    def.reject();
                },
                complete: framework.unblockUI,
            });
            if (blocked) {
                // AAB: this check should be done in get_file service directly,
                // should not be the concern of the caller (and that way, get_file
                // could return a deferred)
                var message = _t('A popup window with your report was blocked. You ' +
                                 'may need to change your browser settings to allow ' +
                                 'popup windows for this page.');
                this.do_warn(_t('Warning'), message, true);
            }
            return def;
        },

        _triggerDownload: function (action, options, type) {
            var self = this;
            var reportUrls = this._makeReportUrls(action);
            if (type === "zpl") {
                // function doModal(heading, formContent) {
                //     let html =  '<div id="dynamicModal" class="modal fade" tabindex="-1" role="dialog" aria-labelledby="confirm-modal" aria-hidden="true">';
                //     html += '<div class="modal-dialog">';
                //     html += '<div class="modal-content">';
                //     html += '<div class="modal-header">';
                //     html += '<h5 class="modal-title">Modal title</h5>';
                //     html += '<button type="button" class="close" data-dismiss="modal" aria-label="Close">';
                //     html += '<span aria-hidden="false">&times;</span>';
                //     html += '</button>';
                //
                //     // html += '<a class="close" data-dismiss="modal">×</a>';
                //     // html += '<h4>'+heading+'</h4>'
                //     html += '</div>';
                //     html += '<div class="modal-body">';
                //     html += formContent;
                //     html += '</div>';
                //     html += '<div class="modal-footer">';
                //     html += '<span class="btn btn-primary" data-dismiss="modal">Close</span>';
                //     html += '</div>';  // content
                //     html += '</div>';  // dialog
                //     html += '</div>';  // footer
                //     html += '</div>';  // modalWindow
                //     $('body').append(html);
                //     $("#dynamicModal").modal();
                //     $("#dynamicModal").modal('show');
                //
                //     $('#dynamicModal').on('hidden.bs.modal', function (e) {
                //         $(this).remove();
                //     });
                //
                // }
                // doModal('test');
                return this._downloadReportZPL(reportUrls[type], action).then(function () {
                    if (action.close_on_report_download) {
                        var closeAction = {type: 'ir.actions.act_window_close'};
                        return self.doAction(closeAction, _.pick(options, 'on_close'));
                    } else {
                        return options.on_close();
                    }
                });
            }
            return this._super.apply(this, arguments);
        },

        // _makeReportUrls: function (action) {
        //     var reportUrls = this._super(action);
        //     reportUrls.zpl = reportUrls.text.replace(
        //         '/report/text/', '/report/zpl/');
        //     return reportUrls;
        // },

        _makeReportUrls: function (action) {
            let reportUrls = this._super.apply(this, arguments);
            reportUrls.zpl = '/report/zpl/' + action.report_name;
            return reportUrls;
        },

        _executeReportAction: function (action, options) {
            if (action.report_type === 'zpl') {
                return this._triggerDownload(action, options, 'zpl');
            }
            return this._super(action, options);
        },

    });

});
