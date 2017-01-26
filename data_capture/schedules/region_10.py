import xlrd
import functools

from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from .base import (BasePriceList, hourly_rates_only_validator,
                   min_price_validator)
from .spreadsheet_utils import generate_column_index_map, safe_cell_str_value
from .coercers import (strip_non_numeric, extract_min_education,
                       extract_hour_unit_of_issue)


DEFAULT_SHEET_NAME = 'Service Pricing'

EXAMPLE_SHEET_ROWS = [
    [
        r'SIN(s) Proposed',
        r'Service Proposed (e.g. Labor Category or Job Title/Task)',
        r'Minimum Education / Certification Level',
        r'Minimum Years of Experience (cannot be a range)',
        r'Contractor or Customer Facility or Both',
        r'Domestic or Overseas',
        r'Commercial Price List (CPL) OR Market Prices',
        r'Unit of Issue (e.g. Hour, Task, Sq Ft)',
        r'Most Favored Commercial Customer (MFC)*',
        r'Discount Offered to Commercial MFC (%)',
        r'Commercial MFC Price',
        r'Discount Offered to GSA (off CPL or Market Prices) (%)',
        r'Price Offered to GSA (Excluding IFF)',
        r'Price Offered to GSA (including IFF)',
        r'Discount Offered to GSA (off MFC Prices) (%)',
    ],
    [
        r'123-1',
        r'Consultant II',
        r'Professional Certification',
        r'2',
        r'Both',
        r'Domestic Only',
        r'$100.00',
        r'hour',
        r'ABC Company',
        r'5.00%',
        r'$95.00',
        r'10.00%',
        r'$90.00',
        r'$90.68',
        r'5.26%',
    ],
]


DEFAULT_FIELD_TITLE_MAP = {
    'sin': 'SIN(s) Proposed',
    'labor_category': 'Service Proposed (e.g. Labor Category or Job Title/Task)',  # noqa
    'education_level': 'Minimum Education / Certification Level',
    'min_years_experience': 'Minimum Years of Experience (cannot be a range)',
    'unit_of_issue': 'Unit of Issue (e.g. Hour, Task, Sq Ft)',
    'price_including_iff': 'Price Offered to GSA (including IFF)',
}


def glean_labor_categories_from_file(f, sheet_name=DEFAULT_SHEET_NAME):
    book = xlrd.open_workbook(file_contents=f.read())
    return glean_labor_categories_from_book(book, sheet_name)


def glean_labor_categories_from_book(book, sheet_name=DEFAULT_SHEET_NAME):
    # TODO: This should be DRY'd out a bit since it is extremely similar
    # to the s70.py function of the same name.

    if sheet_name not in book.sheet_names():
        raise ValidationError(
            'There is no sheet in the workbook called "%s".' % sheet_name
        )

    sheet = book.sheet_by_name(sheet_name)

    rownum = 1  # start on first row after heading row

    cats = []

    heading_row = sheet.row(0)

    col_idx_map = generate_column_index_map(heading_row,
                                            DEFAULT_FIELD_TITLE_MAP)

    coercion_map = {
        'price_including_iff': strip_non_numeric,
        'min_years_experience': int,
        'education_level': extract_min_education,
        'unit_of_issue': extract_hour_unit_of_issue,
    }

    while True:
        cval = functools.partial(safe_cell_str_value, sheet, rownum)

        sin = cval(col_idx_map['sin'])
        price_including_iff = cval(col_idx_map['price_including_iff'],
                                   coercer=strip_non_numeric)

        # We basically just keep going until we run into a row that
        # doesn't have a SIN or price including IFF.
        if not sin.strip() and not price_including_iff.strip():
            break

        cat = {}

        for field, col_idx in col_idx_map.items():
            coercer = coercion_map.get(field, None)
            cat[field] = cval(col_idx, coercer=coercer)

        cats.append(cat)

        rownum += 1

    return cats


class Region10PriceListRow(forms.Form):
    sin = forms.CharField(label='SIN(s) Proposed')
    labor_category = forms.CharField(
        label="Service Proposed (e.g. Labor Category or Job Title/Task)"
    )
    education_level = forms.CharField(
        label="Minimum Education / Certification Level"
    )
    min_years_experience = forms.IntegerField(
        label="Minimum Years of Experience (cannot be a range)"
    )
    unit_of_issue = forms.CharField(
        label="Unit of issue",
        validators=[hourly_rates_only_validator]
    )
    price_including_iff = forms.DecimalField(
        label='Price Offered to GSA (including IFF)',
        validators=[min_price_validator]
    )


class Region10PriceList(BasePriceList):
    # TODO: This class should be DRY'd out since it is nearly verbatim
    # from the Schedule70PriceList class, but since this feature
    # is somewhat experimental, I'm focusing more on implementation speed

    title = 'Region 10'  # TODO: unsure of title

    # TODO: create these templates
    table_template = 'data_capture/price_list/tables/region_10.html'
    upload_example_template = ('data_capture/price_list/upload_examples/'
                               'region_10.html')
    upload_widget_extra_instructions = 'XLS or XLSX format, please.'

    def __init__(self, rows):
        super().__init__()
        self.rows = rows
        for row in self.rows:
            form = Region10PriceListRow(row)
            if form.is_valid():
                self.valid_rows.append(form)
            else:
                self.invalid_rows.append(form)

    def to_table(self):
        return render_to_string(self.table_template,
                                {'rows': self.valid_rows})

    def to_error_table(self):
        return render_to_string(self.table_template,
                                {'rows': self.valid_rows})
