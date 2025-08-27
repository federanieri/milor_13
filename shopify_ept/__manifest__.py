{
    # App information
    'name': 'Shopify Odoo Connector',
    'version': '13.0.47.1',
    'category': 'Sales',
    'summary': 'Our Shopify Connector helps you in integrating and managing your Shopify store with Odoo by providing the most useful features of Product and Order Synchronization. This solution is compatible with our other apps i.e. Amazon, ebay, magento, Inter Company Transfer, Shipstation.Apart from Odoo Shopify Connector, we do have other ecommerce solutions or applications such as Woocommerce connector, Magento Connector, and also we have solutions for Marketplace Integration such as Odoo Amazon Connector, Odoo eBay Connector, Odoo Walmart Connector, Odoo Bol.com Connector.Aside from ecommerce integration and ecommerce marketplace integration, we also provide solutions for various operations, such as shipping , logistics , shipping labels , and shipping carrier management with our shipping integration, known as the Shipstation connector.For the customers who are into Dropship business, we do provide EDI Integration that can help them manage their Dropshipping business with our Dropshipping integration or Dropshipper integration.It is listed as Dropshipping EDI integration and Dropshipper EDI integration.Emipro applications can be searched with different keywords like Amazon integration, Shopify integration, Woocommerce integration, Magento integration, Amazon vendor center module, Amazon seller center module, Inter company transfer, Ebay integration, Bol.com integration, inventory management, warehouse transfer module, dropship and dropshipper integration and other Odoo integration application or module',
    'license': 'OPL-1',

    # Author
    'author': 'Emipro Technologies Pvt. Ltd.',
    'website': 'http://www.emiprotechnologies.com/',
    'maintainer': 'Emipro Technologies Pvt. Ltd.',

    # Dependencies
    'depends': ['common_connector_library',
                'auto_invoice_workflow_ept'],

    # Views
    'init_xml': [],
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'view/instance_view.xml',
        'wizard/res_config_view.xml',
        'data/ir_sequence.xml',
        'data/ir_cron_data.xml',
        'data/product_data.xml',
        'data/ir_cron_data_inherit.xml',
        'data/import_order_status.xml',
        'view/common_log_book_view.xml',
        'view/shopify_job_log.xml',
        'view/product_template_view.xml',
        'view/product_product_view.xml',
        'wizard/process_import_export_view.xml',
        'view/customer_data_queue_line_ept.xml',
        'view/payment_gateway_view.xml',
        'wizard/queue_process_wizard_view.xml',
        'view/product_data_queue_view.xml',
        'view/order_data_queue_ept.xml',
        'view/customer_data_queue_ept.xml',
        'view/location_ept.xml',
        'view/sale_order_view.xml',
        'view/res_partner_view.xml',
        'view/sale_workflow_config_view.xml',
        'view/stock_picking_view.xml',
        'wizard/cron_configuration_ept.xml',
        'wizard/cancel_refund_order_wizard_view.xml',
        'view/account_invoice_view.xml',
        'report/sale_report_view.xml',
        'view/dashboard_view.xml',
        'view/order_data_queue_line_ept.xml',
        'view/product_data_queue_line_view.xml',
        'view/product_image_ept.xml',
        "wizard/prepare_product_for_export.xml",
        'view/shopify_payout_report_ept.xml',
    ],
    'demo_xml': [],

    # Odoo Store Specific
    'images': ['static/description/shopify-odoo-cover.gif'],

    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': 'https://www.emiprotechnologies.com/r/mGK',
    'price': 379.00,
    'currency': 'EUR',
}
