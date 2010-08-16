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

# Import from the Standard Library
import sys
from traceback import format_exc

# Import from itools
from itools.core import get_abspath, merge_dicts
from itools.core import thingy_property, thingy_lazy_property
from itools.core import OrderedDict
from itools.csv import Property
from itools.datatypes import Email, Enumerate, String, Unicode
from itools.fs import lfs
from itools.gettext import MSG
from itools.stl import stl
from itools import vfs
from itools.web import STLView, INFO, ERROR
from itools.web import choice_field, email_field, text_field, textarea_field
from itools.xapian import PhraseQuery, OrQuery, AndQuery, split_unicode

# Import from ikaaro
from autoform import AutoForm
import globals
from messages import MSG_NEW_RESOURCE
from registry import get_resource_class
from views import SearchForm
from views_new import ProxyNewInstance



class NotFoundView(STLView):
    template = 'root/not_found.xml'

    def uri(self):
        return str(self.context.uri)


class ForbiddenView(STLView):
    template = 'root/forbidden.xml'

    def POST(self, resource, context):
        return self.GET


class InternalServerError(STLView):
    template = 'root/internal_server_error.xml'

    def traceback(self):
        return format_exc()



class ForgottenPasswordForm(AutoForm):

    access = True
    view_title = MSG(u'Forgotten password')
    submit_value = MSG(u'Ok')
    meta = [('robots', 'noindex, follow', None)]

    username = email_field(value='', title=MSG(u'Type your email address'))


    def get_value(self, name):
        if name == 'username':
            return self.context.get_query_value('username')

        return super(ForgottenPasswordForm, self).get_value(name)


    def action(self, resource, context, form):
        # Get the email address
        username = form['username'].strip()

        # Get the user with the given login name
        results = context.search(username=username)
        if len(results) == 0:
            message = ERROR(u'There is not a user identified as "{username}"',
                            username=username)
            context.message = message
            return


        # Send email of confirmation
        user = results.get_documents()[0]
        email = user.get_value('email')
        user.send_forgotten_password(context, email)

        handler = resource.get_resource('/ui/website/forgotten_password.xml')
        return stl(handler)



class RegisterForm(AutoForm):

    access = 'is_allowed_to_register'
    view_title = MSG(u'Register')
    submit_value = MSG(u'Register')

    firstname = text_field(required=True, title=MSG(u'First Name'))
    lastname = text_field(required=True, title=MSG(u'Last Name'))
    email = email_field(required=True, title=MSG(u'E-mail Address'))


    def action(self, resource, context, form):
        # Get input data
        firstname = form['firstname'].strip()
        lastname = form['lastname'].strip()
        email = form['email'].strip()

        # Do we already have a user with that email?
        user = context.get_user_by_login(email)
        if user is not None:
            if not user.has_property('user_must_confirm'):
                message = u'There is already an active user with that email.'
                context.message = ERROR(message)
                return
        else:
            # Add the user
            users = resource.get_resource('users')
            user = users.set_user(email, None)
            user.set_property('firstname', firstname)
            user.set_property('lastname', lastname)
            # Set the role
            default_role = resource.class_roles[0]
            resource.set_user_role(user.get_name(), default_role)

        # Send confirmation email
        user.send_confirmation(context, email)

        # Bring the user to the login form
        message = MSG(
            u"An email has been sent to you, to finish the registration "
            u"process follow the instructions detailed in it.")
        return message.gettext().encode('utf-8')



class to_field(choice_field):

    @thingy_lazy_property
    def values(self):
        resource = self.view.resource
        users = resource.get_resource('/users')

        values = OrderedDict()
        for username in resource.get_value('contacts'):
            user = users.get_resource(name, soft=True)
            if user is None:
                continue
            values[username] = users.get_resource(username).get_title()

        return values



class ContactForm(AutoForm):

    access = True
    view_title = MSG(u'Contact')
    submit_value = MSG(u'Send')

    # Fields
    to = to_field(required=True, title = MSG(u'Recipient'))
    subject = text_field(required=True, title=MSG(u'Message subject'))

    message_body = textarea_field(required=True, rows=8, cols=50)
    message_body.title = MSG(u'Message body')

    from_ = email_field(required=True, title=MSG(u'Your email address'))

    captcha_answer = TextField(required=True)
    captcha_answer.title = MSG(u"Please answer this: {captcha_question}")

    field_names = ['to', 'from_', 'subject', 'message_body', 'captcha_answer']


    def get_value(self, field):
        if field.name == 'from_':
            user = self.context.user
            if user:
                return user.get_value('email')

        return super(ContactForm, self).get_value(field)


    def action(self, resource, context, form):
        # Check captcha first
        captcha_answer = form['captcha_answer'].strip()
        expected = resource.get_property('captcha_answer')
        if captcha_answer != expected:
            context.message = ERROR(u"Wrong answer to the question.")
            return
        # Get form values
        contact = form['to']
        from_addr = form['from_'].strip()
        subject = form['subject'].strip()
        body = form['message_body'].strip()

        # Find out the "to" address
        contact = resource.get_resource('/users/%s' % contact)
        contact_title = contact.get_title()
        contact = contact.get_property('email')
        if contact_title != contact:
            contact = (contact_title, contact)
        # Send the email
        context.send_email(contact, subject, from_addr=from_addr, text=body)
        # Ok
        context.message = INFO(u'Message sent.')



