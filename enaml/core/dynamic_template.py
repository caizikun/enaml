#------------------------------------------------------------------------------
# Copyright (c) 2013, Nucleic Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#------------------------------------------------------------------------------
from atom.api import Dict, List, Str, Tuple, Typed, observe

from enaml.application import ScheduledTask, schedule
from enaml.objectdict import ObjectDict

from .declarative import Declarative, d_
from .template import Template


class DynamicTemplate(Declarative):
    """ An object which dynamically instantiates a template.

    A DynamicTemplate allows a template to be instantiated using the
    runtime scope available to RHS expressions.

    Creating a DynamicTemplate without a parent is a programming error.

    """
    #: The template object to instantiate.
    base = d_(Typed(Template))

    #: The arguments to pass to the template.
    args = d_(Tuple())

    #: The tags to apply to the return values of the template. The tags
    #: are used as the key names for the 'tagged' ObjectDict.
    tags = d_(Tuple(Str()))

    #: The tag to apply to overflow return items from the template.
    startag = d_(Str())

    #: The data keywords to apply to the instantiated items.
    data = d_(Dict())

    #: The object dictionary which maps tag name to tagged object. This
    #: is updated automatically when the template is instantiated.
    tagged = Typed(ObjectDict, ())

    #: The internal task used to collapse template updates.
    _update_task = Typed(ScheduledTask)

    #: The internal list of items generated by the template.
    _items = List(Declarative)

    def initialize(self):
        """ A reimplemented initializer.

        This method will instantiate the template and initialize the
        items for the first time.

        """
        self._refresh()
        for item in self._items:
            item.initialize()
        super(DynamicTemplate, self).initialize()

    def destroy(self):
        """ A reimplemented destructor.

        The DynamicTemplate will release its owned references.

        """
        super(DynamicTemplate, self).destroy()
        del self.data
        del self.tagged
        if self._update_task is not None:
            self._update_task.unschedule()
            del self._update_task
        del self._items

    #--------------------------------------------------------------------------
    # Private API
    #--------------------------------------------------------------------------
    @observe('base', 'args', 'data')
    def _schedule_refresh(self, change):
        """ Schedule an item refresh when the item dependencies change.

        """
        if change['type'] == 'update':
            if self._update_task is None:
                self._update_task = schedule(self._refresh)

    @observe('tags', 'startag')
    def _update_tags(self, change):
        """ Update the tagged object when the tag names change.

        """
        if change['type'] == 'update':
            self._rebuild_tags()

    def _rebuild_tags(self):
        """ Rebuild the tagged object for the current items list.

        """
        tags = self.tags
        startag = self.startag
        items = self._items
        tagged = ObjectDict()
        if tags and len(tags) > len(items):
            msg = 'need more than %d values to unpack'
            raise ValueError(msg % len(items))
        if tags and not startag and len(items) > len(tags):
            raise ValueError('too many values to unpack')
        if tags:
            for name, item in zip(tags, items):
                tagged[name] = item
        if startag:
            tagged[startag] = tuple(items[len(tags):])
        self.tagged = tagged

    def _refresh(self):
        """ Refresh the template instantiation.

        This method will destroy the old items, build the new items,
        and then update the parent object and tagged object.

        """
        self._update_task = None

        if self.base is not None:
            items = self.base(*self.args)(**self.data)
        else:
            items = []

        for old in self._items:
            if not old.is_destroyed:
                old.destroy()

        if len(items) > 0:
            self.parent.insert_children(self, items)

        self._items = items
        self._rebuild_tags()
