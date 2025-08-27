from odoo import api, models, fields
from .query import QueryList
from .function import *
from odoo.exceptions import UserError


class ChangeEffectiveWizard(models.TransientModel):
    _name = "change.effective.wizard"

    # Definisikan field wizard
    effective_date = fields.Datetime(string="Effective Date", help="Date at which the transfer is processed")
    rewrite_related_picking = fields.Boolean(string="Apply to Other Stock Picking", default=False, help="Also Apply to Other Stock Picking Which Has the Same Source Document Name")

    # Onchange sebagai reminder ketika memilih tanggal masa depan untuk memilih tanggal di masa lalu saja
    @api.onchange('effective_date')
    def effective_future(self):
        selected = self.env['stock.picking'].browse(self._context.get('active_ids', []))
        current_date = datetime.now()

        # Bandingkan tanggal hari ini dengan tanggal yang terpilih
        # Jika tanggal tidak sesuai (lebih ke masa depan) maka tidak bisa proses
        if self.effective_date and self.effective_date > current_date:
            raise UserError('The date selected is still in the future. Make sure to only do a backdate!')

    # Simpan record
    def update_effective_date(self):
        query = QueryList()  # instantiation query

        # Memanggil record active_id ke dalam transient model
        for picking in self.env['stock.picking'].browse(self._context.get('active_ids', [])):

            # Mendefinisikan field yang ada di wizard (model.Transient)
            picking_name = picking.name
            company_id = picking.company_id
            wildcard_picking_name = concat(picking_name)
            picking_source_document = picking.origin
            selected_effective_date = self.effective_date

            # Melakukan pengecekan internal atau eksternal transfer
            # Jika picking_source_document ada, maka itu adalah eksternal transfer
            if picking_source_document:
                # Jika rewrite_related_picking tidak dicentang, maka update satu picking terpilih saja
                # if self.rewrite_related_picking == False:
                # Update picking
                do_update(query.update_stock_picking_by_name, self.effective_date, picking_name)

                # Update Sale Order
                do_update(query.update_sale_order, self.effective_date, picking_source_document)

                # Update account_move date
                do_update(query.update_journal_entry, self.effective_date, wildcard_picking_name)

                # Update account_move name (journal entry name)
                stj_account_move_find_sequence = account_move_concat(str(selected_effective_date.year), str(selected_effective_date.month))
                stj_account_move_sequences = [stj_account_move for stj_account_move in self.env['account.move'].search([('name', 'ilike', stj_account_move_find_sequence)]).mapped('name')]
                # cek apakah stj sebelumnya sudah pernah terbuat. jika belum maka buat nama baru, jika sudah teruskan nama yang sudah ada
                if stj_account_move_sequences == []:
                    update_account_move(wildcard_picking_name, selected_effective_date)
                else:
                    stj_sequences_max = str(max(stj_account_move_sequences))
                    stj_sequences_trim = int(stj_sequences_max.replace(stj_account_move_find_sequence, ''))
                    stj_sequences_addition = stj_sequences_trim + 1
                    update_account_move(wildcard_picking_name, selected_effective_date, stj_sequences_addition)

                # Update account_move_line
                do_update(query.update_journal_entry_line, self.effective_date, wildcard_picking_name)

                # Update stock_move
                do_update(query.update_stock_move, self.effective_date, picking_name)

                # Update stock_move_line
                do_update(query.update_stock_move_line, self.effective_date, picking_name)

                # Update stock valuation
                product_inside_picking = []
                for stock_move_id in self.env['stock.move'].search([('reference','=', picking_name)]):
                    do_update(query.update_inventory_valuation_date, self.effective_date, int(stock_move_id))
                    product_inside_picking.append(stock_move_id.product_id)


                # # Account Move Update if foreign currency
                # # Ambil dulu system currency (dari company) dan foreign country (dari PO atau SO)
                # system_currency = self.env['res.company'].search([('id', '=', int(company_id))]).currency_id.id
                # purchase_orders_id = self.env['purchase.order'].search([('name', '=', picking_source_document)])
                # sales_orders_id = self.env['sale.order'].search([('name', '=', picking_source_document)])
                # foreign_currency = int(purchase_orders_id.currency_id) if bool(purchase_orders_id) == True else None or int(sales_orders_id.pricelist_id.currency_id) if bool(sales_orders_id) == True else None
                #
                # if picking.picking_type_id.code == 'incoming':
                #     if int(system_currency) != int(foreign_currency):
                #         # Ambil currency rate berdasarkan tanggal yang dipilih & tentukan ratenya
                #         currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', foreign_currency), ('name', '=', selected_effective_date.strftime('%Y-%m-%d'))]).rate
                #         try:
                #             currency_value = float(1 / currency_rate)
                #         except:
                #             raise UserError('You have selected the currency rate of '+ str(purchase_orders_id.currency_id.name or sales_orders_id.currency_id.name) +' which is currently not available based on your selected date. Make sure to fill it under Accounting > Settings > Currencies > ' + str(purchase_orders_id.currency_id.name or sales_orders_id.currency_id.name) +'!')
                #
                #         if bool(purchase_orders_id) == True:
                #             update_stock_valuation_po(picking_name, purchase_orders_id, currency_value, product_inside_picking)
                #
                #         # Ubah account_move_line debit credit
                #
                #         price_unit = []
                #         counter = 0
                #         for product in product_inside_picking:
                #             for purchase_order_line in request.env['purchase.order.line'].search([('product_id', '=', int(product)), ('order_id', '=', int(purchase_orders_id))]):
                #                 if float(purchase_order_line.price_unit) * float(purchase_order_line.product_qty) != float(purchase_order_line.price_total):
                #                     unit_value = (float(currency_value) * float(purchase_order_line.price_unit))  # pajak excluded
                #                 else:
                #                     unit_value = (float(currency_value) * float(purchase_order_line.price_unit)) - (float(currency_value) * (float(purchase_order_line.price_tax / purchase_order_line.product_qty)))
                #
                #                 price_unit.append(float(unit_value))
                #                 counter += 1
                #
                #         price_unit = sorted(price_unit)
                #         print(price_unit)
                #
                #         for prod in product_inside_picking:
                #             penghitung = 0
                #             for account_move_line in self.env['account.move.line'].search([('ref', 'like', picking_name), ('product_id', '=', int(prod))]):
                #                 if account_move_line.debit != 0:
                #                     # aydi_debit = float(account_move_line.quantity) * float(price_unit[a])
                #                     aydi_debit = float(price_unit[penghitung]) * account_move_line.quantity
                #                     account_move_line.with_context(check_move_validity=False).write({'debit': abs(aydi_debit)})
                #
                #                 if account_move_line.credit != 0:
                #                     # aydi_credit = float(account_move_line.quantity) * float(price_unit[a])
                #                     aydi_credit = float(price_unit[penghitung]) * account_move_line.quantity
                #                     account_move_line.with_context(check_move_validity=False).write({'credit': abs(aydi_credit)})
                #
                #             penghitung += 1

            else:
                # Update internal transfer
                do_update(query.update_stock_picking_by_name, self.effective_date, picking_source_document)

                # Update stock move
                do_update(query.update_stock_move, self.effective_date, picking_source_document)

                # Update stock_move_line
                do_update(query.update_stock_move_line, self.effective_date, picking_source_document)