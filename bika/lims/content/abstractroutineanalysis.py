# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE
#
# Copyright 2018 by it's authors.
# Some rights reserved. See LICENSE.rst, CONTRIBUTORS.rst.

from AccessControl import ClassSecurityInfo
from datetime import timedelta
from Products.Archetypes.Field import BooleanField, FixedPointField, \
    StringField
from Products.Archetypes.Schema import Schema
from Products.ATContentTypes.utils import DT2dt, dt2DT
from bika.lims import api
from bika.lims import bikaMessageFactory as _
from bika.lims.browser.fields import UIDReferenceField
from bika.lims.browser.widgets import DecimalWidget
from bika.lims.catalog.indexers.baseanalysis import sortable_title
from bika.lims.content.abstractanalysis import AbstractAnalysis
from bika.lims.content.abstractanalysis import schema
from bika.lims.content.analysisspec import ResultsRangeDict
from bika.lims.content.reflexrule import doReflexRuleAction
from bika.lims.interfaces import IAnalysis, IRoutineAnalysis, ICancellable
from bika.lims.interfaces.analysis import IRequestAnalysis
from bika.lims.workflow import getTransitionDate
from zope.interface import implements


# TODO Remove in >v1.3.0 - This is kept for backwards-compatibility
# The physical sample partition linked to the Analysis.
SamplePartition = UIDReferenceField(
    'SamplePartition',
    required=0,
    allowed_types=('SamplePartition',)
)

# True if the analysis is created by a reflex rule
IsReflexAnalysis = BooleanField(
    'IsReflexAnalysis',
    default=False,
    required=0
)

# This field contains the original analysis which was reflected
OriginalReflexedAnalysis = UIDReferenceField(
    'OriginalReflexedAnalysis',
    required=0,
    allowed_types=('Analysis',)
)

# This field contains the analysis which has been reflected following
# a reflex rule
ReflexAnalysisOf = UIDReferenceField(
    'ReflexAnalysisOf',
    required=0,
    allowed_types=('Analysis',)
)

# Which is the Reflex Rule action that has created this analysis
ReflexRuleAction = StringField(
    'ReflexRuleAction',
    required=0,
    default=0
)

# Which is the 'local_id' inside the reflex rule
ReflexRuleLocalID = StringField(
    'ReflexRuleLocalID',
    required=0,
    default=0
)

# Reflex rule triggered actions which the current analysis is responsible for.
# Separated by '|'
ReflexRuleActionsTriggered = StringField(
    'ReflexRuleActionsTriggered',
    required=0,
    default=''
)

# The actual uncertainty for this analysis' result, populated when the result
# is submitted.
Uncertainty = FixedPointField(
    'Uncertainty',
    precision=10,
    widget=DecimalWidget(
        label=_("Uncertainty")
    )
)
# This field keep track if the field hidden has been set manually or not. If
# this value is false, the system will assume the visibility of this analysis
# in results report will depend on the value set at AR, Profile or Template
# levels (see AnalysisServiceSettings fields in AR). If the value for this
# field is set to true, the system will assume the visibility of the analysis
# will only depend on the value set for the field Hidden (bool).
HiddenManually = BooleanField(
    'HiddenManually',
    default=False,
)


schema = schema.copy() + Schema((
    IsReflexAnalysis,
    OriginalReflexedAnalysis,
    ReflexAnalysisOf,
    ReflexRuleAction,
    ReflexRuleActionsTriggered,
    ReflexRuleLocalID,
    SamplePartition,
    Uncertainty,
    HiddenManually,
))


