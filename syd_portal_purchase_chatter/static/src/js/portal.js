odoo.define('syd_portal_purchase_chatter.portal', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.portalExtraSearchPanel = publicWidget.Widget.extend({
    selector: '.o_portal_extra_search_panel',
    events: {
        'click .extra-search-submit': '_onSearchSubmitClick',
        'click .dropdown-item': '_onDropdownItemClick',
        'keyup input[name="extra_search"]': '_onSearchInputKeyup',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._adaptSearchLabel(this.$('.dropdown-item.active'));
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptSearchLabel: function (elem) {
        var $label = $(elem).clone();
        $label.find('span.nolabel').remove();
        this.$('input[name="extra_search"]').attr('placeholder', $label.text().trim());
    },
    /**
     * @private
     */
    _search: function () {
        var search = $.deparam(window.location.search.substring(1));
        search['extra_search_in'] = this.$('.dropdown-item.active').attr('href').replace('#', '');
        search['extra_search'] = this.$('input[name="extra_search"]').val();
        window.location.search = $.param(search);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onSearchSubmitClick: function () {
        this._search();
    },
    /**
     * @private
     */
    _onDropdownItemClick: function (ev) {
        ev.preventDefault();
        var $item = $(ev.currentTarget);
        $item.closest('.dropdown-menu').find('.dropdown-item').removeClass('active');
        $item.addClass('active');

        this._adaptSearchLabel(ev.currentTarget);
    },
    /**
     * @private
     */
    _onSearchInputKeyup: function (ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER) {
            this._search();
        }
    },
});
});
