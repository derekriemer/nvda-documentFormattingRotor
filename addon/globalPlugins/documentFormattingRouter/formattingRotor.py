from collections import namedtuple
from enum import Enum, auto

import api
import config
import controlTypes
import eventHandler
import ui
from mathPres import MathInteractionNVDAObject as FakeUi
from scriptHandler import script

from . import formattingRotorUtils
from .types import FormattingItem, WorldState
from .fuzzyItemSearch import FuzzyItemSearch

ConfigValidationData = config.ConfigValidationData


def _configKeyExists(configKey: str) -> bool:
    try:
        validateInfo = config.conf.getConfigValidation(["documentFormatting", configKey])
    except Exception:
        return False
    return isinstance(validateInfo, ConfigValidationData)


def _getSpellingErrorsConfigKey() -> str:
    return "reportSpellingErrors2" if _configKeyExists("reportSpellingErrors2") else "reportSpellingErrors"


def _formattingItemIfConfigKeyExists(name: str, configKey: str) -> list[FormattingItem]:
    if not _configKeyExists(configKey):
        return []
    return [FormattingItem(name, configKey)]


class LastChangedState(Enum):
    ITEM = auto()
    CATEGORY = auto()
    SEARCH = auto()
    SETTING = auto()


# There's no generic layeredKeystrokeNVDAObject, but math uses the technique, and we can piggyback.
class FormattingRotor(FakeUi):
    # We don't want NVDA calling this math, and there's no layered keystrokes AFAIK that we can use without reporting some role. Menuitem just has the nice sideaffect that name changes report and it feels native.
    role = controlTypes.role.Role.MENUITEM
    # Translators: Help text for the rotor.
    description = ("""
    Press left/right to cycle through categories, then press
    up/down to select the formatting setting you want. You can also type
    part of the setting,then press up/down to search the settings. Backspace to
    remove typed characters. Press space to cycle through the available
    settings. Press enter to save, or escape to cancel.
    """)

    def _get_name(self):
        item = self.getItem()
        category = self.getCategory()
        state = formattingRotorUtils.makeHumanReadableConfigValue(item.configKey, self.config[item.configKey])
        name = []
        match self.lastChanged:
            case LastChangedState.ITEM | LastChangedState.SEARCH:
                return F"{item.name} {state}"
            case LastChangedState.CATEGORY:
                return f"{category}: {item.name} {state}"
            case LastChangedState.SETTING:
                return state
    _cache_name = False

    ROTOR_CATEGORIES = [
        # Translators: This is a category in the document formatting rotor.
        _("Font"),
        # Translators: This is a category in the document formatting rotor.
        _("Document information"),
        # Translators: This is a category in the document formatting rotor.
        _("Pages and spacing"),
        # Translators: This is a category in the document formatting rotor.
        _("Table information"),
        # Translators: This is a category in the document formatting rotor.
        _("Elements"),
    ]

    ROTOR_ITEMS = [
        [
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Font name"),
                "reportFontName",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Font size"),
                "reportFontSize",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Font attributes"),
                "fontAttributeReporting",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Superscripts and subscripts"),
                "reportSuperscriptsAndSubscripts",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Emphasis"),
                "reportEmphasis",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Highlighted (marked) text"),
                "reportHighlight",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Style"),
                "reportStyle",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Colors"),
                "reportColor",
            ),
        ],
        [
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Notes and comments"),
                "reportComments",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Bookmarks"),
                "reportBookmarks",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Editor revisions"),
                "reportRevisions",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Spelling and grammar errors"),
                _getSpellingErrorsConfigKey(),
            ),
        ],
        [
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Pages"),
                "reportPage",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Line numbers"),
                "reportLineNumber",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor. Options are Off, Speech, Tones, or Both.
                _("Line indentation reporting"),
                "reportLineIndentation",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Ignore blank lines for line indentation reporting"),
                "ignoreBlankLinesForRLI",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Paragraph indentation"),
                "reportParagraphIndentation",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Line spacing"),
                "reportLineSpacing",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Alignment"),
                "reportAlignment",
            ),
        ],
        [
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Tables"),
                "reportTables",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Headers"),
                "reportTableHeaders",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Cell coordinates"),
                "reportTableCellCoords",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Cell borders"),
                "reportCellBorders",
            ),
        ],
        [
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Headings"),
                "reportHeadings",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Links"),
                "reportLinks",
            ),
            *_formattingItemIfConfigKeyExists(
                # Translators: This is an item in the document formatting rotor.
                _("Link type"),
                "reportLinkType",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Graphics"),
                "reportGraphics",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Lists"),
                "reportLists",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Block quotes"),
                "reportBlockQuotes",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Groupings"),
                "reportGroupings",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Landmarks and regions"),
                "reportLandmarks",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Articles"),
                "reportArticles",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Frames"),
                "reportFrames",
            ),
            *_formattingItemIfConfigKeyExists(
                # Translators: This is an item in the document formatting rotor.
                _("Figures and captions"),
                "reportFigures",
            ),
            FormattingItem(
                # Translators: This is an item in the document formatting rotor.
                _("Clickable"),
                "reportClickable",
            ),
        ],
    ]

    buffer = ""
    categoryIndex = 0
    itemIndex = 0
    lastChanged = LastChangedState.CATEGORY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deep copy the config object, so that we only write it explicitly.
        self.config = config.conf['documentFormatting'].copy()
        # This is not the most elegant way to do this, but other methods of doing it require patching getScript.
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            self.bindGesture(F'kb:{letter}', 'addToBuffer')
            self.bindGesture(F'kb:shift+{letter}', 'addToBuffer')

    def reportInitialFocus(self):
        api.getFocusObject().reportFocus()
        self.description = None

    def getItem(self):
        return self.ROTOR_ITEMS[self.categoryIndex][self.itemIndex]

    def getCategory(self):
        return self.ROTOR_CATEGORIES[self.categoryIndex]

    def reportChange(self):
        eventHandler.executeEvent("nameChange", self)

    def reportNoSearchResults(self):
        # Translators: No search results were found in the document formatting rotor.
        ui.message(_("No items match"))

    def searchFromStart(self):
        state = self.fuzzySearch.searchFirst()
        if not state:
            self.reportNoSearchResults()
            return
        self.categoryIndex, self.itemIndex = state.categoryIndex, state.itemIndex
        self.lastChanged = LastChangedState.SEARCH
        self.reportFocus()

    def searchFromEnd(self):
        state = self.fuzzySearch.searchLast()
        if not state:
            self.reportNoSearchResults()
            return
        self.categoryIndex, self.itemIndex = state.categoryIndex, state.itemIndex
        self.lastChanged = LastChangedState.SEARCH
        self.reportFocus()

    @script(gesture="kb:upArrow")
    def script_previousItem(self, gesture):
        if self.buffer:
            state = self.fuzzySearch.searchBackward(
                WorldState(self.categoryIndex, self.itemIndex))
            if not state:
                self.searchFromEnd()
                return
            self.categoryIndex, self.itemIndex = state.categoryIndex, state.itemIndex
            self.lastChanged = LastChangedState.SEARCH
            self.reportFocus()
            return
        self.itemIndex = (self.itemIndex - 1 + len(self.ROTOR_ITEMS[self.categoryIndex])
                          ) % len(self.ROTOR_ITEMS[self.categoryIndex])
        self.lastChanged = LastChangedState.ITEM
        self.reportFocus()

    @script(gesture='kb:downArrow')
    def script_nextItem(self, gesture):
        if self.buffer:
            state = self.fuzzySearch.searchForward(
                WorldState(self.categoryIndex, self.itemIndex))
            if not state:
                # There's no search results after  this index. Reset to the start, and search from there.
                state = self.searchFromStart()
                return
            self.categoryIndex, self.itemIndex = state.categoryIndex, state.itemIndex
            self.lastChanged = LastChangedState.SEARCH
            self.reportFocus()
            return
        self.itemIndex = (
            self.itemIndex + 1) % len(self.ROTOR_ITEMS[self.categoryIndex])
        self.lastChanged = LastChangedState.ITEM
        self.reportFocus()

    @script(gesture="kb:leftArrow")
    def script_previousCategory(self, gesture):
        if self.buffer:
            return
        self.categoryIndex = (
            self.categoryIndex - 1 + len(self.ROTOR_CATEGORIES)) % len(self.ROTOR_CATEGORIES)
        self.itemIndex = 0
        self.lastChanged = LastChangedState.CATEGORY
        self.reportFocus()

    @script(gesture="kb:rightArrow")
    def script_nextCategory(self, gesture):
        if self.buffer:
            return
        self.categoryIndex = (self.categoryIndex +
                              1) % len(self.ROTOR_CATEGORIES)
        self.itemIndex = 0
        self.lastChanged = LastChangedState.CATEGORY
        self.reportFocus()

    @script(gesture="kb:space")
    def script_cycleSetting(self, gesture):
        formattingItem = self.getItem()
        validateInfo = config.conf.getConfigValidation(
            ['documentFormatting', formattingItem.configKey])
        match validateInfo:
            case ConfigValidationData(validationFuncName='boolean'):
                self.config[formattingItem.configKey] = not self.config[formattingItem.configKey]
            case ConfigValidationData(validationFuncName='integer'):
                self.config[formattingItem.configKey] = formattingRotorUtils.getNextConfigValue(
                    formattingItem.configKey,
                    self.config[formattingItem.configKey],
                    validateInfo.args,
                )
            case _:
                # There shouldn't be any str, or other funcs.
                pass
        self.lastChanged = LastChangedState.SETTING
        self.reportFocus()

    def script_addToBuffer(self, gesture):
        if not gesture.isCharacter:
            return
        key = gesture.mainKeyName
        self.buffer += key
        self.fuzzySearch = FuzzyItemSearch(self.buffer, self.ROTOR_ITEMS)
        self.searchFromStart()

    @script(gesture="kb:enter")
    def script_save(self, other):
        config.conf['documentFormatting'] = self.config
        # Translators: Configuration saved for document formatting rotor.
        ui.message(_("Config saved"))
        eventHandler.executeEvent("gainFocus", self.parent)

    @script(gesture='kb:backspace')
    def script_remove(self, gesture):
        if not self.buffer:
            ui.message('nothing to delete')
            return
        ui.message('%s deleted' % self.buffer[-1])
        self.buffer = self.buffer[:-1]
        self.fuzySearch = FuzzyItemSearch(self.buffer, self.ROTOR_ITEMS)
        self.searchFromStart()
