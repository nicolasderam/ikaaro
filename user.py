# -*- coding: UTF-8 -*-
# Copyright (C) 2005-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2006-2007 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007 Henry Obein <henry@itaapy.com>
# Copyright (C) 2007-2008 Sylvain Taverne <sylvain@itaapy.com>
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
from copy import deepcopy

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Email, String, Unicode
from itools.gettext import MSG
from itools.uri import Path

# Import from ikaaro
from access import AccessControl
from datatypes import Password
from folder import Folder
from registry import get_resource_class
from resource_views import DBResource_Edit
from user_views import User_ConfirmRegistration, User_EditAccount
from user_views import User_EditPassword, User_EditPreferences, User_EditRole
from user_views import User_Profile, User_ResendConfirmation, User_Tasks
from user_views import User_ChangePasswordForgotten
from user_views import UserFolder_Table, UserFolder_AddUser
from utils import crypt_password, generate_password



class User(AccessControl, Folder):

    class_id = 'user'
    class_version = '20081217'
    class_title = MSG(u'User')
    class_icon16 = 'icons/16x16/user.png'
    class_icon48 = 'icons/48x48/user.png'
    class_views = [
        'profile', 'edit_account', 'edit_preferences', 'edit_password',
        'edit_role', 'tasks']


    ########################################################################
    # Schema
    ########################################################################
    class_schema = merge_dicts(
        Folder.class_schema,
        # Metadata
        firstname=Unicode(source='metadata', indexed=True, stored=True),
        lastname=Unicode(source='metadata', indexed=True, stored=True),
        email=Email(source='metadata', indexed=True, stored=True),
        password=Password(source='metadata'),
        role=String(source='metadata'),
        user_language=String(source='metadata'),
        user_must_confirm=String(source='metadata'),
        # Metadata (backwards compatibility)
        username=String(source='metadata', indexed=True, stored=True),
        # Other
        email_domain=String(indexed=True, stored=True))


    def get_email_domain(self):
        email = self.metadata.get_property('email')
        if email and '@' in email.value:
            return email.value.split('@', 1)[1]
        return None


    def get_username(self):
        # FIXME Check first the username (for compatibility with 0.14)
        username = self.metadata.get_property('username')
        if username:
            return username.value

        return self.metadata.get_property('email').value


    def get_role_title(self):
        role = self.get_value('role')
        return self.get_parent().get_parent().roles[role]['title']


    ########################################################################
    # API
    ########################################################################
    def get_title(self, language=None):
        firstname = self.get_value('firstname')
        lastname = self.get_value('lastname')
        if firstname:
            if lastname:
                return '%s %s' % (firstname, lastname)
            return firstname
        if lastname:
            return lastname
        return self.get_value('username')


    def set_password(self, password):
        crypted = crypt_password(password)
        self.set_property('password', crypted)


    def authenticate(self, password, clear=False):
        if clear:
            password = crypt_password(password)

        return password == self.get_value('password')


    def set_auth_cookie(self, context, password):
        username = self.get_name()
        crypted = crypt_password(password)
        cookie = Password.encode('%s:%s' % (username, crypted))
        # TODO Add a reasonable expires value, for security
        context.set_cookie('__ac', cookie, path='/')


    ########################################################################
    # Email: Register confirmation & Password forgotten
    ########################################################################

    confirmation_subject = MSG(u"Confirmation required")
    confirmation_txt = MSG(u"To confirm your identity, click the link:"
                           u"\n"
                           u"\n {uri}")
    def send_confirmation(self, context, email):
        self.send_confirm_url(context, email, self.confirmation_subject,
            self.confirmation_txt, ';confirm_registration')


    forgotten_subject = MSG(u"Choose a new password")
    forgotten_txt = MSG(u"To choose a new password, click the link:"
                        u"\n"
                        u"\n {uri}")
    def send_forgotten_password(self, context, email):
        self.send_confirm_url(context, email, self.forgotten_subject,
            self.forgotten_txt, ';change_password_forgotten')


    def send_confirm_url(self, context, email, subject, text, view):
        # Set the confirmation key
        if self.has_property('user_must_confirm'):
            key = self.get_property('user_must_confirm')
        else:
            key = generate_password(30)
            self.set_property('user_must_confirm', key)

        # Build the confirmation link
        confirm_url = deepcopy(context.uri)
        path = '/users/%s/%s' % (self.get_name(), view)
        confirm_url.path = Path(path)
        confirm_url.query = {
            'key': key,
            'username': self.get_value('username')}
        confirm_url = str(confirm_url)
        text = text.gettext(uri=confirm_url)
        context.send_email(email, subject.gettext(), text=text)


    ########################################################################
    # Access control
    def is_self_or_admin(self, user, resource):
        # You are nobody here, ha ha ha
        if user is None:
            return False

        # In my home I am the king
        if self.path == user.path:
            return True

        # The all-powerfull
        return self.is_admin(user, resource)


    is_allowed_to_edit = is_self_or_admin


    #######################################################################
    # Views
    #######################################################################
    resend_confirmation = User_ResendConfirmation
    confirm_registration = User_ConfirmRegistration
    change_password_forgotten = User_ChangePasswordForgotten
    profile = User_Profile
    edit_account = User_EditAccount
    edit_preferences = User_EditPreferences
    edit_password = User_EditPassword
    edit_role = User_EditRole
    tasks = User_Tasks



class UserFolder(Folder):

    class_id = 'users'
    class_title = MSG(u'User Folder')
    class_icon16 = 'icons/16x16/userfolder.png'
    class_icon48 = 'icons/48x48/userfolder.png'
    class_views = ['table', 'add_user', 'edit']


    def get_document_types(self):
        return [get_resource_class('user')]


    def get_canonical_path(self):
        return Path('/users')


    def get_usernames(self):
        """Return all user names.
        """
        names = self._get_names()
        return frozenset(names)


    #######################################################################
    # Back-Office
    #######################################################################
    table = UserFolder_Table
    add_user = UserFolder_AddUser
    edit = DBResource_Edit(access='is_admin')

