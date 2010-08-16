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
from itools.core import merge_dicts
from itools.datatypes import String, Tokens, Unicode
from itools.gettext import MSG
from itools.web import STLView, VirtualRoot

# Import from ikaaro
from access import RoleAware
from calendar.views import MonthlyView, WeeklyView, DailyView
from control_panel import ControlPanel, CPAddUser, CPBrokenLinks
from control_panel import CPBrowseUsers, CPEditContactOptions, CPEditLanguages
from control_panel import CPEditMembership, CPEditSecurityPolicy
from control_panel import CPEditVirtualHosts, CPOrphans, CPEditSEO
from folder import Folder
from registry import register_document_type
from resource_views import LoginView
from skins import Skin
from website_views import AboutView, ContactForm, CreditsView
from website_views import ForgottenPasswordForm, RegisterForm
from website_views import SiteSearchView, NotFoundView, ForbiddenView
from website_views import WebSite_NewInstance
from website_views import InternalServerError



class WebSite(RoleAware, Folder, VirtualRoot):

    class_id = 'WebSite'
    class_version = '20100430'
    class_title = MSG(u'Web Site')
    class_description = MSG(u'Create a new Web Site or Work Place.')
    class_icon16 = 'icons/16x16/website.png'
    class_icon48 = 'icons/48x48/website.png'
    class_skin = 'ui/aruni'
    class_views = ['view', 'list', 'table', 'gallery', 'month', 'week',
                   'edit', 'backlinks', 'last_changes', 'control_panel']
    class_control_panel = ['browse_users', 'add_user', 'edit_virtual_hosts',
                           'edit_security_policy', 'edit_languages',
                           'edit_contact_options', 'broken_links', 'orphans',
                           'edit_seo']


    __fixed_handlers__ = ['skin', 'index']


    class_schema = merge_dicts(
        Folder.class_schema,
        RoleAware.class_schema,
        # Metadata
        vhosts=String(source='metadata', multiple=True, indexed=True),
        contacts=Tokens(source='metadata'),
        emails_from_addr=String(source='metadata'),
        emails_signature=Unicode(source='metadata'),
        google_site_verification=String(source='metadata'),
        yahoo_site_verification=String(source='metadata'),
        bing_site_verification=String(source='metadata'),
        website_languages=Tokens(source='metadata', default=('en',)),
        captcha_question=Unicode(source='metadata', default=u"2 + 3"),
        captcha_answer=Unicode(source='metadata', default=u"5"))


    ########################################################################
    # API
    ########################################################################
    def get_default_language(self):
        return self.get_value('website_languages')[0]


    def is_allowed_to_register(self, user, resource):
        return self.get_property('website_is_open')


    #######################################################################
    # HTTP stuff
    #######################################################################
    def get_skin(self):
        return Skin

    # Views for error conditions
    http_forbidden = ForbiddenView
    http_unauthorized = LoginView
    http_not_found = NotFoundView
    http_internal_server_error = InternalServerError


    #######################################################################
    # UI
    #######################################################################
    new_instance = WebSite_NewInstance
    # Control Panel
    control_panel = ControlPanel
    browse_users = CPBrowseUsers
    add_user = CPAddUser
    edit_membership = CPEditMembership
    edit_virtual_hosts = CPEditVirtualHosts
    edit_security_policy = CPEditSecurityPolicy
    edit_seo = CPEditSEO
    edit_contact_options = CPEditContactOptions
    edit_languages = CPEditLanguages
    broken_links = CPBrokenLinks
    orphans = CPOrphans
    # Register / Login
    register = RegisterForm
    forgotten_password = ForgottenPasswordForm
    # Public views
    site_search = SiteSearchView
    contact = ContactForm
    about = AboutView
    credits = CreditsView
    license = STLView(access=True, view_title=MSG(u'License'),
                      template='root/license.xml')

    # Calendar views
    month = MonthlyView
    week = WeeklyView
    day = DailyView


    #######################################################################
    # Upgrade
    #######################################################################
    def update_20100430(self):
        vhosts = self.get_property('vhosts')
        if len(vhosts) == 1:
            vhosts = vhosts[0].split()
            if len(vhosts) > 1:
                self.set_property('vhosts', vhosts)



###########################################################################
# Register
###########################################################################
register_document_type(WebSite, WebSite.class_id)
