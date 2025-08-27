# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Show Images in Excel",
  "summary"              :  """Odoo Show Images in Excel allows you to export the images instead of Base64 while exporting Excel file.""",
  "category"             :  "Extra Tools",
  "version"              :  "1.0.0",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "maintainer"           :  "Mandeep Duggal",
  "website"              :  "https://store.webkul.com/Odoo-Show-Images-in-Excel.html",
  "description"          :  """Show Images in Excel
Odoo Show Images in Excel
Show Images in Excel in Odoo
export Images in excel
convert Base64 to image
Images in Excel
Image Format in Excel
Odoo Image E""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=image_in_excel&lifetime=90&lout=1&custom_url=/",
  "depends"              :  [
                             'base',
                             'web',
                            ],
  "data"                 :  [],
  "demo"                 :  [],
  "css"                  :  [],
  "js"                   :  [],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  35,
  "currency"             :  "USD",
  "external_dependencies":  {'python3': ['XlsxWriter']},
}