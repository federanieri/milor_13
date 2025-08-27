from odoo.http import request
from datetime import datetime


def do_query(query, key):
    request.env.cr.execute(query, [key])


def do_update(query, key1, key2):
    request.env.cr.execute(query, [key1, key2])


def concat(pulled_name):
    percent_pulled_name = str(pulled_name + "%")
    return percent_pulled_name


def account_move_concat(year, date):
    stj_account_move_find_sequence = str("STJ" + "/" + year + "/" + date.zfill(2) + "/")
    return stj_account_move_find_sequence


def account_move_new_name(year, date, number):
    stj_account_move_new_name = str("STJ" + "/" + year + "/" + date.zfill(2) + "/" + str(number).zfill(4))
    return stj_account_move_new_name


def update_account_move(wildcard_picking_name, selected_effective_date, stj_sequences_addition=None):
    ids = request.env['account.move'].search([('ref', 'ilike', wildcard_picking_name)]).mapped('id')
    starter = stj_sequences_addition
    number = 1
    while number <= len(ids):
        for id in ids:
            if starter == None:
                stj_account_move_new_name = account_move_new_name(str(selected_effective_date.year), str(selected_effective_date.month), str(number))
                request.env.cr.execute("UPDATE account_move SET name = (%s) WHERE id = %s", [stj_account_move_new_name, id])
                number += 1
            else:
                stj_account_move_new_name = account_move_new_name(str(selected_effective_date.year), str(selected_effective_date.month), str(starter))
                request.env.cr.execute("UPDATE account_move SET name = (%s) WHERE id = %s", [stj_account_move_new_name, id])
                starter += 1
                number += 1


def update_stock_valuation_po(picking_name, purchase_orders_id, currency_value, product_inside_picking):
    value_per_unit = []
    counter = 0
    for product in product_inside_picking:
        for purchase_order_line in request.env['purchase.order.line'].search([('product_id', '=', int(product)),('order_id', '=', int(purchase_orders_id))]):
            if float(purchase_order_line.price_unit) * float(purchase_order_line.product_qty) != float(purchase_order_line.price_total):
                unit_value = (float(currency_value) * float(purchase_order_line.price_unit)) # pajak excluded
            else:
                unit_value = (float(currency_value) * float(purchase_order_line.price_unit)) - (float(currency_value) * (float(purchase_order_line.price_tax / purchase_order_line.product_qty))) # pajak included

            value_per_unit.append(unit_value)
            counter += 1

    counter = 0
    for product in product_inside_picking:
        for stock_valuation in request.env['stock.valuation.layer'].search([('description', 'like', picking_name),('product_id', '=', int(product))]):
            unit_value = value_per_unit[counter]
            stock_valuation.unit_cost = unit_value
            stock_valuation.value = stock_valuation.quantity * unit_value
            stock_valuation.remaining_value = unit_value * stock_valuation.remaining_qty
            counter += 1

