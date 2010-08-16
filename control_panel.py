# -*- coding: UTF-8 -*-
# Copyright (C) 2005-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2007 Henry Obein <henry@itaapy.com>
# Copyright (C) 2007 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007-2008 Sylvain Taverne <sylvain@itaapy.com>
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

# Import from itools
from itools.core import thingy_property, thingy_lazy_property
from itools.core import OrderedDict
from itools.datatypes import Boolean, Enumerate, String
from itools.gettext import MSG
from itools.http import get_context
from itools.i18n import get_language_name, get_languages
from itools.web import stl_view, INFO, ERROR
from itools.web import boolean_field, choice_field, input_field
from itools.web import multiple_choice_field, textarea_field

# Import from ikaaro
from autoform import AutoForm
import messages
from resource_views import DBResource_Edit
from views import IconsView



class ControlPanel(IconsView):

    access = 'is_allowed_to_edit'
    view_title = MSG(u'Control Panel')
    icon = 'settings.png'

    def items(self):
        items = []
        # Hardcode direct link to the users folder
        description = MSG(u'View and edit current users, register new users.')
        items.append({
            'icon': '/ui/icons/48x48/userfolder.png',
            'title': MSG(u'Users'),
            'description': description,
            'url': '/users/'})

        # Add dynamic views
        resource = self.resource
        context = self.context
        for name in resource.class_control_panel:
            view = resource.get_view(name)
            if view is None:
                continue
            if not resource.is_access_allowed(context, resource, view):
                continue
            items.append({
                'icon': resource.get_method_icon(view, size='48x48'),
                'title': view.view_title,
                'description': view.view_description,
                'url': ';%s' % name})

        return items



class CPEditVirtualHosts(stl_view):

    access = 'is_admin'
    view_title = MSG(u'Virtual Hosts')
    view_description = MSG(u'Define the domain names for this Web Site.')
    icon = 'website.png'
    template = 'website/virtual_hosts.xml'

    vhosts = textarea_field(datatype=String, cols=50)


    @thingy_lazy_property
    def vhosts__value(self):
        vhosts = self.view.resource.get_value('vhosts')
        return '\n'.join(vhosts)


    def action(self):
        vhosts = [ x.strip() for x in self.vhosts.value.splitlines() ]
        vhosts = [ x for x in vhosts if x ]
        self.resource.set_property('vhosts', vhosts)
        # Ok
        context = self.context
        context.message = messages.MSG_CHANGES_SAVED
        context.redirect()



class CPEditSEO(AutoForm):

    access = 'is_allowed_to_edit'
    view_title = MSG(u'Search engine optimization')
    icon = 'search.png'
    view_description = MSG(u"""
      Optimize your website for better ranking in search engine results.""")

    # Fields
    google_site_verification = input_field()
    google_site_verification.title = MSG(u'Google site verification key')

    yahoo_site_verification = input_field()
    yahoo_site_verification.title = MSG(u'Yahoo site verification key')

    bing_site_verification = input_field()
    bing_site_verification.title = MSG(u'Bing site verification key')

    @thingy_property
    def google_site_verification__value(self):
        return self.view.resource.get_value('google_site_verification')


    @thingy_property
    def yahoo_site_verification__value(self):
        return self.view.resource.get_value('yahoo_site_verification')


    @thingy_property
    def bing_site_verification__value(self):
        return self.view.resource.get_value('bing_site_verification')


    def action(self):
        value = self.google_site_verification.value
        self.resource.set_property('google_site_verification', value)
        value = self.yahoo_site_verification.value
        self.resource.set_property('yahoo_site_verification', value)
        value = self.bing_site_verification.value
        self.resource.set_property('bing_site_verification', value)
        # Ok
        context = self.context
        context.message = messages.MSG_CHANGES_SAVED
        context.redirect()



class CPEditSecurityPolicy(stl_view):

    access = 'is_allowed_to_edit'
    view_title = MSG(u'Security Policy')
    icon = 'lock.png'
    view_description = MSG(u'Choose the security policy.')
    template = 'website/security_policy.xml'

    website_is_open = boolean_field()


    def is_open(self):
        return self.resource.get_value('website_is_open')


    def action(self, resource, context, form):
        value = form['website_is_open']
        resource.set_property('website_is_open', value)
        # Ok
        context.message = messages.MSG_CHANGES_SAVED
        context.redirect()



def values(self):
    values = []
    for user in self.view.resource.get_resources('/users'):
        email = user.get_value('email')
        title = user.get_title()
        title = email if title == email else '%s <%s>' % (title, email)
        values.append((user.get_name(), {'title': title}))
    values.sort(key=lambda x: x[1]['title'].lower())

    return OrderedDict(values)



