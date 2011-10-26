# -*- coding: UTF-8 -*-
# Copyright (C) 2011 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
from itools.core import proto_lazy_property
from itools.datatypes import String
from itools.gettext import MSG
from itools.web import ERROR, INFO, FormError

# Import from ikaaro
from autoadd import AutoAdd
from buttons import Button, BrowseButton
from config import Configuration
from emails import send_email
from fields import Password_Field
from messages import MSG_CHANGES_SAVED, MSG_PASSWORD_MISMATCH
from resource_ import DBResource
from user_views import BrowseUsers



class AddUser(AutoAdd):

    access = 'is_admin'
    title = MSG(u'Add New Member')
    icon = 'card.png'
    description = MSG(u'Grant access to a new user.')

    fields = ['email', 'password', 'password2', 'groups']

    password = Password_Field(title=MSG(u'Password'), datatype=String,
            tip = MSG(u'If no password is given an email will be sent to the '
                      u' user, asking him to choose his password.'))
    password2 = Password_Field(title=MSG(u'Repeat password'),
                               datatype=String)


    @proto_lazy_property
    def _resource_class(self):
        return self.context.database.get_resource_class('user')


    def _get_form(self, resource, context):
        form = super(AddUser, self)._get_form(resource, context)

        # Check whether the user already exists
        email = form['email'].strip()
        results = context.search(email=email)
        if len(results):
            raise FormError, ERROR(u'The user is already here.')

        # Check the password is right
        password = form['password'].strip()
        if password != form['password2']:
            raise FormError, MSG_PASSWORD_MISMATCH
        if password == '':
            form['password'] = None

        return form


    actions = [
        Button(access='is_admin', css='button-ok',
               title=MSG(u'Add and view')),
        Button(access='is_admin', css='button-ok', name='add_and_return',
               title=MSG(u'Add and return'))]


    def get_container(self, resource, context, form):
        return resource.get_resource('/users')


    automatic_resource_name = True


    def make_new_resource(self, resource, context, form):
        proxy = super(AddUser, self)
        child = proxy.make_new_resource(resource, context, form)

        # Send email to the new user
        if child:
            if form['password']:
                email_id = 'add-user-send-notification'
            else:
                child.update_pending_key()
                email_id = 'add-user-send-invitation'

            send_email(email_id, context, form['email'], user=child)

        # Ok
        return child


    def action_add_and_return(self, resource, context, form):
        child = self.make_new_resource(resource, context, form)
        if child is None:
            return

        context.message = INFO(u'User added.')



class ConfigUsers_Browse(BrowseUsers):

    table_actions = [
        BrowseButton(access='is_admin', name='switch_state',
                     title=MSG(u'Switch state'))]


    def action_switch_state(self, resource, context, form):
        # Verify if after this operation, all is ok
        usernames = form['ids']
        if context.user.name in usernames:
            context.message = ERROR(u'You cannot change your state yourself.')
            return

        database = resource.database
        for username in usernames:
            user = database.get_resource('/users/%s' % username)
            user_state = user.get_value('user_state')
            if user_state == 'active':
                user.set_value('user_state', 'inactive')
            elif user_state == 'inactive':
                user.set_value('user_state', 'active')
            else: # pending
                continue

        # Ok
        context.message = MSG_CHANGES_SAVED



class ConfigUsers(DBResource):

    class_id = 'config-users'
    class_title = MSG(u'Users')
    class_description = MSG(u'Manage users.')
    class_icon48 = 'icons/48x48/userfolder.png'

    # Views
    class_views = ['browse_users', 'add_user']
    browse_users = ConfigUsers_Browse()
    add_user = AddUser()

    # Configuration
    config_name = 'users'
    config_group = 'access'


# Register
Configuration.register_plugin(ConfigUsers)