class SiteSearchView(SearchForm):

    access = True
    view_title = MSG(u'Search')
    template = 'website/search.xml'

    site_search_text = text_field(source='query')

    sort_by = None
    reverse = None


    def text(self):
        return self.site_search_text.value.strip()


    search_template = 'website/search_form.xml'


    @thingy_lazy_property
    def all_items(self):
        text = self.site_search_text.value.strip()
        if not text:
            return []

        # The Search Query
        resource = self.resource
        languages = resource.get_value('website_languages')
        queries = []
        for language in languages:
            query = [
                OrQuery(PhraseQuery('title', word), PhraseQuery('text', word))
                for word in split_unicode(text, language) ]
            if query:
                queries.append(AndQuery(*query))

        if not queries:
            return []
        query = OrQuery(*queries)

        # Search
        context = self.context
        results = context.search(query)

        # Check access rights
        user = context.user
        items = []
        for resource in results.get_documents():
            ac = resource.get_access_control()
            if ac.is_allowed_to_view(user, resource):
                items.append(resource)

        return items


    @thingy_property
    def items(self):
        # Batch
        start = self.batch_start.value
        size = self.batch_size.value
        return self.all_items[start:start+size]


    table_template = 'website/search_table.xml'
    def get_table_namespace(self, resource, context, items):
        # Build the namespace
        site_root = resource.get_site_root()
        items_ns = [{
            'abspath': '/%s' % site_root.get_pathto(item),
            'title': item.get_title(),
            'type': item.class_title.gettext(),
            'size': item.get_human_size(),
            'url': '%s/' % resource.get_pathto(item),
            'icon': item.get_class_icon(),
        } for item in items ]

        return {'items': items_ns}



class AboutView(STLView):

    access = True
    view_title = MSG(u'About')
    template = 'root/about.xml'


    def packages(self):
        # Python, itools & ikaaro
        packages = ['sys', 'itools', 'ikaaro']
        config = globals.config
        packages.extend(config.get_value('modules'))
        # Try packages we frequently use
        packages.extend([
            'gio', 'xapian', 'pywin32', 'PIL.Image', 'docutils', 'reportlab',
            'xlrd'])
        # Mapping from package to version attribute
        package2version = {
            'gio': 'pygio_version',
            'xapian': 'version_string',
            'PIL.Image': 'VERSION',
            'reportlab': 'Version',
            'sys': 'version_info',
            'xlrd': '__VERSION__'}
        package2title = {
            'gio': 'pygobject',
            'sys': 'Python',
            }

        # Namespace
        packages_ns = []
        for name in packages:
            attribute = package2version.get(name, '__version__')
            # Import
            if '.' in name:
                name, subname = name.split('.')
                try:
                    package = __import__(subname, fromlist=[name])
                except ImportError:
                    continue
            else:
                try:
                    package = __import__(name)
                except ImportError:
                    continue

            # Version
            try:
                version = getattr(package, attribute)
            except AttributeError:
                version = MSG(u'no version found')
            else:
                if hasattr(version, '__call__'):
                    version = version()
                if isinstance(version, tuple):
                    version = '.'.join([str(v) for v in version])
            # Ok
            title = package2title.get(name, name)
            packages_ns.append({'name': title, 'version': version})

        # Insert first the platform
        platform = {
            'linux2': 'GNU/Linux',
            'darwin': 'Mac OS X',
            'win32': 'Windows'}.get(sys.platform, sys.platform)
        packages_ns.insert(0,
            {'name': MSG(u'Operating System'), 'version': platform})

        return packages_ns



class CreditsView(STLView):

    access = True
    view_title = MSG(u'Credits')
    template = 'root/credits.xml'
    styles = ['/ui/credits.css']


    def hackers(self):
        credits = get_abspath('CREDITS')
        lines = lfs.open(credits).readlines()
        return [ x[3:].strip() for x in lines if x.startswith('N: ') ]



class WebSite_NewInstance(ProxyNewInstance):

    template = '/ui/website/new_instance.xml.en'

    schema = merge_dicts(ProxyNewInstance.schema, vhosts=String)

    def get_namespace(self, resource, context):
        namespace = ProxyNewInstance.get_namespace(self, resource, context)
        # Add vhosts
        vhosts = context.get_form_value('vhosts')
        namespace['vhosts'] = vhosts

        return namespace


    def action(self, resource, context, form):
        name = form['name']
        title = form['title']
        vhosts = form['vhosts']
        vhosts = [ x.strip() for x in vhosts.splitlines() ]
        vhosts = [ x for x in vhosts if x ]

        # Create the resource
        class_id = form['class_id']
        if class_id is None:
            # Get it from the query
            class_id = context.query['type']
        cls = get_resource_class(class_id)
        child = resource.make_resource(name, cls)
        # The metadata
        metadata = child.metadata
        language = resource.get_content_language(context)
        metadata.set_property('title', Property(title, lang=language))
        metadata.set_property('vhosts', vhosts)

        goto = './%s/' % name
        return context.come_back(MSG_NEW_RESOURCE, goto=goto)

