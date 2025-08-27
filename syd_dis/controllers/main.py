from odoo import http
from odoo.http import request

from werkzeug.utils import redirect


class MyController(http.Controller):

    @http.route('/syd_dis/download_txt/<int:task_id>', type='http', auth='user')
    def download_txt(self, task_id):
        task_id = request.env['project.task'].sudo().browse(task_id)
        if task_id:
            action = task_id.action_download_txt(only_orphans=False)
            return redirect(action.get('url'), 301)

    @http.route('/syd_dis/download_all_txt/<int:order_id>', type='http', auth='user')
    def download_all_txt(self, order_id=None):
        oid = request.env['purchase.order'].browse(order_id).sudo()

        action = oid.order_line.mapped('dis_task_id').action_download_txt(only_orphans=False)
        return action and redirect(action.get('url'), 301)
