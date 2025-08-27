odoo.define('printnode.status_menu', function (require) {
    "use strict";

    const ajax = require('web.ajax');
    const core = require('web.core');
    const session = require('web.session');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');

    const WORKSTATION_DEVICES = require('printnode_base.constants');
    const MANAGER_GROUP = 'printnode_base.printnode_security_group_manager';

    const QWeb = core.qweb;

    const ActionMenu = Widget.extend({
        template: 'printnode_status_menu',

        events: {
            'show.bs.dropdown': '_onStatusMenuShow',
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);

            this.limits = [];
            this.releases = [];
            this.newRelease = false;
            this.loaded = false;
        },

        willStart: function () {
            // We check if current user has Manager group to make some elements of status menu
            // visible only for managers
            const groupCheckPromise = session.user_has_group(MANAGER_GROUP).then(
                this._loadContent.bind(this));

            return groupCheckPromise;
        },

        _loadContent: function (isManager) {
            this.isManager = isManager;

            if (isManager) {
                // Rate Us URL
                let odooVersion = odoo.session_info.server_version;
                // This attribute can include some additional symbols we do not need here (like 12.0e+)
                odooVersion = odooVersion.substring(0, 4);
                this.rateUsURL = `https://apps.odoo.com/apps/modules/${odooVersion}/printnode_base/#ratings`;

                const limitsPromise = this._rpc({ model: 'printnode.account', method: 'get_limits' });

                // Check if model with releases already exists 
                const releasesPromise = ajax.post("/dpc/release-model-check").then((data) => {
                    const status = JSON.parse(data);

                    // If model exists load releases
                    if (status) {
                        return this._rpc({ model: 'printnode.release', method: 'search_read' });
                    }
                    // If not exist return empty array
                    return [];
                });

                return Promise.all(
                    [limitsPromise, releasesPromise]
                ).then(this._loadedCallback.bind(this));
            } else {
                // There is nothing to load
                this.loaded = true;
            }
        },

        _loadedCallback: function ([limits, releases]) {
            // Process limits
            this.limits = limits;

            // Process accounts
            this.releases = releases;
            this.newRelease = releases.length > 0;

            // Loading ended
            this.loaded = true;
        },

        _capitalizeWords: (str) => {
            const words = str.split(" ");
            let capitalizedWords = words.map(w => w[0].toUpperCase() + w.substr(1))
            return capitalizedWords.join(' ');
        },

        _onStatusMenuShow: function () {
            /*
            Update workstation devices each time user clicks on the status menu
            */
            const devicesInfo = Object.fromEntries(
                WORKSTATION_DEVICES
                    .map(n => [n, localStorage.getItem('printnode_base.' + n)])  // Two elements array
                    .filter(i => i[1]) // Skip empty values
            );

            const devicesPromise = this._rpc({
                model: 'res.users',
                method: 'validate_device_id',
                kwargs: { devices: devicesInfo }
            })

            devicesPromise.then((data) => {
                // Process workstation devices
                const devices = WORKSTATION_DEVICES.map(
                    device => {
                        // Remove printnode_ and _id from the of string
                        let deviceName = device.substring(10, device.length - 3).replace(/_/g, ' ');

                        // Return pairs (type, name)
                        return [this._capitalizeWords(deviceName), data[device]];
                    }
                );

                const template = QWeb.render('printnode_workstation_devices', { devices: devices });

                this.$el.find('.o_printnode_status_menu_devices').html(template);
            })
        }

    });

    SystrayMenu.Items.push(ActionMenu);

    return ActionMenu;
});
