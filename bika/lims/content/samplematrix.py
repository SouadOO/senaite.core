# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from AccessControl import ClassSecurityInfo
from Products.Archetypes.public import *
from Products.CMFCore.utils import getToolByName
from bika.lims.config import PROJECTNAME
from bika.lims.content.bikaschema import BikaSchema
from bika.lims.interfaces import IDeactivable
from zope.interface import implements

schema = BikaSchema.copy() + Schema((

))

schema['description'].schemata = 'default'
schema['description'].widget.visible = True

class SampleMatrix(BaseFolder):
    implements(IDeactivable)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    _at_rename_after_creation = True
    def _renameAfterCreation(self, check_auto_id=False):
        from bika.lims.idserver import renameAfterCreation
        renameAfterCreation(self)

registerType(SampleMatrix, PROJECTNAME)

def SampleMatrices(self, instance=None, allow_blank=False):
    instance = instance or self
    bsc = getToolByName(instance, 'bika_setup_catalog')
    items = []
    for sm in bsc(portal_type='SampleMatrix',
                  is_active=True,
                  sort_on = 'sortable_title'):
        items.append((sm.UID, sm.Title))
    items = allow_blank and [['','']] + list(items) or list(items)
    return DisplayList(items)
