from odoo.http import request, Controller, route
from werkzeug.exceptions import NotFound


from odoo import http
import logging
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import TableCompute
from odoo.addons.website_sale_wishlist.controllers.main import WebsiteSale
from odoo.addons.bi_website_shop_product_filter.controllers.main import WebsiteSale as WebsiteSaleFilter
#from milor_master.odoo13_milor_collaudo.bi_website_shop_product_filter.controllers.main import WebsiteSale as WebsiteSaleFilter
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

_logger = logging.getLogger(__name__)

class NaEmiproThemeBase(http.Controller):

    @http.route(['/promo','/promo/page/<int:page>'], type='http', auth="public", website=True)
    def Promo(self, brand=None, page=0, category=None, search='', ppg=False, **post):
        if request.session.filters != request.httprequest.args.getlist('filter'):
            page = 0

        product_categories = request.env['product.public.category']
        if category:
            category = product_categories.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = product_categories

        arr_options = request.httprequest.args.getlist('attrib')
        options_values = [[int(x) for x in v.split("-")] for v in arr_options if v]
        options_group = {v[1] for v in options_values}

        items_filter = request.env['product.filter']
        items_filter_arr = request.httprequest.args.getlist('filter')
        request.session['filters'] = items_filter_arr

        items_filter_values = [[int(x) for x in v.split("-")] for v in items_filter_arr if v]
        items_filter_group = {v[1] for v in items_filter_values}

        filters = items_filter.search([])
        filter_group = request.env['group.filter'].search([])

        domain = WebsiteSaleFilter._get_search_domain(self, search, category, options_values,
                                                      filter_values=items_filter_values)
        promo_season_list = request.env['product.season'].search([('is_promo_website', '=', True)]).mapped('id')
        domain.append(tuple(('season_id', 'in', promo_season_list)))

        if brand:
            domain += [('product_brand_ept_id.id', '=', brand.id)]
        else:
            domain += [('product_brand_ept_id', '!=', False)]

        pricing, general_pricing = WebsiteSale._get_pricelist_context(self)

        request.context = dict(request.context, pricelist=general_pricing.id, partner=request.env.user.partner_id)

        url = "/promo"
        if brand:
            url = "/promo/%s" % slug(brand)
        if arr_options:
            post['attrib'] = arr_options
        if items_filter_arr:
            post['filter'] = items_filter_arr
        if search:
            post["search"] = search

        shop_url = QueryURL('/shop', category=category and int(category), search=search, filter=items_filter_arr,
                            attrib=arr_options, order=post.get('order'))

        item = request.env['product.template'].with_context(bin_size=True)

        filter_item = item.with_context(lang=u'en_US').search(domain)
        website_domain = request.website.website_domain()
        categs = [('parent_id', '=', False)] + website_domain
        if search:
            categ_filter = product_categories.search(
                [('product_tmpl_ids', 'in', filter_item.ids)] + website_domain).parents_and_self
            categs.append(('id', 'in', categ_filter.ids))
        else:
            categ_filter = product_categories
        categs = product_categories.search(categs)

        if category:
            url = "/shop/category/%s" % slug(category)

        total_items = len(filter_item)
        ppr = request.env['website'].get_current_website().shop_ppr or 4
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20
        pager = request.website.pager(url=url, total=total_items, page=page, step=ppg, scope=7, url_args=post)
        items = item.with_context(lang=u'en_US').search(domain, limit=ppg, offset=pager['offset'],
                                                              order=WebsiteSale._get_search_order(self, post))

        applied_filter = False
        if items_filter_values:
            applied_filter = True

        if filter_group:
            activities_set = [request.env['product.filter'].concat(*b) for a, b in
                             groupbyelem(filters, itemgetter('group_id'))]
        else:
            activities_set = [filters]

        item_options = request.env['product.attribute']

        page_layout = request.session.get('website_sale_shop_layout_mode')
        if not page_layout:
            if request.website.viewref('website_sale.products_list_view').active:
                page_layout = 'list'
            else:
                page_layout = 'grid'

        new_qty = int(post.get('add_qty', 1))


        values = {
            'search': search,
            'category': category,
            'attrib_values': options_values,
            'attrib_set': options_group,
            'pager': pager,
            'pricelist': general_pricing,
            'add_qty': new_qty,
            'products': items,
            'search_count': total_items,
            'bins': TableCompute().process(items, ppg, ppr),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': item_options,
            'keep': shop_url,
            'search_categories_ids': categ_filter.ids,
            'layout_mode': page_layout,
            'brand': brand,
            'is_brand_page': True,
            'filter_set': items_filter_group,
            'filter_values': items_filter_values,
            'filters': filters,
            'filter_group': filter_group,
            'grouped_tasks': activities_set,
            'has_plating': next((x for x in domain if x[0] == 'plating_id'), None)
        }
        if category:
            values['main_object'] = category
        return request.render("website_sale.products", values)