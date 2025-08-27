# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PrintnodeReportAbstractWizard(models.AbstractModel):
    _name = 'printnode.report.abstract.wizard'
    _description = 'Print Report via PrintNode'

    number_copy = fields.Integer(
        default=1,
        string='Copies',
    )

    number_copy_selectable = fields.Boolean(
        default=lambda self: self.default_number_copy_selectable(),
    )

    printer_id = fields.Many2one(
        comodel_name='printnode.printer',
        default=lambda self: self._default_printer_id(),
    )

    printer_bin = fields.Many2one(
        'printnode.printer.bin',
        string='Printer Bin',
        required=False,
        domain='[("printer_id", "=", printer_id)]',
    )

    status = fields.Char(
        related='printer_id.status',
    )

    def _default_printer_id(self):
        """
        Return default printer to use in wizard
        """
        workstation_printer_id = self.env.user._get_workstation_device(
            'printnode_workstation_printer_id')

        # Workstation printer or user default printer
        return workstation_printer_id or self.env.user.printnode_printer or \
            self.env.company.printnode_printer

    @api.onchange('printer_id')
    def _onchange_printer(self):
        """
        Reset printer_bin field to avoid bug with printing
        in wrong bin
        """
        self.printer_bin = self.printer_id.default_printer_bin.id

    def default_number_copy_selectable(self):
        # return Boolean
        return False

    def get_attachment(self):
        # return (ir.attachment, params)
        return (None, None)

    def get_report(self):
        # return ir.actions.report
        return False

    def get_docids(self):
        # return list
        return []

    def do_print(self):
        self.ensure_one()

        # first try to print specified attachment
        attachment, params = self.get_attachment()

        if isinstance(params, str):
            params = {'title': params}

        if attachment is not None:
            return self._print_attachment(attachment, params)

        # if no attachment specified than try to print report
        return self._print_report()

    def _print_attachment(self, attachment, params):
        if not attachment:
            raise UserError(_('No attachment found.'))

        if not self.printer_id:
            if self.number_copy > 1:
                raise UserError(_(
                    'Only 1 copy can be downloaded '
                    'when printer is not selected.'
                ))

            return {
                'type': 'ir.actions.act_url',
                'name': params.get('title'),
                'url': '/web/content/%s?download=true' % attachment.id,
            }

        params.update({'copies': self.number_copy})

        if self.printer_bin:
            params.update({'options': {'bin': self.printer_bin.name}})

        self.printer_id.printnode_print_b64(
            data=attachment.datas.decode('ascii'),
            params=params
        )

        title = _('Document was sent to printer')
        message = _('Document "{}" was sent to printer {}').format(
            attachment.name,
            self.printer_id.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def _print_report(self):
        report = self.get_report()
        docids = self.get_docids()

        # add copies
        for i in range(self.number_copy - 1):
            docids += self.get_docids()

        # If no printer than download PDF
        if not self.printer_id:
            return report.with_context(download=True).report_action(docids=docids)

        options = {}
        if self.printer_bin:
            options['bin'] = self.printer_bin.name

        # If printer than send to printnode
        self.printer_id.printnode_print(
            report,
            docids,
            options=options,
        )

        title = _('Report was sent to printer')
        message = _('Document "{}" was sent to printer {}').format(
            report.name, self.printer_id.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }
