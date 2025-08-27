from odoo.addons.web.controllers import main as main_report
from odoo.http import content_disposition, route, request
from odoo.tools.safe_eval import safe_eval

import json
import time
import re


# INFO: creates a new report output type for zpl.
class ReportController(main_report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == 'zpl':
            report = request.env['ir.actions.report']._get_report_from_name(reportname)
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                # INFO: Remove 'lang' here, because not needed in data from webclient.
                data['context'] = json.loads(data['context'])
                if data['context'].get('lang'):
                    del data['context']['lang']
                context.update(data['context'])

            zpl = report.with_context(context).render_zpl(docids, data=data)[0]

            if docids:
                obj = request.env[report.model].browse(docids)
                multi = not (report.print_report_name and not len(obj) > 1)

                filename = safe_eval(
                    report.print_report_name,
                    # INFO: When multiple object then add an 's' at the name of the 'object' field.
                    {'object%s' % ('s' if multi else ''): obj, 'time': time, 'multi': multi})
            else:
                filename = report.name

            # INFO: sets default ZPL extension (from user settings or standard one).
            ext = request.env.user.zpl_out_ext or 'zpl'

            # INFO: looks for ZPL filters system parameter.
            fe = request.env['ir.config_parameter'].sudo().get_param('zpl_out_exts_filter')
            fe = fe and json.loads(fe)
            if fe:
                for f in fe:
                    res = re.match(f.get('filter'), filename, re.M | re.I)
                    # INFO: in case (last) matched filter then sets new ZPL extension.
                    if res:
                        ext = f.get('ext')

            # INFO: sets ZPL filename extension.
            filename = "%s.%s" % (filename, ext)

            zplhttpheaders = [
                ('Content-Type', 'text/txt'),
                ('Content-Length', len(zpl)),
                (
                    'Content-Disposition',
                    content_disposition(filename)
                )
            ]
            return request.make_response(zpl, headers=zplhttpheaders)
        return super(ReportController, self).report_routes(reportname, docids, converter, **data)