class AbstractRoutineAnalysis(AbstractAnalysis):
    implements(IAnalysis, IRequestAnalysis, IRoutineAnalysis, ICancellable)
    security = ClassSecurityInfo()
    displayContentsTab = False
    schema = schema

    @security.public
    def getRequest(self):
        """Returns the Analysis Request this analysis belongs to.
        Delegates to self.aq_parent
        """
        ar = self.aq_parent
        return ar

    @security.public
    def getRequestID(self):
        """Used to populate catalog values.
        Returns the ID of the parent analysis request.
        """
        ar = self.getRequest()
        if ar:
            return ar.getId()

    @security.public
    def getRequestUID(self):
        """Returns the UID of the parent analysis request.
        """
        ar = self.getRequest()
        if ar:
            return ar.UID()

    @security.public
    def getRequestURL(self):
        """Returns the url path of the Analysis Request object this analysis
        belongs to. Returns None if there is no Request assigned.
        :return: the Analysis Request URL path this analysis belongs to
        :rtype: str
        """
        request = self.getRequest()
        if request:
            return request.absolute_url_path()

    @security.public
    def getClientTitle(self):
        """Used to populate catalog values.
        Returns the Title of the client for this analysis' AR.
        """
        request = self.getRequest()
        if request:
            client = request.getClient()
            if client:
                return client.Title()

    @security.public
    def getClientUID(self):
        """Used to populate catalog values.
        Returns the UID of the client for this analysis' AR.
        """
        request = self.getRequest()
        if request:
            client = request.getClient()
            if client:
                return client.UID()

    @security.public
    def getClientURL(self):
        """This method is used to populate catalog values
        Returns the URL of the client for this analysis' AR.
        """
        request = self.getRequest()
        if request:
            client = request.getClient()
            if client:
                return client.absolute_url_path()

    @security.public
    def getClientOrderNumber(self):
        """Used to populate catalog values.
        Returns the ClientOrderNumber of the associated AR
        """
        request = self.getRequest()
        if request:
            return request.getClientOrderNumber()

    @security.public
    def getDateReceived(self):
        """Used to populate catalog values.
        Returns the date the Analysis Request this analysis belongs to was
        received. If the analysis was created after, then returns the date
        the analysis was created.
        """
        request = self.getRequest()
        if request:
            ar_date = request.getDateReceived()
            if ar_date and self.created() > ar_date:
                return self.created()
            return ar_date
        return None

    @security.public
    def isSampleReceived(instance):
        """Returns whether if the Analysis Request this analysis comes from has
        been received or not
        """
        return instance.getDateReceived() and True or False

    @security.public
    def getDatePublished(self):
        """Used to populate catalog values.
        Returns the date on which the "publish" transition was invoked on this
        analysis.
        """
        return getTransitionDate(self, 'publish', return_as_datetime=True)

    @security.public
    def getDateSampled(self):
        """Returns the date when the Sample was Sampled
        """
        request = self.getRequest()
        if request:
            return request.getDateSampled()
        return None

    @security.public
    def isSampleSampled(instance):
        """Returns whether if the Analysis Request this analysis comes from has
        been received or not
        """
        return instance.getDateSampled() and True or False

    @security.public
    def getStartProcessDate(self):
        """Returns the date time when the analysis request the analysis belongs
        to was received. If the analysis request hasn't yet been received,
        returns None
        Overrides getStartProcessDateTime from the base class
        :return: Date time when the analysis is ready to be processed.
        :rtype: DateTime
        """
        return self.getDateReceived()

    @security.public
    def getSamplePoint(self):
        request = self.getRequest()
        if request:
            return request.getSamplePoint()
        return None

    @security.public
    def getSamplePointUID(self):
        """Used to populate catalog values.
        """
        sample_point = self.getSamplePoint()
        if sample_point:
            return api.get_uid(sample_point)

    @security.public
    def getDueDate(self):
        """Used to populate getDueDate index and metadata.
        This calculates the difference between the time the analysis processing
        started and the maximum turnaround time. If the analysis has no
        turnaround time set or is not yet ready for proces, returns None
        """
        tat = self.getMaxTimeAllowed()
        if not tat:
            return None
        start = self.getStartProcessDate()
        if not start:
            return None
        return dt2DT(DT2dt(start) + timedelta(minutes=api.to_minutes(**tat)))

    @security.public
    def getSampleType(self):
        request = self.getRequest()
        if request:
            return request.getSampleType()
        return None

    @security.public
    def getSampleTypeUID(self):
        """Used to populate catalog values.
        """
        sample_type = self.getSampleType()
        if sample_type:
            return api.get_uid(sample_type)

    @security.public
    def getBatchUID(self):
        """This method is used to populate catalog values
        """
        request = self.getRequest()
        if request:
            return request.getBatchUID()

    @security.public
    def getAnalysisRequestPrintStatus(self):
        """This method is used to populate catalog values
        """
        request = self.getRequest()
        if request:
            return request.getPrinted()

    @security.public
    def getResultsRange(self):
        """Returns the valid result range for this routine analysis based on the
        results ranges defined in the Analysis Request this routine analysis is
        assigned to.

        A routine analysis will be considered out of range if it result falls
        out of the range defined in "min" and "max". If there are values set for
        "warn_min" and "warn_max", these are used to compute the shoulders in
        both ends of the range. Thus, an analysis can be out of range, but be
        within shoulders still.
        :return: A dictionary with keys "min", "max", "warn_min" and "warn_max"
        :rtype: dict
        """
        specs = ResultsRangeDict()
        analysis_request = self.getRequest()
        if not analysis_request:
            return specs

        keyword = self.getKeyword()
        ar_ranges = analysis_request.getResultsRange()
        # Get the result range that corresponds to this specific analysis
        an_range = [rr for rr in ar_ranges if rr.get('keyword', '') == keyword]
        return an_range and an_range[0] or specs

    @security.public
    def getSiblings(self, retracted=False):
        """
        Return the siblings analyses, using the parent to which the current
        analysis belongs to as the source
        :param retracted: If false, retracted/rejected siblings are dismissed
        :type retracted: bool
        :return: list of siblings for this analysis
        :rtype: list of IAnalysis
        """
        raise NotImplementedError("getSiblings is not implemented.")

    @security.public
    def getDependents(self, retracted=False):
        """
        Returns a list of siblings who depend on us to calculate their result.
        :param retracted: If false, retracted/rejected dependents are dismissed
        :type retracted: bool
        :return: Analyses the current analysis depends on
        :rtype: list of IAnalysis
        """
        dependents = []
        for sibling in self.getSiblings(retracted=retracted):
            calculation = sibling.getCalculation()
            if not calculation:
                continue
            depservices = calculation.getDependentServices()
            dep_keywords = [dep.getKeyword() for dep in depservices]
            if self.getKeyword() in dep_keywords:
                dependents.append(sibling)
        return dependents

    @security.public
    def getDependencies(self, retracted=False):
        """
        Return a list of siblings who we depend on to calculate our result.
        :param retracted: If false retracted/rejected dependencies are dismissed
        :type retracted: bool
        :return: Analyses the current analysis depends on
        :rtype: list of IAnalysis
        """
        calc = self.getCalculation()
        if not calc:
            return []

        dependencies = []
        for sibling in self.getSiblings(retracted=retracted):
            # We get all analyses that depend on me, also if retracted (maybe
            # I am one of those that are retracted!)
            deps = sibling.getDependents(retracted=True)
            deps = [dep.UID() for dep in deps]
            if self.UID() in deps:
                dependencies.append(sibling)
        return dependencies

    @security.public
    def getPrioritySortkey(self):
        """
        Returns the key that will be used to sort the current Analysis, from
        most prioritary to less prioritary.
        :return: string used for sorting
        """
        analysis_request = self.getRequest()
        if analysis_request is None:
            return None
        ar_sort_key = analysis_request.getPrioritySortkey()
        ar_id = analysis_request.getId().lower()
        title = sortable_title(self)
        if callable(title):
            title = title()
        return '{}.{}.{}'.format(ar_sort_key, ar_id, title)

    @security.public
    def getHidden(self):
        """ Returns whether if the analysis must be displayed in results
        reports or not, as well as in analyses view when the user logged in
        is a Client Contact.

        If the value for the field HiddenManually is set to False, this function
        will delegate the action to the method getAnalysisServiceSettings() from
        the Analysis Request.

        If the value for the field HiddenManually is set to True, this function
        will return the value of the field Hidden.
        :return: true or false
        :rtype: bool
        """
        if self.getHiddenManually():
            return self.getField('Hidden').get(self)
        request = self.getRequest()
        if request:
            service_uid = self.getServiceUID()
            ar_settings = request.getAnalysisServiceSettings(service_uid)
            return ar_settings.get('hidden', False)
        return False

    @security.public
    def setHidden(self, hidden):
        """ Sets if this analysis must be displayed or not in results report and
        in manage analyses view if the user is a lab contact as well.

        The value set by using this field will have priority over the visibility
        criteria set at Analysis Request, Template or Profile levels (see
        field AnalysisServiceSettings from Analysis Request. To achieve this
        behavior, this setter also sets the value to HiddenManually to true.
        :param hidden: true if the analysis must be hidden in report
        :type hidden: bool
        """
        self.setHiddenManually(True)
        self.getField('Hidden').set(self, hidden)

    @security.public
    def setReflexAnalysisOf(self, analysis):
        """Sets the analysis that has been reflexed in order to create this
        one, but if the analysis is the same as self, do nothing.
        :param analysis: an analysis object or UID
        """
        if not analysis or analysis.UID() == self.UID():
            pass
        else:
            self.getField('ReflexAnalysisOf').set(self, analysis)

    @security.public
    def addReflexRuleActionsTriggered(self, text):
        """This function adds a new item to the string field
        ReflexRuleActionsTriggered. From the field: Reflex rule triggered
        actions from which the current analysis is responsible of. Separated
        by '|'
        :param text: is a str object with the format '<UID>.<rulename>' ->
        '123354.1'
        """
        old = self.getReflexRuleActionsTriggered()
        self.setReflexRuleActionsTriggered(old + text + '|')

    @security.public
    def getOriginalReflexedAnalysisUID(self):
        """
        Returns the uid of the original reflexed analysis.
        """
        original = self.getOriginalReflexedAnalysis()
        if original:
            return original.UID()
        return ''

    @security.private
    def _reflex_rule_process(self, wf_action):
        """This function does all the reflex rule process.
        :param wf_action: is a string containing the workflow action triggered
        """
        # Check out if the analysis has any reflex rule bound to it.
        # First we have get the analysis' method because the Reflex Rule
        # objects are related to a method.
        a_method = self.getMethod()
        if not a_method:
            return
        # After getting the analysis' method we have to get all Reflex Rules
        # related to that method.
        all_rrs = a_method.getBackReferences('ReflexRuleMethod')
        if not all_rrs:
            return
        # Once we have all the Reflex Rules with the same method as the
        # analysis has, it is time to get the rules that are bound to the
        # same analysis service that is using the analysis.
        for rule in all_rrs:
            if not api.is_active(rule):
                continue
            # Getting the rules to be done from the reflex rule taking
            # in consideration the analysis service, the result and
            # the state change
            action_row = rule.getActionReflexRules(self, wf_action)
            # Once we have the rules, the system has to execute its
            # instructions if the result has the expected result.
            doReflexRuleAction(self, action_row)
