# -*- coding: UTF-8 -*-
# Copyright (C) 2005-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2006-2008 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2007 Sylvain Taverne <sylvain@itaapy.com>
# Copyright (C) 2007-2008 Henry Obein <henry@itaapy.com>
# Copyright (C) 2008 Matthieu France <matthieu@itaapy.com>
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
from itools.core import freeze
from itools.csv import Property
from itools.datatypes import Unicode, String, Integer, Boolean, DateTime
from itools.http import get_context
from itools.log import log_error
from itools.uri import Path
from itools.web import Resource
from itools.xapian import CatalogAware, PhraseQuery

# Import from ikaaro
from metadata import Metadata
from registry import register_field, register_resource_class
from resource_views import DBResource_Edit, DBResource_Backlinks
from resource_views import DBResource_AddImage, DBResource_AddLink
from resource_views import DBResource_AddMedia, LoginView, LogoutView
from revisions_views import DBResource_CommitLog, DBResource_Changes
from workflow import WorkflowAware
from views_new import NewInstance


class IResource(Resource):

    class_views = []
    context_menus = []


    @property
    def parent(self):
        # Special case: the root
        if not self.path:
            return None
        path = self.path[:-1]
        return self.context.get_resource(path)


    @property
    def name(self):
        # Special case: the root
        if not self.path:
            return None

        return self.path[-1]


    def get_site_root(self):
        from website import WebSite
        resource = self
        while not isinstance(resource, WebSite):
            resource = resource.parent
        return resource


    def get_default_view_name(self):
        views = self.class_views
        if not views:
            return None
        context = get_context()
        ac = self.get_access_control()
        for view_name in views:
            view = getattr(self, view_name, None)
            if ac.is_access_allowed(context, self, view):
                return view_name
        return views[0]


    def get_context_menus(self):
        return self.context_menus


    ########################################################################
    # Properties
    ########################################################################
    @classmethod
    def get_property_datatype(cls, name, default=String):
        return default


    def _get_property(self, name, language=None):
        return None


    def get_property(self, name, language=None):
        """Return the property value for the given property name.
        """
        property = self._get_property(name, language=language)
        # Default
        if not property:
            datatype = self.get_property_datatype(name)
            return datatype.get_default()

        # Multiple
        if type(property) is list:
            return [ x.value for x in property ]

        # Simple
        return property.value


    def get_title(self):
        return unicode(self.name)


    def get_page_title(self):
        return self.get_title()


    ########################################################################
    # Icons
    ########################################################################
    @classmethod
    def get_class_icon(cls, size=16):
        icon = getattr(cls, 'class_icon%s' % size, None)
        if icon is None:
            return None
        return '/ui/%s' % icon


    @classmethod
    def get_resource_icon(cls, size=16):
        icon = getattr(cls, 'icon%s' % size, None)
        if icon is None:
            return cls.get_class_icon(size)
        return ';icon%s' % size


    def get_method_icon(self, view, size='16x16', **kw):
        icon = getattr(view, 'icon', None)
        if icon is None:
            return None
        if callable(icon):
            icon = icon(self, **kw)
        return '/ui/icons/%s/%s' % (size, icon)


    ########################################################################
    # User interface
    ########################################################################
    def get_views(self):
        context = get_context()
        ac = self.get_access_control()
        for name in self.class_views:
            view_name = name.split('?')[0]
            view = self.get_view(view_name)
            if ac.is_access_allowed(context, self, view):
                yield name, view



###########################################################################
# Database resources
###########################################################################
class DBResourceMetaclass(type):

    def __new__(mcs, name, bases, dict):
        cls = type.__new__(mcs, name, bases, dict)
        if 'class_id' in dict:
            register_resource_class(cls)
        for name, dt in cls.class_schema.iteritems():
            if getattr(dt, 'indexed', False) or getattr(dt, 'stored', False):
                register_field(name, dt)
        return cls



