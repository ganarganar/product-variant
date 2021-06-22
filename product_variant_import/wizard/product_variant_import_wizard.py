##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

import base64
import codecs
import csv
import logging
import requests
import xlrd

from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, ustr

_logger = logging.getLogger(__name__)


class ProductVariantImportWizard(models.TransientModel):
    _name = "product.variant.import.wizard"
    _description = "Product Variant Import Wizard"

    import_type = fields.Selection(
        [("csv", "CSV File"), ("excel", "Excel File")],
        default="csv",
        string="Import File Type",
        required=True
    )
    method = fields.Selection(
        [("create", "Create Product Variants"), ("write", "Create or Update Product Variants")],
        default="create",
        string="Method",
        required=True
    )
    product_update_by = fields.Selection(
        [("name", "Name"), ("barcode", "Barcode"), ("int_ref", "Internal Reference")],
        default="name",
        string="Product Variant Update By",
        required=True
    )
    is_create_m2m_record = fields.Boolean(
        string="Create New Record for Dynamic M2M Field (if it doesn't exists)"
    )
    is_create_categ_id_record = fields.Boolean(
        string="Create New Record for Product Category Field (if doesn't exists)"
    )
    file = fields.Binary(
        string="File",
        required=True
    )

    def create_internal_category(self, categ_complete_name):
        categs_ids_list = []
        previous_categ = False
        for x in categ_complete_name.split("/"):
            x = x.strip()
            if x != "":
                search_categ = self.env["product.category"].sudo().search([("name", "=", x)], limit=1)
                if search_categ:
                    categs_ids_list.append(search_categ.id)
                    if previous_categ:
                        search_categ.update({"parent_id": previous_categ})
                    previous_categ = search_categ.id
                else:
                    # Create new one.
                    if previous_categ:
                        categ_id = self.env["product.category"].sudo().create({"name": x, "parent_id": previous_categ})
                    else:
                        categ_id = self.env["product.category"].sudo().create({"name": x})
                    categs_ids_list.append(categ_id.id)

                    previous_categ = categ_id.id

    # Validation methods for custom fields.

    def validate_field_value(self, field_name, field_type, field_value, field_required, field_name_m2o):
        """ Validate field value, depending on field type and given value."""
        self.ensure_one()
        try:
            checker = getattr(self, "validate_field_" + field_type)
        except AttributeError:
            _logger.warning(field_type + ": This type of field has no validation method.")
            return {}
        else:
            return checker(field_name, field_type, field_value, field_required, field_name_m2o)

    def validate_field_many2many(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            name_relational_model = self.env["product.product"].fields_get()[field_name]["relation"]

            ids_list = []
            if field_value.strip() not in (None, ""):
                for x in field_value.split(","):
                    x = x.strip()
                    if x != "":
                        record = self.env[name_relational_model].sudo().search([
                            (field_name_m2o, "=", x)
                            ], limit=1)

                        # If m2m record not found then create a new record for it.
                        # If tick in wizard.
                        if self.is_create_m2m_record and not record:
                            try:
                                record = self.env[name_relational_model].sudo().create({field_name_m2o: x})
                            except Exception as e:
                                msg = " - Value is not valid " + ustr(e)
                                return {"error": " - " + x + msg}
                                break
                        # If m2m record not found then create a new record for it.
                        if record:
                            ids_list.append(record.id)
                        else:
                            return {"error": " - " + x + " not found."}
                            break
            return {field_name: [(6, 0, ids_list)]}

    def validate_field_many2one(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            name_relational_model = self.env["product.product"].fields_get()[field_name]["relation"]
            record = self.env[name_relational_model].sudo().search([
                (field_name_m2o, "=", field_value)
                ], limit=1)
            return {field_name: record.id if record else False}

    def validate_field_text(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            return {field_name: field_value or False}

    def validate_field_integer(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            return {field_name: field_value or False}

    def validate_field_float(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            return {field_name: field_value or False}

    def validate_field_char(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}
        else:
            return {field_name: field_value or False}

    def validate_field_boolean(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        boolean_field_value = False
        if field_value.strip() == "Verdadero":
            boolean_field_value = True

        return {field_name: boolean_field_value}

    def validate_field_selection(self, field_name, field_type, field_value, field_required, field_name_m2o):
        self.ensure_one()
        if field_required and field_value in (None, ""):
            return {"error": " - " + field_name + " is required."}

        # Get selection field key and value.
        selection_key_value_list = self.env["product.product"].sudo(
        )._fields[field_name].selection
        if not isinstance(selection_key_value_list, list):
            selection_key_value_list = self.env["product.template"].sudo()._fields[field_name].selection

        if selection_key_value_list and field_value not in (None, ""):
            for tuple_item in selection_key_value_list:
                if tuple_item[1] == field_value:
                    return {field_name: tuple_item[0] or False}

            return {"error": " - " + field_name + " given value " + str(field_value) + " does not match for selection."}

        # finaly return false
        if field_value in (None, ""):
            return {field_name: False}

        return {field_name: field_value or False}

    # Validation methods for custom fields.

    def show_success_msg(self, counter, skipped_line_no):

        # Open the new success message box.
        view = self.env.ref("message_popup.message_wizard")
        view_id = view and view.id or False
        context = dict(self._context or {})
        dic_msg = str(counter) + " records imported successfully."
        if skipped_line_no:
            dic_msg = dic_msg + "\nNote:"
        for k, v in skipped_line_no.items():
            dic_msg = dic_msg + "\nRow no. " + k + " " + v + " "
        context["message"] = dic_msg
        return {
            "name": "Success",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "message.wizard",
            "views": [(view_id, "form")],
            "view_id": view_id,
            "target": "new",
            "context": context,
        }

    def read_xls_book(self):
        book = xlrd.open_workbook(file_contents=base64.decodestring(self.file))
        sheet = book.sheet_by_index(0)
        # Emulate Sheet.get_rows for pre-0.9.4.
        values_sheet = []
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value)
                        if is_float
                        else str(int(cell.value))
                    )
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # Emulate xldate_as_datetime for pre-0.9.3.
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if is_datetime
                        else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                    )
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append(u"True" if cell.value else u"False")
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s") % {
                            "row": rowx,
                            "col": colx,
                            "cell_value": xlrd.error_text_from_code.get(cell.value, _("Unknown error code %s.") % cell.value)
                        }
                    )
                else:
                    values.append(cell.value)
            values_sheet.append(values)
        return values_sheet

    def product_variant_import_apply(self):

        product_tmpl_obj = self.env["product.template"]
        ir_model_fields_obj = self.env["ir.model.fields"]

        # Perform import lead.
        if self and self.file:

            # For CSV
            if self.import_type == "csv" or self.import_type == "excel":
                counter = 1
                skipped_line_no = {}
                row_field_dic = {}
                row_field_error_dic = {}

                try:
                    values = []
                    if self.import_type == "csv":
                        file = str(base64.decodebytes(
                            self.file).decode("utf-8"))
                        values = csv.reader(file.splitlines())

                    elif self.import_type == "excel":
                        values = self.read_xls_book()

                    skip_header = True
                    running_tmpl = None

                    running_tmpl_domain = []
                    created_product_tmpl = False
                    has_variant = False

                    list_to_keep_attr = []
                    list_to_keep_attr_value = []

                    for row in values:
                        try:
                            if skip_header:
                                skip_header = False

                                for i in range(22, len(row)):
                                    name_field = row[i]
                                    name_m2o = False
                                    if "@" in row[i]:
                                        list_field_str = name_field.split("@")
                                        name_field = list_field_str[0]
                                        name_m2o = list_field_str[1]
                                    search_field = ir_model_fields_obj.sudo().search([
                                        ("model", "=", "product.product"),
                                        ("name", "=", name_field),
                                        ("store", "=", True),
                                    ], limit=1)

                                    if not search_field:
                                        search_field = ir_model_fields_obj.sudo().search([
                                            ("model", "=", "product.template"),
                                            ("name", "=", name_field),
                                            ("store", "=", True),
                                            ], limit=1)

                                    if search_field:
                                        field_dic = {
                                            "name": name_field,
                                            "type": search_field.type,
                                            "required": search_field.required,
                                            "name_m2o": name_m2o
                                        }
                                        row_field_dic.update({i: field_dic})
                                    else:
                                        row_field_error_dic.update(
                                            {row[i]: " - Field not found."})

                                counter = counter + 1
                                continue

                            # Check if any error in dynamic field.

                            if row_field_error_dic:
                                res = self.show_success_msg(
                                    0, row_field_error_dic)
                                return res

                            # Check if any error in dynamic field.

                            # Actual variant importing start here.

                            if row[0] not in (None, "") and row[1] not in (None, ""):
                                var_vals = {}

                                # Product Template start.
                                if row[0] != running_tmpl:
                                    running_tmpl = row[0]

                                    # Search or update product by.

                                    if self.product_update_by == "name":
                                        running_tmpl_domain = [
                                            ("name", "=", row[1]),
                                        ]

                                    elif self.product_update_by == "barcode":
                                        running_tmpl_domain = [
                                            ("product_variant_ids.barcode",
                                            "=", row[17]),
                                        ]

                                    elif self.product_update_by == "int_ref":
                                        running_tmpl_domain = [
                                            ("product_variant_ids.default_code",
                                            "=", row[16]),
                                        ]

                                    # Search or update product by.

                                    # TODO: NEED TO CLEAN LAST PRODUCT ALSO.
                                    if created_product_tmpl and self.method == "write":

                                        # Remove unnecessary attribute line.
                                        attrs = created_product_tmpl.attribute_line_ids.mapped(
                                            "attribute_id").filtered(lambda r: r.id not in list_to_keep_attr)
                                        for attr in attrs:
                                            line = created_product_tmpl.attribute_line_ids.search([
                                                ("attribute_id", "=", attr.id),
                                                ("product_tmpl_id", "=",
                                                created_product_tmpl.id),
                                            ], limit=1)
                                            if line:
                                                line.unlink()

                                        # Remove unnecessary attribute value from line.
                                        attr_values = created_product_tmpl.attribute_line_ids.mapped(
                                            "value_ids").filtered(lambda r: r.id not in list_to_keep_attr_value)
                                        for attr_value in attr_values:
                                            line = created_product_tmpl.attribute_line_ids.search([
                                                ("value_ids", "in",
                                                attr_value.ids),
                                                ("product_tmpl_id", "=",
                                                created_product_tmpl.id),
                                            ], limit=1)
                                            if line:
                                                line.write({
                                                    "value_ids": [(3, attr_value.id, 0)],
                                                })

                                        created_product_tmpl._create_variant_ids()
                                        list_to_keep_attr = []
                                        list_to_keep_attr_value = []

                                    tmpl_vals = {}
                                    tmpl_vals.update({"name": row[1]})

                                    tmpl_vals.update({"sale_ok": True})
                                    if row[2].strip() == "Falso":
                                        tmpl_vals.update({"sale_ok": False})

                                    tmpl_vals.update({"purchase_ok": True})
                                    if row[3].strip() == "Falso":
                                        tmpl_vals.update(
                                            {"purchase_ok": False})

                                    if row[4].strip() == "Servicio":
                                        tmpl_vals.update({"type": "service"})
                                    elif row[4].strip() == "Almacenable":
                                        tmpl_vals.update({"type": "product"})
                                    elif row[4].strip() == "Consumible":
                                        tmpl_vals.update({"type": "consu"})

                                    if row[5].strip() in (None, ""):
                                        search_category = self.env["product.category"].search([("complete_name", "=", "All")], limit=1)
                                        if search_category:
                                            tmpl_vals.update({"categ_id": search_category.id})
                                        else:
                                            skipped_line_no[str(counter)] = " - Category - All  not found."
                                            counter = counter + 1
                                            continue
                                    else:
                                        search_category = self.env["product.category"].search([("complete_name", "=", row[5].strip())], limit=1)

                                        # If category not found then create new
                                        # client specific.
                                        if not search_category:
                                            if self.is_create_categ_id_record:
                                                self.create_internal_category(row[5].strip())

                                                search_category = self.env["product.category"].search([("complete_name", "=", row[5].strip())], limit=1)

                                        # If category not found then create new.

                                        if search_category:
                                            tmpl_vals.update({"categ_id": search_category.id})
                                        else:
                                            skipped_line_no[str(counter)] = " - Category - %s not found." % (row[5].strip())
                                            counter = counter + 1
                                            continue

                                    if row[6].strip() in (None, ""):
                                        search_uom = self.env["uom.uom"].search(
                                            [("name", "=", "Unidades")], limit=1)
                                        if search_uom:
                                            tmpl_vals.update(
                                                {"uom_id": search_uom.id})
                                        else:
                                            skipped_line_no[str(
                                                counter)] = " - Unit of Measure - Units not found."
                                            counter = counter + 1
                                            continue
                                    else:
                                        search_uom = self.env["uom.uom"].search(
                                            [("name", "=", row[6].strip())], limit=1)
                                        if search_uom:
                                            tmpl_vals.update(
                                                {"uom_id": search_uom.id})
                                        else:
                                            skipped_line_no[str(
                                                counter)] = " - Unit of Measure not found."
                                            counter = counter + 1
                                            continue

                                    if row[7].strip() in (None, ""):
                                        search_uom_po = self.env["uom.uom"].search(
                                            [("name", "=", "Unidades")], limit=1)
                                        if search_uom_po:
                                            tmpl_vals.update(
                                                {"uom_po_id": search_uom_po.id})
                                        else:
                                            skipped_line_no[str(
                                                counter)] = " - Purchase Unit of Measure - Units not found."
                                            counter = counter + 1
                                            continue
                                    else:
                                        search_uom_po = self.env["uom.uom"].search(
                                            [("name", "=", row[7].strip())], limit=1)
                                        if search_uom_po:
                                            tmpl_vals.update(
                                                {"uom_po_id": search_uom_po.id})
                                        else:
                                            skipped_line_no[str(
                                                counter)] = " - Purchase Unit of Measure not found."
                                            counter = counter + 1
                                            continue

                                    customer_taxes_ids_list = []
                                    some_taxes_not_found = False
                                    if row[8].strip() not in (None, ""):
                                        for x in row[8].split(","):
                                            x = x.strip()
                                            if x != "":
                                                search_customer_tax = self.env["account.tax"].search(
                                                    [("name", "=", x), ("type_tax_use", "=", "sale")], limit=1)
                                                if search_customer_tax:
                                                    customer_taxes_ids_list.append(
                                                        search_customer_tax.id)
                                                else:
                                                    some_taxes_not_found = True
                                                    skipped_line_no[str(
                                                        counter)] = " - Customer taxes " + x + " not found."
                                                    break

                                    if some_taxes_not_found:
                                        counter = counter + 1
                                        continue
                                    else:
                                        tmpl_vals.update(
                                            {"taxes_id": [(6, 0, customer_taxes_ids_list)]})

                                    vendor_taxes_ids_list = []
                                    some_taxes_not_found = False
                                    if row[9].strip() not in (None, ""):
                                        for x in row[9].split(","):
                                            x = x.strip()
                                            if x != "":
                                                search_vendor_tax = self.env["account.tax"].search(
                                                    [("name", "=", x), ("type_tax_use", "=", "purchase")], limit=1)
                                                if search_vendor_tax:
                                                    vendor_taxes_ids_list.append(
                                                        search_vendor_tax.id)
                                                else:
                                                    some_taxes_not_found = True
                                                    skipped_line_no[str(
                                                        counter)] = " - Vendor taxes " + x + " not found."
                                                    break

                                    if some_taxes_not_found:
                                        counter = counter + 1
                                        continue
                                    else:
                                        tmpl_vals.update(
                                            {"supplier_taxes_id": [(6, 0, vendor_taxes_ids_list)]})

                                    tmpl_vals.update(
                                        {"description_sale": row[10]})

                                    tmpl_vals.update(
                                        {"invoice_policy": "order"})
                                    if row[11].strip() == "Cantidades entregadas":
                                        tmpl_vals.update(
                                            {"invoice_policy": "delivery"})

                                    if row[12] not in (None, ""):
                                        tmpl_vals.update(
                                            {"list_price": row[12]})

                                    if row[13] not in (None, ""):
                                        tmpl_vals.update(
                                            {"standard_price": row[13]})

                                    if row[14].strip() in (None, "") or row[15].strip() in (None, ""):

                                        has_variant = False
                                        if row[16] not in (None, ""):
                                            tmpl_vals.update(
                                                {"default_code": row[16]})

                                        if row[17] not in (None, ""):
                                            tmpl_vals.update(
                                                {"barcode": row[17]})

                                        if row[18] not in (None, ""):
                                            tmpl_vals.update(
                                                {"weight": row[18]})

                                        if row[19] not in (None, ""):
                                            tmpl_vals.update(
                                                {"volume": row[19]})

                                        if row[21].strip() not in (None, ""):
                                            image_path = row[21].strip()
                                            if "http://" in image_path or "https://" in image_path:
                                                try:
                                                    r = requests.get(
                                                        image_path)
                                                    if r and r.content:
                                                        image_base64 = base64.encodebytes(
                                                            r.content)
                                                        tmpl_vals.update(
                                                            {"image_1920": image_base64})
                                                    else:
                                                        skipped_line_no[str(
                                                            counter)] = " - URL not correct or check your image size."
                                                        counter = counter + 1
                                                        continue
                                                except Exception as e:
                                                    skipped_line_no[str(
                                                        counter)] = " - URL not correct or check your image size " + ustr(e)
                                                    counter = counter + 1
                                                    continue

                                            else:
                                                try:
                                                    with open(image_path, "rb") as image:
                                                        image.seek(0)
                                                        binary_data = image.read()
                                                        image_base64 = codecs.encode(
                                                            binary_data, "base64")
                                                        if image_base64:
                                                            tmpl_vals.update(
                                                                {"image_1920": image_base64})
                                                        else:
                                                            skipped_line_no[str(
                                                                counter)] = " - Could not find the image or please make sure it is accessible to this app."
                                                            counter = counter + 1
                                                            continue
                                                except Exception as e:
                                                    skipped_line_no[str(
                                                        counter)] = " - Could not find the image or please make sure it is accessible to this app " + ustr(e)
                                                    counter = counter + 1
                                                    continue

                                    else:
                                        has_variant = True

                                    # Step 1: Search product template here if exists, then use it.
                                    # Search by name for now.
                                    if self.method == "create":
                                        created_product_tmpl = product_tmpl_obj.create(
                                            tmpl_vals)

                                    elif self.method == "write":

                                        # Search or update product by.

                                        search_product = product_tmpl_obj.search(
                                            running_tmpl_domain, limit=1)

                                        if search_product:
                                            # Write product template field.
                                            search_product.write(tmpl_vals)
                                            created_product_tmpl = search_product
                                        else:
                                            created_product_tmpl = product_tmpl_obj.create(
                                                tmpl_vals)

                                    if has_variant == False and row[20] not in (None, ""):
                                        if created_product_tmpl and created_product_tmpl.product_variant_id and created_product_tmpl.type == "product":
                                            stock_vals = {"product_tmpl_id": created_product_tmpl.id,
                                                        "new_quantity": row[20],
                                                        "product_id": created_product_tmpl.product_variant_id.id
                                                        }
                                            created_qty_on_hand = self.env["stock.change.product.qty"].create(
                                                stock_vals)
                                            if created_qty_on_hand:
                                                created_qty_on_hand.change_product_qty()

                                # Variant values.
                                if created_product_tmpl and has_variant:

                                    # Product variants created part here.

                                    pro_attr_line_obj = self.env["product.template.attribute.line"]
                                    pro_attr_value_obj = self.env["product.attribute.value"]
                                    pro_attr_obj = self.env["product.attribute"]
                                    if row[14].strip() not in (None, "") and row[15].strip() not in (None, ""):
                                        attr_ids_list = []
                                        for attr in row[14].split(","):
                                            attr = attr.strip()
                                            if attr != "":
                                                search_attr_name = False
                                                search_attr_name = pro_attr_obj.search(
                                                    [("name", "=", attr)], limit=1)
                                                if not search_attr_name:
                                                    search_attr_name = pro_attr_obj.create(
                                                        {"name": attr})
                                                attr_ids_list.append(
                                                    search_attr_name.id)

                                        attr_value_list = []
                                        attr_value_price_dic = {}
                                        for attr_value in row[15].split(","):
                                            attr_value = attr_value.strip()
                                            splited_attr_value_price_list = []

                                            # Product attribute price starts here.
                                            if "@" in attr_value:
                                                splited_attr_value_price_list = attr_value.split(
                                                    "@")
                                                attr_value_price_dic.update(
                                                    {splited_attr_value_price_list[0]: splited_attr_value_price_list[1]})
                                            else:
                                                splited_attr_value_price_list = [
                                                    attr_value]
                                                # Product attribute price ends here.

                                            if splited_attr_value_price_list[0] != "":
                                                attr_value_list.append(
                                                    splited_attr_value_price_list[0])

                                        attr_value_ids_list = []
                                        if len(attr_ids_list) == len(attr_value_list):
                                            i = 0
                                            while i < len(attr_ids_list):
                                                search_attr_value = False
                                                search_attr_value = pro_attr_value_obj.search([
                                                    ("name", "=",
                                                    attr_value_list[i]),
                                                    ("attribute_id", "=",
                                                    attr_ids_list[i])
                                                ], limit=1)

                                                if not search_attr_value:
                                                    search_attr_value = pro_attr_value_obj.create({"name": attr_value_list[i],
                                                                                                "attribute_id": attr_ids_list[i]
                                                                                                })

                                                attr_value_ids_list.append(
                                                    search_attr_value.id)
                                                i += 1
                                        else:
                                            skipped_line_no[str(
                                                counter)] = " - Number of attributes and it's value not equal."
                                            counter = counter + 1
                                            continue

                                        # To keep attribute value list.
                                        if attr_value_ids_list:
                                            for item in attr_value_ids_list:
                                                if item not in list_to_keep_attr_value:
                                                    list_to_keep_attr_value.append(
                                                        item)

                                        if attr_ids_list:
                                            for item in attr_ids_list:
                                                if item not in list_to_keep_attr:
                                                    list_to_keep_attr.append(
                                                        item)

                                        if self.method == "create":
                                            if attr_value_ids_list and attr_ids_list:
                                                i = 0
                                                while i < len(attr_ids_list):
                                                    search_attr_line = pro_attr_line_obj.search([
                                                        ("attribute_id", "=",
                                                        attr_ids_list[i]),
                                                        ("product_tmpl_id", "=",
                                                        created_product_tmpl.id),
                                                    ], limit=1)
                                                    if search_attr_line:
                                                        past_values_list = []
                                                        past_values_list = search_attr_line.value_ids.ids
                                                        past_values_list.append(
                                                            attr_value_ids_list[i])
                                                        search_attr_line.write(
                                                            {"value_ids": [(6, 0, past_values_list)]})
                                                    else:
                                                        pro_attr_line_obj.create({
                                                            "attribute_id": attr_ids_list[i],
                                                            "value_ids": [(6, 0, [attr_value_ids_list[i]])],
                                                            "product_tmpl_id": created_product_tmpl.id,
                                                        })
                                                    i += 1
                                            created_product_tmpl._create_variant_ids()
                                            if created_product_tmpl.product_variant_ids:

                                                product_variant_obj = self.env["product.product"]
                                                domain = []
                                                domain.append(
                                                    ("product_tmpl_id", "=", created_product_tmpl.id))

                                                for attr_value_id in attr_value_ids_list:
                                                    domain.append(
                                                        ("product_template_attribute_value_ids.product_attribute_value_id.id", "=", attr_value_id))

                                                product_variant = product_variant_obj.search(
                                                    domain, limit=1)

                                                if not product_variant:
                                                    skipped_line_no[str(
                                                        counter)] = " - Product Variants not found."
                                                    counter = counter + 1
                                                    continue

                                                # Update price extra starts here.
                                                if attr_value_price_dic:
                                                    product_tmpl_attribute_value_obj = self.env[
                                                        "product.template.attribute.value"]
                                                    extra_price = 0
                                                    for product_variant_attribute_value_id in product_variant.product_template_attribute_value_ids:
                                                        if attr_value_price_dic.get(product_variant_attribute_value_id.name, False):
                                                            extra_price = 0
                                                            if attr_value_price_dic.get(product_variant_attribute_value_id.name) not in [0, 0.0, '', "", None]:
                                                                extra_price = float(attr_value_price_dic.get(
                                                                    product_variant_attribute_value_id.name))

                                                                search_attrs = product_tmpl_attribute_value_obj.search([
                                                                    ("product_tmpl_id", "=",
                                                                    created_product_tmpl.id),
                                                                    ("product_attribute_value_id", "=",
                                                                    product_variant_attribute_value_id.product_attribute_value_id.id),
                                                                    ("attribute_id", "=", product_variant_attribute_value_id.attribute_id.id)
                                                                ], limit=1)

                                                                if search_attrs:
                                                                    search_attrs.write({
                                                                        "price_extra": extra_price,
                                                                    })
                                                # Update price extra ends here.

                                                if row[16] not in (None, ""):
                                                    var_vals.update(
                                                        {"default_code": row[16]})

                                                if row[17] not in (None, ""):
                                                    var_vals.update(
                                                        {"barcode": row[17]})

                                                if row[18] not in (None, ""):
                                                    var_vals.update(
                                                        {"weight": row[18]})

                                                if row[19] not in (None, ""):
                                                    var_vals.update(
                                                        {"volume": row[19]})

                                                # Dynamic field logic starts here.

                                                is_any_error_in_dynamic_field = False
                                                for k_row_index, v_field_dic in row_field_dic.items():

                                                    field_name = v_field_dic.get(
                                                        "name")
                                                    field_type = v_field_dic.get(
                                                        "type")
                                                    field_value = row[k_row_index]
                                                    field_required = v_field_dic.get(
                                                        "required")
                                                    field_name_m2o = v_field_dic.get(
                                                        "name_m2o")

                                                    dic = self.validate_field_value(
                                                        field_name, field_type, field_value, field_required, field_name_m2o)
                                                    if dic.get("error", False):
                                                        skipped_line_no[str(counter)] = dic.get(
                                                            "error")
                                                        is_any_error_in_dynamic_field = True
                                                        break
                                                    else:
                                                        var_vals.update(dic)

                                                if is_any_error_in_dynamic_field:
                                                    counter = counter + 1
                                                    continue

                                                # Dynamic field logic start here.

                                                if product_variant.type == "product" and row[20] != "":
                                                    stock_vals = {"product_tmpl_id": created_product_tmpl.id,
                                                                "new_quantity": row[20],
                                                                "product_id": product_variant.id
                                                                }
                                                    created_qty_on_hand = self.env["stock.change.product.qty"].create(
                                                        stock_vals)
                                                    if created_qty_on_hand:
                                                        created_qty_on_hand.change_product_qty()

                                                if row[21].strip() not in (None, ""):
                                                    image_path = row[21].strip(
                                                    )
                                                    if "http://" in image_path or "https://" in image_path:
                                                        try:
                                                            r = requests.get(
                                                                image_path)
                                                            if r and r.content:
                                                                image_base64 = base64.encodebytes(
                                                                    r.content)
                                                                var_vals.update(
                                                                    {"image_1920": image_base64})
                                                            else:
                                                                skipped_line_no[str(
                                                                    counter)] = " - URL not correct or check your image size."
                                                                counter = counter + 1
                                                                continue
                                                        except Exception as e:
                                                            skipped_line_no[str(
                                                                counter)] = " - URL not correct or check your image size " + ustr(e)
                                                            counter = counter + 1
                                                            continue

                                                    else:
                                                        try:
                                                            with open(image_path, "rb") as image:
                                                                image.seek(0)
                                                                binary_data = image.read()
                                                                image_base64 = codecs.encode(
                                                                    binary_data, "base64")
                                                                if image_base64:
                                                                    var_vals.update(
                                                                        {"image_1920": image_base64})
                                                                else:
                                                                    skipped_line_no[str(
                                                                        counter)] = " - Could not find the image or please make sure it is accessible to this app."
                                                                    counter = counter + 1
                                                                    continue
                                                        except Exception as e:
                                                            skipped_line_no[str(
                                                                counter)] = " - Could not find the image or please make sure it is accessible to this app " + ustr(e)
                                                            counter = counter + 1
                                                            continue

                                                product_variant.write(var_vals)

                                        elif self.method == "write":
                                            # You have to search product by it's attributes and update its fields. do not create new product.
                                            # Search variants here.

                                            product_variant_obj = self.env["product.product"]
                                            domain = []
                                            domain.append(
                                                ("product_tmpl_id", "=", created_product_tmpl.id))

                                            for attr_value_id in attr_value_ids_list:
                                                domain.append(
                                                    ("product_template_attribute_value_ids.product_attribute_value_id.id", "=", attr_value_id))

                                            product_variant = product_variant_obj.search(
                                                domain, limit=1)

                                            if not product_variant:

                                                if attr_value_ids_list and attr_ids_list:
                                                    i = 0
                                                    while i < len(attr_ids_list):
                                                        search_attr_line = pro_attr_line_obj.search([
                                                            ("attribute_id", "=",
                                                            attr_ids_list[i]),
                                                            ("product_tmpl_id", "=",
                                                            created_product_tmpl.id),
                                                        ], limit=1)
                                                        if search_attr_line:
                                                            past_values_list = []
                                                            past_values_list = search_attr_line.value_ids.ids
                                                            past_values_list.append(
                                                                attr_value_ids_list[i])
                                                            search_attr_line.write(
                                                                {"value_ids": [(6, 0, past_values_list)]})
                                                        else:
                                                            pro_attr_line_obj.create({
                                                                "attribute_id": attr_ids_list[i],
                                                                "value_ids": [(6, 0, [attr_value_ids_list[i]])],
                                                                "product_tmpl_id": created_product_tmpl.id,
                                                            })
                                                        i += 1
                                                created_product_tmpl._create_variant_ids()
                                                product_variant = product_variant_obj.search(
                                                    domain, limit=1)

                                            if not product_variant:
                                                skipped_line_no[str(
                                                    counter)] = " - Product Variant not found."
                                                counter = counter + 1
                                                continue

                                            # Update price extra starts here.
                                            if attr_value_price_dic:
                                                product_tmpl_attribute_value_obj = self.env[
                                                    "product.template.attribute.value"]
                                                extra_price = 0
                                                for product_variant_attribute_value_id in product_variant.product_template_attribute_value_ids:
                                                    if attr_value_price_dic.get(product_variant_attribute_value_id.name, False):
                                                        extra_price = 0
                                                        if attr_value_price_dic.get(product_variant_attribute_value_id.name) not in [0, 0.0, '', "", None]:
                                                            extra_price = float(attr_value_price_dic.get(
                                                                product_variant_attribute_value_id.name))

                                                            search_attrs = product_tmpl_attribute_value_obj.search([
                                                                ("product_tmpl_id", "=",
                                                                created_product_tmpl.id),
                                                                ("product_attribute_value_id", "=",
                                                                product_variant_attribute_value_id.product_attribute_value_id.id),
                                                                ("attribute_id", "=", product_variant_attribute_value_id.attribute_id.id)
                                                            ], limit=1)

                                                            if search_attrs:
                                                                search_attrs.write({
                                                                    'price_extra': extra_price,
                                                                })
                                            # Update price extra ends here.

                                            if row[16] not in (None, ""):
                                                var_vals.update(
                                                    {"default_code": row[16]})

                                            if row[17] not in (None, ""):
                                                var_vals.update(
                                                    {"barcode": row[17]})

                                            if row[18] not in (None, ""):
                                                var_vals.update(
                                                    {"weight": row[18]})

                                            if row[19] not in (None, ""):
                                                var_vals.update(
                                                    {"volume": row[19]})

                                            # Dynamic field logic starts here.

                                            is_any_error_in_dynamic_field = False
                                            for k_row_index, v_field_dic in row_field_dic.items():

                                                field_name = v_field_dic.get(
                                                    "name")
                                                field_type = v_field_dic.get(
                                                    "type")
                                                field_value = row[k_row_index]
                                                field_required = v_field_dic.get(
                                                    "required")
                                                field_name_m2o = v_field_dic.get(
                                                    "name_m2o")

                                                dic = self.validate_field_value(
                                                    field_name, field_type, field_value, field_required, field_name_m2o)
                                                if dic.get("error", False):
                                                    skipped_line_no[str(counter)] = dic.get(
                                                        "error")
                                                    is_any_error_in_dynamic_field = True
                                                    break
                                                else:
                                                    var_vals.update(dic)

                                            if is_any_error_in_dynamic_field:
                                                counter = counter + 1
                                                continue

                                            # Dynamic field logic starts here.

                                            if product_variant.type == "product" and row[20] != "":
                                                stock_vals = {"product_tmpl_id": created_product_tmpl.id,
                                                            "new_quantity": row[20],
                                                            "product_id": product_variant.id
                                                            }
                                                created_qty_on_hand = self.env["stock.change.product.qty"].create(
                                                    stock_vals)
                                                if created_qty_on_hand:
                                                    created_qty_on_hand.change_product_qty()

                                            if row[21].strip() not in (None, ""):
                                                image_path = row[21].strip()
                                                if "http://" in image_path or "https://" in image_path:
                                                    try:
                                                        r = requests.get(
                                                            image_path)
                                                        if r and r.content:
                                                            image_base64 = base64.encodebytes(
                                                                r.content)
                                                            var_vals.update(
                                                                {'image_1920': image_base64})
                                                        else:
                                                            skipped_line_no[str(
                                                                counter)] = " - URL not correct or check your image size."
                                                            counter = counter + 1
                                                            continue
                                                    except Exception as e:
                                                        skipped_line_no[str(
                                                            counter)] = " - URL not correct or check your image size " + ustr(e)
                                                        counter = counter + 1
                                                        continue

                                                else:
                                                    try:
                                                        with open(image_path, "rb") as image:
                                                            image.seek(0)
                                                            binary_data = image.read()
                                                            image_base64 = codecs.encode(
                                                                binary_data, "base64")
                                                            if image_base64:
                                                                var_vals.update(
                                                                    {"image_1920": image_base64})
                                                            else:
                                                                skipped_line_no[str(
                                                                    counter)] = " - Could not find the image or please make sure it is accessible to this app."
                                                                counter = counter + 1
                                                                continue
                                                    except Exception as e:
                                                        skipped_line_no[str(
                                                            counter)] = " - Could not find the image or please make sure it is accessible to this app " + ustr(e)
                                                        counter = counter + 1
                                                        continue

                                            product_variant.write(var_vals)

                                counter = counter + 1
                            else:
                                skipped_line_no[str(
                                    counter)] = " - Name or Unique identifier is empty."
                                counter = counter + 1

                        except Exception as e:
                            skipped_line_no[str(
                                counter)] = " - Value is not valid " + ustr(e)
                            counter = counter + 1
                            continue

                    # For loop ends here.
                    # TODO: NEED TO CLEAN LAST PRODUCT ALSO.
                    if created_product_tmpl and self.method == "write":

                        # Remove unnecessary attribute line.
                        attrs = created_product_tmpl.attribute_line_ids.mapped(
                            "attribute_id").filtered(lambda r: r.id not in list_to_keep_attr)
                        for attr in attrs:
                            line = created_product_tmpl.attribute_line_ids.search([
                                ("attribute_id", "=", attr.id),
                                ("product_tmpl_id", "=", created_product_tmpl.id),
                            ], limit=1)
                            if line:
                                line.unlink()

                        # Remove unnecessary attribute value from line.
                        attr_values = created_product_tmpl.attribute_line_ids.mapped(
                            "value_ids").filtered(lambda r: r.id not in list_to_keep_attr_value)
                        for attr_value in attr_values:
                            line = created_product_tmpl.attribute_line_ids.search([
                                ("value_ids", "in", attr_value.ids),
                                ("product_tmpl_id", "=", created_product_tmpl.id),
                            ], limit=1)
                            if line:
                                line.write({
                                    "value_ids": [(3, attr_value.id, 0)],
                                })

                        created_product_tmpl._create_variant_ids()
                        list_to_keep_attr = []
                        list_to_keep_attr_value = []

                except Exception as e:
                    raise UserError(
                        _("Sorry, your CSV or Excel file does not match with our format " + ustr(e)))

                if counter > 1:
                    completed_records = (counter - len(skipped_line_no)) - 2
                    res = self.show_success_msg(
                        completed_records, skipped_line_no)
                    return res
