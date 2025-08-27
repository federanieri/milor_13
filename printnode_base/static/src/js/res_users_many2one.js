odoo.define('printnode_base.res_users_many2one', function (require) {
    "use strict";

    const FieldMany2One = require('web.relational_fields').FieldMany2One;
    const FieldRegistry = require('web.field_registry');
    const localStorage = require('web.local_storage');
    const session = require('web.session');

    const WorkstationDeviceField = FieldMany2One.extend({
        init: function (parent, name, record, options) {
            // Save form object for later use
            this.parent = parent;

            // Clean record field data if not presented in localStorage
            // This is required to clean workstation devices fields after clean field and save
            if (!localStorage.getItem('printnode_base.' + name)) {
                record.data[name] = false;
            }

            this._super.apply(this, arguments);
        },

        commitChanges: function () {
            // This is not a perfect way to update workstations devices but the best one we can use :)
            // The only disadvantage of use of this method is inability to detect form validation
            // issues (in this case we still will update workstation devices)
            const invalidFields = this.parent.canBeSaved(this.record.id);

            // If there is not invalid fields then save the new workstation device
            if (invalidFields.length === 0) {
                if (this.value.data) {
                    const workstationDeviceId = this.value.data.id;

                    // Save in localStorage for future use
                    localStorage.setItem('printnode_base.' + this.name, workstationDeviceId);

                    // Update context to send with every request
                    session.user_context[this.name] = workstationDeviceId;
                } else {
                    // Clean localStorage
                    localStorage.removeItem('printnode_base.' + this.name);

                    // Remove from user context
                    delete session.user_context[this.name];
                }
            }

            return this._super.apply(this, arguments);
        },
    });

    FieldRegistry.add('res_users_workstation_device_many2one', WorkstationDeviceField);

    return WorkstationDeviceField;
});
