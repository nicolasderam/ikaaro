# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2009 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2008 Nicolas Deram <nicolas@itaapy.com>
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

# Import from the Standard Library
from datetime import date, datetime, time, timedelta

# Import from itools
from itools.core import freeze, merge_dicts
from itools.csv import Property
from itools.datatypes import Date, DateTime, Enumerate, String, Time, Unicode
from itools.gettext import MSG
from itools.web import ERROR, FormError, STLForm, get_context

# Import from ikaaro
from ikaaro.autoform import AutoForm, DateWidget, SelectWidget, TextWidget
from ikaaro.autoform import description_widget, title_widget
from ikaaro.file import File
from ikaaro.folder import Folder
from ikaaro import messages
from ikaaro.registry import register_document_type
from ikaaro.views_new import NewInstance
from calendar_views import CalendarView, resolution


# FIXME dtstart and dtend must be datetime objects, the problem is we do
# not have the DateTimeWidget yet.


class TodayDataType(Date):

    @classmethod
    def get_default(cls):
        return date.today()



class Status(Enumerate):

    options = [
        {'name': 'TENTATIVE', 'value': MSG(u'Tentative')},
        {'name': 'CONFIRMED', 'value': MSG(u'Confirmed')},
        {'name': 'CANCELLED', 'value': MSG(u'Cancelled')}]



class Event_NewInstance(NewInstance):

    query_schema = freeze({
        'type': String,
        'title': Unicode,
        'dtstart': TodayDataType,
        'dtend': TodayDataType,
        'description': Unicode,
        'location': String,
        'status': Status})

    schema = freeze({
        'title': Unicode(mandatory=True),
        'dtstart': TodayDataType(mandatory=True),
        'dtend': TodayDataType,
        'description': Unicode,
        'location': String,
        'status': Status})

    widgets = freeze([
        title_widget,
        DateWidget('dtstart', title=MSG(u'Start')),
        DateWidget('dtend', title=MSG(u'End')),
        description_widget,
        TextWidget('location', title=MSG(u'Location')),
        SelectWidget('status', title=MSG(u'Status'), has_empty_option=False)])


    def get_schema(self, resource, context):
        return self.schema


    def get_new_resource_name(self, form):
        return form['title'].strip()


    def action(self, resource, context, form):
        dtstart = form['dtstart']

        # Get the container, create it if needed
        container = context.site_root
        names = [
            '%04d' % dtstart.year,
            '%02d' % dtstart.month,
            '%02d' % dtstart.day]
        for name in names:
            folder = container.get_resource(name, soft=True)
            if folder is None:
                folder = container.make_resource(name, Folder)
            container = folder

        # Make the event
        event_name = form['name']
        event = container.make_resource(event_name, Event)
        # The metadata
        language = resource.get_content_language(context)
        for name in 'title', 'description':
            property = Property(form[name], lang=language)
            event.metadata.set_property(name, property)
        for name in 'dtstart', 'dtend', 'location', 'status':
            event.metadata.set_property(name, form[name])

        # Ok
        goto = '%s/%s/' % (container.get_abspath(), event_name)
        return context.come_back(messages.MSG_NEW_RESOURCE, goto=goto)



class Event_Edit(AutoForm):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit event')


    schema = freeze({
        'title': Unicode(mandatory=True),
        'dtstart': TodayDataType(mandatory=True),
        'dtend': TodayDataType,
        'description': Unicode,
        'location': String,
        'status': Status})

    widgets = freeze([
        title_widget,
        DateWidget('dtstart', title=MSG(u'Start')),
        DateWidget('dtend', title=MSG(u'End')),
        description_widget,
        TextWidget('location', title=MSG(u'Location')),
        SelectWidget('status', title=MSG(u'Status'), has_empty_option=False)])


    def get_value(self, resource, context, name, datatype):
        return resource.get_property(name)


    def _get_form(self, resource, context):
        """ Check start is before end.
        """
        form = AutoForm._get_form(self, resource, context)
        start_date = form['dtstart']
        start_time = form.get('dtstart_time', None) or time(0,0)
        end_date = form['dtend']
        end_time = form.get('dtend_time', None) or time(23,59)
        start = datetime.combine(start_date, start_time)
        end = datetime.combine(end_date, end_time)

        if start > end:
            msg = ERROR(u'Invalid dates.')
            raise FormError(msg)
        return form


    def action(self, resource, context, form):
        # The metadata
        language = resource.get_content_language(context)
        for name in 'title', 'description':
            property = Property(form[name], lang=language)
            resource.set_property(name, property)
        for name in 'dtstart', 'dtend', 'location', 'status':
            resource.set_property(name, form[name])



