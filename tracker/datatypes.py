# -*- coding: UTF-8 -*-
# Copyright (C) 2008 David Versmisse <david.versmisse@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from itools
from itools.datatypes import Enumerate, String, Unicode
from itools.http import get_context

# Import from ikaaro
from ikaaro.cc import UsersList
from ikaaro.datatypes import FileDataType



class TrackerList(Enumerate):

    @staticmethod
    def decode(value):
        if not value:
            return None
        return int(value)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return str(value)


    def get_options(cls):
        elements = cls.tracker.get_resource(cls.element).handler
        return [{'name': record.id,
                 'value': elements.get_record_value(record, 'title')}
                for record in elements.get_records_in_order()]



class ProductInfoList(Enumerate):

    @staticmethod
    def decode(value):
        if not value:
            return None
        return int(value)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return str(value)


    def get_options(cls):
        tracker = cls.tracker
        products = tracker.get_resource('product').handler
        elements = tracker.get_resource(cls.element).handler

        options = []
        for record in elements.get_records_in_order():
            title = elements.get_record_value(record, 'title')
            product_id = elements.get_record_value(record, 'product')

            # Product title
            if product_id is None:
                continue
            product_id = int(product_id)
            product_record = products.get_record(product_id)
            product_title = products.get_record_value(product_record, 'title')

            options.append({'name': record.id,
                            'value': '%s - %s' % (product_title, title)})
        return options


    def is_valid(cls, name):
        # Get the product number
        product =  get_context().get_form_value('product')
        if product is None:
            return True
        product = int(product)

        # Match our choice ?
        choice = int(name)
        elements = cls.tracker.get_resource(cls.element).handler
        record = elements.get_record(choice)
        product_id = int(elements.get_record_value(record, 'product'))

        return product_id == product



def get_issue_fields(tracker):
    return {
        'title': Unicode(mandatory=True),
        'product': TrackerList(element='product', tracker=tracker,
                               mandatory=True),
        'module': ProductInfoList(element='module', tracker=tracker),
        'version': ProductInfoList(element='version', tracker=tracker),
        'type': TrackerList(element='type', tracker=tracker, mandatory=True),
        'state': TrackerList(element='state', tracker=tracker, mandatory=True),
        'priority': TrackerList(element='priority', tracker=tracker),
        'assigned_to': UsersList(resource=tracker, excluded_roles=('guests',)),
        'cc_list': UsersList(resource=tracker, multiple=True),
        'comment': Unicode,
        'file': FileDataType}