class CPEditContactOptions(DBResource_Edit):

    access = 'is_allowed_to_edit'
    view_title = MSG(u'Email options')
    icon = 'mail.png'
    view_description = MSG(u'Configure the website email options')

    # Fields
    emails_signature = textarea_field(title=MSG(u'Emails signature'))

    emails_from_addr = choice_field(title=MSG(u'Emails from addr'))
    emails_from_addr.values = thingy_lazy_property(values)

    contacts = multiple_choice_field()
    contacts.title = MSG(u'Select the contact accounts')
    contacts.values = thingy_lazy_property(values)

    captcha_question = TextField(required=True, title=MSG(u'Captcha question'))
    captcha_answer = TextField(required=True, title=MSG(u'Captcha answer'))

    field_names = ['emails_from_addr', 'emails_signature', 'contacts',
                   'captcha_question', 'captcha_answer']


#   def get_value(self, name):
#       if name == 'contacts':
#           return list(self.resource.get_property('value'))

#       return super(CPEditContactOptions, self).get_value(name)


    def action(self, resource, context, form):
        resource.set_property('emails_from_addr', form['emails_from_addr'])
        resource.set_property('emails_signature', form['emails_signature'])
        resource.set_property('contacts', tuple(form['contacts']))
        resource.set_property('captcha_question', form['captcha_question'])
        resource.set_property('captcha_answer', form['captcha_answer'])
        # Ok
        context.message = messages.MSG_CHANGES_SAVED



class CPBrokenLinks(stl_view):

    access = 'is_admin'
    view_title = MSG(u'Broken Links')
    icon = 'clear.png'
    view_description = MSG(u'Check the referential integrity.')
    template = 'website/broken_links.xml'


    @thingy_lazy_property
    def items(self):
        # These are all the physical links we have in the database
        context = self.context
        links = context.database.catalog.get_unique_values('links')

        # Make a partial search within the website
        results = context.get_root_search()

        # Find out the broken links within scope and classify them by the
        # origin paths
        broken = {}
        for link in links:
            # Filter links out of scope and not broken links
            link_logical = context.get_logical_path(link)
            if link_logical is None:
                continue
            if context.get_resource(link_logical, soft=True):
                continue
            # Keep in the mapping
            link_logical = str(link_logical)
            for brain in results.search(links=link).get_documents():
                broken.setdefault(brain.abspath, []).append(link_logical)

        # Ok
        return [
            {'path': path, 'links': links, 'n': len(links)}
            for path, links in sorted(broken.iteritems()) ]


    def total(self):
        return sum( x['n'] for x in self.items )



class language_field(choice_field):

    @thingy_lazy_property
    def values(self):
        view = self.view
        languages = set(view.languages)
        values = [
            (x['code'], {'title': x['name']})
            for x in get_languages() if x['code'] not in languages ]
        values = sorted(values, key=lambda x: x[1]['title'])
        values.insert(0, ('', {'title': MSG(u'Choose a language')}))
        return OrderedDict(values)



class CPEditLanguages(stl_view):

    access = 'is_admin'
    view_title = MSG(u'Languages')
    view_description = MSG(u'Define the Web Site languages.')
    icon = 'languages.png'
    template = 'website/edit_languages.xml'

    codes = multiple_choice_field(required=True)
    code = language_field(required=True)


    @thingy_lazy_property
    def languages(self):
        return self.resource.get_value('website_languages')


    def active_languages(self):
        languages = self.languages
        default = languages[0]

        return [
            {'code': x, 'name': get_language_name(x),
             'isdefault': x == default}
            for x in languages ]


    #######################################################################
    # Actions / Edit
    def action_change_default_language(self, resource, context, form):
        codes = form['codes']

        # This action requires only one language to be selected
        if len(codes) != 1:
            message = ERROR(u'You must select one and only one language.')
            context.message = message
            return
        default = codes[0]

        # Change the default language
        languages = resource.get_value('website_languages')
        languages = [ x for x in languages if x != default ]
        languages.insert(0, default)
        resource.set_property('website_languages', tuple(languages))
        # Ok
        context.message = messages.MSG_CHANGES_SAVED


    def action_remove_languages(self, resource, context, form):
        codes = form['codes']

        # Check the default language is not to be removed
        languages = resource.get_value('website_languages')
        default = languages[0]
        if default in codes:
            message = ERROR(u'You can not remove the default language.')
            context.message = message
            return

        # Remove the languages
        languages = [ x for x in languages if x not in codes ]
        resource.set_property('website_languages', tuple(languages))
        # Ok
        context.message = INFO(u'Languages removed.')


    #######################################################################
    # Actions / Add
    action_add_language_fields = ['code']
    def action_add_language(self):
        code = self.code.value

        # Change
        resource = self.resource
        ws_languages = resource.get_value('website_languages')
        resource.set_property('website_languages', ws_languages + (code,))

        # Ok
        context = self.context
        context.message = INFO(u'Language added.')
        context.redirect()