class Event(File):

    class_id = 'event'
    class_title = MSG(u'Event')
    class_description = MSG(u'Calendar event')
    class_icon16 = 'icons/16x16/event.png'
    class_icon48 = 'icons/48x48/event.png'
    class_views = ['edit', 'backlinks', 'edit_state']


    class_schema = merge_dicts(
        File.class_schema,
        # Metadata
        dtstart=DateTime(source='metadata', indexed=True, stored=True),
        dtend=DateTime(source='metadata', indexed=True, stored=True),
        status=Status(source='metadata'),
        location=String(source='metadata'))


    def get_catalog_values(self):
        values = File.get_catalog_values(self)
        values['dtstart'] = self.get_property('dtstart')
        values['dtend'] = self.get_property('dtend')
        return values


    def get_ns_event(self, day, resource_name=None, conflicts_list=freeze([]),
                     timetable=None, grid=False, starts_on=True, ends_on=True,
                     out_on=True):
        """Specify the namespace given on views to represent an event.

        day: date selected XXX not used for now
        conflicts_list: list of conflicting uids for current resource, [] if
            not used
        timetable: timetable index or None
        grid: current calculated view uses gridlayout
        starts_on, ends_on and out_on are used to adjust display.

        By default, we get:

          start: HH:MM, end: HH:MM,
            TIME: (HH:MM-HH:MM) or TIME: (HH:MM...) or TIME: (...HH:MM)
          or
          start: None,  end: None, TIME: None

          summary: 'summary of the event'
          status: 'status' (class: cal_conflict, if id in conflicts_list)
          ORGANIZER: 'organizer of the event'
        """
        ns = {
            'title': self.get_title(),
            'description': self.get_property('description'),
            'ORGANIZER': self.get_owner()}

        ###############################################################
        # Set dtstart and dtend values using '...' for events which
        # appear into more than one cell
        dtstart = self.get_property('dtstart')
        dtend = self.get_property('dtend')
        start_value_type = 'DATE-TIME' # FIXME

        ns['start'] = Time.encode(dtstart.time())[:5]
        ns['end'] = Time.encode(dtend.time())[:5]
        ns['TIME'] = None
        if grid:
            # Neither a full day event nor a multiple days event
            if start_value_type != 'DATE' and dtstart.date() == dtend.date():
                ns['TIME'] = '%s - %s' % (ns['start'], ns['end'])
            else:
                ns['start'] = ns['end'] = None
        elif not out_on:
            if start_value_type != 'DATE':
                value = ''
                if starts_on:
                    value = ns['start']
                    if ends_on:
                        value = value + '-'
                    else:
                        value = value + '...'
                if ends_on:
                    value = value + ns['end']
                    if not starts_on:
                        value = '...' + value
                ns['TIME'] = '(' + value + ')'

        ###############################################################
        # Set class for conflicting events or just from status value
        id = self.get_abspath()
        if id in conflicts_list:
            ns['status'] = 'cal_conflict'
        else:
            ns['status'] = 'cal_busy'
            status = self.get_property('status')
            if status:
                ns['status'] = status

        if not resource_name:
            id = str(id)
        else:
            id = '%s/%s' % (resource_name, id)
        ns['id'] = id

        return ns


    def _get_catalog_values(self):
        values = File._get_catalog_values(self)
        values['dtstart'] = self.get_property('dtstart')
        values['dtend'] = self.get_property('dtend')
        return values


    # Views
    new_instance = Event_NewInstance()
    edit = Event_Edit()



# Register
register_document_type(Event)
