odoo.define('syd_zpl_out_ext.systray_menu', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var core = require("web.core");
    var QWeb = core.qweb;
    const session = require("web.session");

    /**
     *
     *
     */
    var ActionMenu = Widget.extend({
        name: 'zpl_out_ext_systray_menu',
        // INFO: default tagname to span to avoid issue when there is nothing to render (an empty <div> will misalign systray menu).
        tagName: 'span',

        start: function () {
            let self = this;
            return Promise.all([
                this._super.apply(this, arguments),

                self._rpc({
                    model: 'res.users',
                    method: 'get_zpl_out_exts',
                }).then(function (res) {
                    if (res.exts) {
                        // INFO: keeps render here to level one promise because otherwise won't work.
                        self.$el = $(QWeb.render('syd_zpl_out_ext.systray_menu', {widget: self}));
                        self._renderDropdown(res.selected_ext, res.exts);
                    }
                })
            ]);
        },

        _renderDropdown: function (selected_ext, exts) {
            let self = this;

            // INFO: renders current user selected ZPL ext.
            self._renderHeader(selected_ext);

            // INFO: renders dropdown items with loaded JSON data.
            let $dropdown = $(QWeb.render("syd_zpl_out_ext.systray_dropdown", {
                selected_ext: selected_ext,
                exts: exts,
            }));

            // INFO: appends loaded items to the dropdown menu.
            self.$el.append($dropdown);

            // INFO: handles dropdown click event.
            $dropdown.on("click", ".dropdown-item", function (e) {
                e.preventDefault();
                e.stopImmediatePropagation();

                // $dropdown.find('.dropdown-menu').removeClass('show');

                // INFO: removes currect selected ext and sets new one.
                $dropdown.find('.dropdown-item.selected').removeClass('selected');
                $(this).addClass('selected');

                let selected_ext = $(this).data('ext');

                self._rpc({
                    model: 'res.users',
                    method: 'set_zpl_out_ext',
                    args: [selected_ext],
                }).then(function () {
                    // INFO: render new ZPL selected ext.
                    self._renderHeader(selected_ext);
                });
            });
        },

        _renderHeader: function (s) {
            this.$('.o_zpl_out_ext_selected').html(s);
        }

    });

    SystrayMenu.Items.unshift(ActionMenu);

    return ActionMenu;
});
