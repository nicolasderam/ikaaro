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
from itools.datatypes import Tokens
from itools.gettext import MSG
from itools.html import stream_to_str_as_html, xhtml_doctype
from itools.web import STLView, VirtualRoot

# Import from ikaaro
from access import RoleAware
from calendar.views import MonthlyView, WeeklyView, DailyView
from control_panel import ControlPanel, CPAddUser, CPBrokenLinks
from control_panel import CPBrowseUsers, CPEditContactOptions, CPEditLanguages
from control_panel import CPEditMembership, CPEditSecurityPolicy
from control_panel import CPEditVirtualHosts, CPOrphans
from folder import Folder
from registry import register_resource_class, register_document_type
from resource_views import LoginView
from skins import Skin
from views_new import ProxyNewInstance
from website_views import AboutView, ContactForm, CreditsView
from website_views import ForgottenPasswordForm, RegisterForm
from website_views import SiteSearchView, NotFoundView, ForbiddenView
from website_views import InternalServerError



class WebSite(RoleAware, Folder, VirtualRoot):

    class_id = 'WebSite'
    class_title = MSG(u'Web Site')
    class_description = MSG(u'Create a new Web Site or Work Place.')
    class_icon16 = 'icons/16x16/website.png'
    class_icon48 = 'icons/48x48/website.png'
    class_skin = 'ui/aruni'
    class_views = Folder.class_views + ['control_panel']
    class_control_panel = ['browse_users', 'add_user', 'edit_virtual_hosts',
                           'edit_security_policy', 'edit_languages',
                           'edit_contact_options', 'broken_links', 'orphans']


    __fixed_handlers__ = ['skin', 'index']


    def _get_resource(self, name):
        if name in ('users', 'users.metadata'):
            return self.parent._get_resource(name)
        return Folder._get_resource(self, name)


    @classmethod
    def get_metadata_schema(cls):
        schema = Folder.get_metadata_schema()
        schema.update(RoleAware.get_metadata_schema())
        schema['vhosts'] = Tokens
        schema['contacts'] = Tokens
        schema['website_languages'] = Tokens(default=('en',))
        return schema


    def _get_catalog_values(self):
        values = Folder._get_catalog_values(self)
        values['vhosts'] = self.get_property('vhosts')
        return values


    ########################################################################
    # API
    ########################################################################
    def get_default_language(self):
        return self.get_property('website_languages')[0]


    def is_allowed_to_register(self, user, resource):
        return self.get_property('website_is_open')


    #######################################################################
    # HTTP stuff
    #######################################################################
    skin = Skin()

    # Views for error conditions
    http_forbidden = ForbiddenView()
    http_unauthorized = LoginView()
    http_not_found = NotFoundView()
    http_internal_server_error = InternalServerError()


    #######################################################################
    # UI
    #######################################################################
    new_instance = ProxyNewInstance()
    # Control Panel
    control_panel = ControlPanel()
    browse_users = CPBrowseUsers()
    add_user = CPAddUser()
    edit_membership = CPEditMembership()
    edit_virtual_hosts = CPEditVirtualHosts()
    edit_security_policy = CPEditSecurityPolicy()
    edit_contact_options = CPEditContactOptions()
    edit_languages = CPEditLanguages()
    broken_links = CPBrokenLinks()
    orphans = CPOrphans()
    # Register / Login
    register = RegisterForm()
    forgotten_password = ForgottenPasswordForm()
    # Public views
    site_search = SiteSearchView()
    contact = ContactForm()
    about = AboutView()
    credits = CreditsView()
    license = STLView(access=True, title=MSG(u'License'),
                      template='root/license.xml')

    # Calendar views
    monthly_view = MonthlyView()
    weekly_view = WeeklyView()
    daily_view = DailyView()


###########################################################################
# Register
###########################################################################
register_resource_class(WebSite)
register_document_type(WebSite, WebSite.class_id)
