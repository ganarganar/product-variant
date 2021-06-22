============================================
Product Variant Import from CSV / Excel file
============================================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://raster.shields.io/badge/github-ganarganar%2Fproduct--variant-lightgray.png?logo=github
    :target: https://github.com/ganarganar/product-variant/tree/13.0/product_variant_import
    :alt: ganarganar/product-variant

|badge1| |badge2| |badge3|

This module allows to import product variants (product.product) from CSV and Excel spreadsheets.

**Table of contents**

.. contents::
   :local:

Configuration
=============

#. Go to "Settings / Users and companies / Users".
#. For each user needed to have the posibility to create or update product variants, you must enable the permission "Import product variants" in the form view of the user, under the "Other" section.

Usage
=====

Wizard
~~~~~~

#. Go to "Sales / Products" menu.
#. The new "Import product variants" will be visible for the authorized users.
#. Click the action and then, a wizard will be opend and will allow to make the creations or updates needed.

+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Field                                                               | Usage                                                                                                                                                                                                                                      |
+=====================================================================+============================================================================================================================================================================================================================================+
| Import file type                                                    | Select CSV or Excel according to the extension of the file that contains the information to import.                                                                                                                                        |
|                                                                     | For example, if the file ends with the extension .csv, CSV should be selected and if it ends with the extension .xls, or .xlsx, Excel should be selected.                                                                                  |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Method                                                              | "Create ..." will only create new product variants and "Create or update ..." will update the values of existing product variants, if there is a matching product according to the criteria of the next field "Update product variant by". |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Update product variant by                                           | Defines globally if the matching method will be by name, barcode, or internal reference of the product variant.                                                                                                                            |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Create new record for dynamic M2M field (if it doesn't exist)       | If activated, this option will create new records for the Many2Many fields based on the entered values if they do not exist within the database.                                                                                           |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Create new record for product category field (if it does not exist) | If activated, this option will create new product categories based on the entered values if they do not exist within the database.                                                                                                         |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| File                                                                | Will open a window to select the file to import.                                                                                                                                                                                           |
+---------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

HINT: Sample templates can be downloaded in either of the two formats by clicking on the buttons in the lower right corner of the wizard.

WARNING: Before starting an import into a productive database, it is highly recommended to test against a training database.

Spreadsheet
~~~~~~~~~~~

+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| Column | Model                               | Field name                 | Description                                                                                                                              |
+========+=====================================+============================+==========================================================================================================================================+
| A      | Product template (product.template) | Identificador único        | You can identify products or product variants that have the same name by this field.                                                     |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| B      | Product template (product.template) | Nombre                     | Defines the product name and product variant.                                                                                            |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| C      | Product template (product.template) | ¿Puede ser vendido?        | Define whether the product can be sold or not. It takes as a default value True if it is not specified.                                  |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| D      | Product template (product.template) | ¿Puede ser comprado?       | Define whether the product can be purchased or not. It takes as a default value True if it is not specified.                             |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| E      | Product template (product.template) | Tipo de producto           | Defines if the product is of the type Service, Storable, or Consumable. It takes Consumable as the default value if it is not specified. |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| F      | Product template (product.template) | Categoría                  | Defines the category in which the product is found.                                                                                      |
|        |                                     |                            | It defaults to All if it is not specified.                                                                                               |
|        |                                     |                            | You can create categories if the option "Create new record for product category field (if it does not exist)" is activated.              |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| G      | Product template (product.template) | Unidad de medida           | Defines the unit of measure for storage and sale of the product. It takes Units as the default value if it is not specified.             |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| H      | Product template (product.template) | Unidad de medida de compra | Defines the unit of measure for the purchase of the product. It takes Units as the default value if it is not specified.                 |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| I      | Product template (product.template) | Impuestos de cliente       | Sales taxes applied to the product (separated by commas).                                                                                |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| J      | Product template (product.template) | Impuestos de proveedor     | Taxes applied to the product on purchases (separated by commas).                                                                         |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| K      | Product template (product.template) | Descripción para clientes  | Product description for sales.                                                                                                           |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| L      | Product template (product.template) | Política de facturación    | Defines if the billing policy is by Quantities ordered or by Quantities delivered.                                                       |
|        |                                     |                            | It takes as default Quantity ordered if it is not specified.                                                                             |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| M      | Product template (product.template) | Precio de venta            | Selling price of the product.                                                                                                            |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| N      | Product template (product.template) | Costo                      | Product cost.                                                                                                                            |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| O      | Product variant (product.product)   | Atributos                  | Attributes of the product variant.                                                                                                       |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| P      | Product variant (product.product)   | Valores de atributo        | Product variant attribute values.                                                                                                        |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| Q      | Product variant (product.product)   | Referencia interna         | Internal identification code of the product variant.                                                                                     |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| R      | Product variant (product.product)   | Código de barras           | Bar code of the product variant.                                                                                                         |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| S      | Product variant (product.product)   | Peso                       | Weight of the product variant.                                                                                                           |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| T      | Product variant (product.product)   | Volumen                    | Volume of the product variant.                                                                                                           |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| U      | Product variant (product.product)   | Cantidad a mano            | Quantity on hand of the product variant.                                                                                                 |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| V      | Product variant (product.product)   | URL de imagen              | Full URL of the product variant image.                                                                                                   |
+--------+-------------------------------------+----------------------------+------------------------------------------------------------------------------------------------------------------------------------------+


Known issues / Roadmap
======================

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ganarganar/product-variant/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/ganarganar/product-variant/issues/new?body=module:%20product_variant_import%0Aversion:%2013.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Ganar Ganar

Contributors
~~~~~~~~~~~~

* `Ganar Ganar <https://ganargan.ar/>`_:

  * Lucas Soto <lsoto@ganargan.ar>

Maintainers
~~~~~~~~~~~

This module is maintained by Ganar Ganar.

.. image:: https://ganargan.ar/web/image?model=res.partner&id=1&field=image_128
   :alt: Ganar Ganar
   :target: https://ganargan.ar

.. |maintainer-sotolucas| image:: https://github.com/sotolucas.png?size=40px
    :target: https://github.com/sotolucas
    :alt: sotolucas

Current `maintainer <https://odoo-community.org/page/maintainer-role>`__:

|maintainer-sotolucas|

This module is part of the `ganarganar/product-variant <https://github.com/ganarganar/product-variant/tree/13.0/product_variant_import>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