class DBResource(CatalogAware, IResource):

    __metaclass__ = DBResourceMetaclass

    def __init__(self, metadata=None, brain=None):
        self._handler = None

        # Case 1. The brain
        if brain:
            if metadata:
                raise ValueError, 'expected brain or metadata, not both'
            self.brain = brain
        # Case 2. The metadata
        else:
            if not metadata:
                raise ValueError, 'expected brain or metadata, got none'
            self.brain = None
            self.metadata = metadata


    def __getattr__(self, name):
        if name == 'metadata':
            path = self.path
            metadata = self.context._get_metadata(str(path), path)
            self.metadata = metadata
            return metadata

        msg = "'%s' object has no attribute '%s'"
        raise AttributeError, msg % (self.__class__.__name__, name)


    def init_resource(self, **kw):
        """Return a Metadata object with sensible default values.
        """
        metadata = self.metadata
        # Properties
        for key in kw:
            value = kw[key]
            if type(value) is dict:
                for lang in value:
                    property = Property(value[lang], lang=lang)
                    metadata._set_property(key, property)
            else:
                metadata._set_property(key, value)

        # Workflow State (default)
        if kw.get('state') is None and isinstance(self, WorkflowAware):
            datatype = self.get_property_datatype('state')
            state = datatype.get_default()
            if state is None:
                state  = self.workflow.initstate
            metadata._set_property('state', state)


    def get_handler(self):
        if self._handler is None:
            cls = self.class_handler
            database = self.metadata.database
            key = self.metadata.key[:-len('.metadata')]
            if database.has_handler(key):
                handler = database.get_handler(key, cls=cls)
            else:
                handler = cls()
                database.push_phantom(key, handler)
            self._handler = handler
        return self._handler

    handler = property(get_handler)


    def load_handlers(self):
        self.get_handlers()


    ########################################################################
    # Metadata
    ########################################################################
    Multilingual = Unicode(multilingual=True)
    class_schema = freeze({
        # Metadata
        'version': String(source='metadata'),
        'mtime': DateTime(source='metadata', indexed=True, stored=True),
        'last_author': String(source='metadata', indexed=False, stored=True),
        'title': Multilingual(source='metadata', indexed=True, stored=True),
        'description': Multilingual(source='metadata', indexed=True),
        'subject': Multilingual(source='metadata', indexed=True),
        # Key & class id
        'abspath': String(key_field=True, indexed=True, stored=True),
        'format': String(indexed=True, stored=True),
        # Folder's view
        'parent_path': String(indexed=True),
        'name': String(stored=True, indexed=True),
        'size': Integer(stored=True, indexed=False),
        # Referential integrity
        'links': String(multiple=True, indexed=True),
        # Full text search
        'text': Unicode(indexed=True),
        # Various classifications
        'is_role_aware': Boolean(indexed=True),
        'is_folder': Boolean(indexed=True),
        'is_image': Boolean(indexed=True),
        })


    @classmethod
    def get_property_datatype(cls, name, default=String):
        datatype = cls.class_schema.get(name)
        if datatype and getattr(datatype, 'source', None) == 'metadata':
            return datatype
        return default


    def has_property(self, name, language=None):
        return self.metadata.has_property(name, language=language)


    def _get_property(self, name, language=None):
        return self.metadata.get_property(name, language=language)


    def set_property(self, name, value, language=None):
        get_context().change_resource(self)
        if language:
            value = Property(value, lang=language)
        self.metadata.set_property(name, value)


    def del_property(self, name):
        get_context().database.change_resource(self)
        self.metadata.del_property(name)


    ########################################################################
    # Versioning
    ########################################################################
    def get_files_to_archive(self, content=False):
        raise NotImplementedError


    def get_revisions(self, n=None, content=False):
        files = self.get_files_to_archive(content)
        database = get_context().database
        return database.get_revisions(files, n)


    def get_last_revision(self):
        files = self.get_files_to_archive()
        database = get_context().database
        return database.get_last_revision(files)


    def get_owner(self):
        revisions = self.get_revisions()
        if not revisions:
            return None
        return revisions[-1]['username']


    def get_last_author(self):
        revision = self.get_last_revision()
        return revision['username'] if revision else None


    def get_mtime(self):
        revision = self.get_last_revision()
        return revision['date'] if revision else None


    ########################################################################
    # Indexing
    ########################################################################
    @property
    def abspath(self):
        abspath = self.get_canonical_path()
        return str(abspath)


    @property
    def format(self):
        return self.metadata.format


    @property
    def title(self):
        languages = self.get_site_root().get_property('website_languages')
        return dict([ (x, self.get_title(language=x)) for x in languages ])


    @property
    def subject(self):
        languages = self.get_site_root().get_property('website_languages')
        get = self.get_property
        return dict([ (x, get('subject', language=x)) for x in languages ])


    @property
    def description(self):
        languages = self.get_site_root().get_property('website_languages')
        get = self.get_property
        return dict([ (x, get('description', language=x)) for x in languages ])


    @property
    def text(self):
        context = get_context()
        try:
            server = context.server
        except AttributeError:
            return None

        if server is None or not server.index_text:
            return None

        return self.to_text()


    def to_text(self):
        """This function must return:
           1) An unicode text.
            or
           2) A dict in a multilingual context:
              {'fr': u'....',
               'en': u'....' ....}
        """
        return None


    @property
    def links(self):
        return self.get_links()


    @property
    def parent_path(self):
        abspath = self.get_canonical_path()
        if not abspath:
            return None
        return str(abspath[:-1])


    is_folder = False
    is_image = False
    is_role_aware = False

    ########################################################################
    # API
    ########################################################################
    def get_handlers(self):
        """Return all the handlers attached to this resource, except the
        metadata.
        """
        return [self.handler]


    def rename_handlers(self, new_name):
        """Consider we want to rename this resource to the given 'new_name',
        return the old a new names for all the attached handlers (except the
        metadata).

        This method is required by the "move_resource" method.
        """
        return [(self.name, new_name)]


    def _on_move_resource(self, source):
        """This method updates the links from/to other resources.  It is
        called when the resource has been moved and/or renamed.

        This method is called by 'Database._before_commit', the 'source'
        parameter is the place the resource has been moved from.
        """
        # (1) Update links to other resources
        self.update_relative_links(Path(source))

        # (2) Update resources that link to me
        database = get_context().database
        target = self.get_canonical_path()
        query = PhraseQuery('links', source)
        results = database.catalog.search(query).get_documents()
        for result in results:
            path = result.abspath
            path = database.resources_old2new.get(path, path)
            resource = self.get_resource(path)
            resource.update_links(source, target)


    def update_links(self, source, target):
        """The resource identified by 'source' is going to be moved to
        'target'.  Update our links to it.

        The parameters 'source' and 'target' are absolute 'Path' objects.
        """


    def update_relative_links(self, target):
        """Update the relative links coming out from this resource, so they
        are not broken when this resource moves to 'target'.
        """


    def get_links(self):
        return []


    ########################################################################
    # Upgrade
    ########################################################################
    def get_next_versions(self):
        cls_version = self.class_version
        obj_version = self.metadata.version
        # Set zero version if the resource does not have a version
        if obj_version is None:
            obj_version = '00000000'

        # Get all the version numbers
        versions = []
        for cls in self.__class__.mro():
            for name in cls.__dict__.keys():
                if not name.startswith('update_'):
                    continue
                kk, version = name.split('_', 1)
                if len(version) != 8:
                    continue
                try:
                    int(version)
                except ValueError:
                    continue
                if version > obj_version and version <= cls_version:
                    versions.append(version)

        versions.sort()
        return versions


    def update(self, version):
        # We don't check the version is good
        getattr(self, 'update_%s' % version)()
        metadata = self.metadata
        metadata.set_changed()
        metadata.version = version


    ########################################################################
    # User interface
    ########################################################################
    def get_title(self, language=None):
        title = self.get_property('title', language=language)
        if title:
            return title
        # Fallback to the resource's name
        return unicode(self.name)


    def get_content_language(self, context, languages=None):
        if languages is None:
            site_root = self.get_site_root()
            languages = site_root.get_property('website_languages')

        # The 'content_language' query parameter has preference
        language = context.get_query_value('content_language')
        if language in languages:
            return language

        # Language negotiation
        return context.accept_language.select_language(languages)


    ########################################################################
    # Cut & Paste Resources
    ########################################################################
    def can_paste(self, source):
        """Is the source resource can be pasted into myself.
        Question is "can I handle this type of resource?"
        """
        raise NotImplementedError


    def can_paste_into(self, target):
        """Can I be pasted into the given target.
        Question is "Is this container compatible with myself?"
        """
        # No restriction by default. Functional modules will want to keep
        # their specific resources for them.
        return True


    # Views
    new_instance = NewInstance()
    login = LoginView()
    logout = LogoutView()
    edit = DBResource_Edit()
    add_image = DBResource_AddImage()
    add_link = DBResource_AddLink()
    add_media = DBResource_AddMedia()
    commit_log = DBResource_CommitLog()
    changes = DBResource_Changes()
    backlinks = DBResource_Backlinks()

