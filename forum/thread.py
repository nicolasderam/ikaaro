# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Henry Obein <henry@itaapy.com>
# Copyright (C) 2007 Sylvain Taverne <sylvain@itaapy.com>
# Copyright (C) 2007-2008 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
from itools.datatypes import Unicode, String
from itools.gettext import MSG
from itools.i18n import format_datetime
from itools.vfs import FileName
from itools.web import STLForm

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.messages import MSG_DELETE_SELECTION, MSG_CHANGES_SAVED
from ikaaro.registry import register_object_class
from message import Message, build_message


###########################################################################
# Views
###########################################################################
class ThreadView(STLForm):

    access = 'is_allowed_to_view'
    title = MSG(u'View')
    icon = 'view.png'
    template = '/ui/forum/Thread_view.xml'

    schema = {
        'ids': String(multiple=True, mandatory=True)
        }

    def get_namespace(self, resource, context):
        context.styles.append('/ui/forum/forum.css')
        user = context.user
        users = resource.get_resource('/users')
        ac = resource.get_access_control()
        accept_language = context.accept_language
        # The namespace
        namespace = {'editable': ac.is_admin(user, resource)}
        # Actions
        actions = []
        message = MSG_DELETE_SELECTION.gettext()
        remove_message = 'return confirm("%s");' % message
        namespace['remove_message'] = remove_message

        namespace['messages'] = []
        for message in resource.get_posts():
            author = message.get_owner()
            if author is not None:
                author = users.get_resource(author).get_title()
            namespace['messages'].append({
                'name': message.name,
                'author': author,
                'mtime': format_datetime(message.get_mtime(), accept_language),
                'body': message.handler.events,
            })
        namespace['is_allowed_to_add'] = ac.is_allowed_to_add(user, resource)
        if namespace['is_allowed_to_add']:
            namespace['rte'] = resource.get_rte(context, 'data', None)
        return namespace


    action_new_reply_schema = {'data': Unicode(mandatory=True)}
    def action_new_reply(self, resource, context, form):
        # Add
        id = resource.get_last_post_id()
        name = str(id + 1)
        data = form['data']
        language = resource.get_content_language()
        thread = Message.make_object(Message, resource, name, data, language)
        # Ok
        return context.come_back(MSG(u'Reply posted'))


    def action_remove(self, resource, context, form):
        user = context.user
        for name in form['ids']:
            object = resource.get_resource(name)
            ac = object.get_access_control()
            if ac.is_allowed_to_remove(user, object):
                resource.del_resource(name)
        message = MSG(u"Message(s) deleted !")
        return context.come_back(message, goto='#new_reply')


###########################################################################
# Model
###########################################################################

class Thread(Folder):

    class_id = 'ForumThread'
    class_version = '20071215'
    class_title = MSG(u'Thread')
    class_description = u"A thread to discuss"
    class_views = ['view', 'edit_metadata_form']

    # XXX
    #addlink_form__access__ = False
    #addimage_form__access__ = False


    @staticmethod
    def _make_object(cls, folder, name, data=u'', language='en'):
        Folder._make_object(cls, folder, name)
        # First post
        folder.set_handler('%s/0.metadata' % name, Message.build_metadata())
        message = build_message(data)
        folder.set_handler('%s/0.xhtml.%s' % (name, language), message)


    def to_text(self):
        # Index the thread by the content of all its posts
        text = [ x.to_text() for x in self.search_resources(cls=Message) ]
        return u'\n'.join(text)


    def get_document_types(self):
        return [self.message_class]


    def get_posts(self):
        posts = self.search_resources(cls=Message)
        posts = [ (int(FileName.decode(x.name)[0]), x) for x in posts ]
        posts.sort()
        return [ x[1] for x in posts ]


    def get_last_post_id(self):
        ids = [ int(x.name) for x in self.search_resources(cls=Message) ]
        return max(ids)


    # Views
    view = ThreadView()


###########################################################################
# Register
###########################################################################
register_object_class(Thread)
