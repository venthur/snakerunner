#!/usr/bin/env python
"""The main script for the Snakerunner profile viewer"""

import sys
import os
import logging
import traceback
import configparser
from gettext import gettext as _
from pathlib import Path

import wx
import wx.py

from snakerunner import squaremap
from snakerunner import pstatsloader, pstatsadapter
from snakerunner import listviews

if sys.platform == 'win32':
    windows = True
else:
    windows = False
if sys.platform == 'darwin':
    osx = True
else:
    osx = False

log = logging.getLogger(__name__)

ID_OPEN = wx.NewIdRef(count=1)
ID_EXIT = wx.NewIdRef(count=1)

ID_TREE_TYPE = wx.NewIdRef(count=1)

ID_PERCENTAGE_VIEW = wx.NewIdRef(count=1)
ID_ROOT_VIEW = wx.NewIdRef(count=1)
ID_BACK_VIEW = wx.NewIdRef(count=1)
ID_UP_VIEW = wx.NewIdRef(count=1)
ID_DEEPER_VIEW = wx.NewIdRef(count=1)
ID_SHALLOWER_VIEW = wx.NewIdRef(count=1)
ID_MORE_SQUARE = wx.NewIdRef(count=1)

PROFILE_VIEW_COLUMNS = [
    listviews.ColumnDefinition(
        name=_('Name'),
        attribute='name',
        defaultOrder=True,
        targetWidth=50,
    ),
    listviews.ColumnDefinition(
        name=_('Calls'),
        attribute='calls',
        defaultOrder=False,
        targetWidth=50,
    ),
    listviews.ColumnDefinition(
        name=_('RCalls'),
        attribute='recursive',
        defaultOrder=False,
        targetWidth=40,
    ),
    listviews.ColumnDefinition(
        name=_('Local'),
        attribute='local',
        format='%0.5f',
        defaultOrder=False,
        percentPossible=True,
        targetWidth=50,
    ),
    listviews.ColumnDefinition(
        name=_('/Call'),
        attribute='localPer',
        defaultOrder=False,
        format='%0.5f',
        targetWidth=50,
    ),
    listviews.ColumnDefinition(
        name=_('Cum'),
        attribute='cumulative',
        format='%0.5f',
        percentPossible=True,
        targetWidth=50,
        defaultOrder=False,
        sortDefault=True,
    ),
    listviews.ColumnDefinition(
        name=_('/Call'),
        attribute='cumulativePer',
        format='%0.5f',
        defaultOrder=False,
        targetWidth=50,
    ),
    listviews.ColumnDefinition(
        name=_('File'),
        attribute='filename',
        sortOn=('filename', 'lineno', 'directory',),
        defaultOrder=True,
        targetWidth=70,
    ),
    listviews.ColumnDefinition(
        name=_('Line'),
        attribute='lineno',
        sortOn=('filename', 'lineno', 'directory'),
        defaultOrder=True,
        targetWidth=30,
    ),
    listviews.ColumnDefinition(
        name=_('Directory'),
        attribute='directory',
        sortOn=('directory', 'filename', 'lineno'),
        defaultOrder=True,
        targetWidth=90,
    ),
]


class MainFrame(wx.Frame):
    """The root frame for the display of a single data-set"""
    loader = None
    percentageView = False

    historyIndex = -1
    activated_node = None
    selected_node = None

    viewType = 'functions'
    viewTypeTool = None

    TBFLAGS = (
        wx.TB_HORIZONTAL
        # | wx.NO_BORDER
        | wx.TB_FLAT
    )

    def __init__(
        self, parent=None, id=-1,
        title=_("Run Snake Run"),
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=wx.DEFAULT_FRAME_STYLE | wx.CLIP_CHILDREN,
        name=_("Snakerunner"),
        config_parser=None,
    ):
        """Initialise the Frame"""
        wx.Frame.__init__(self, parent, id, title, pos, size, style, name)
        # TODO: toolbar for back, up, root, directory-view, percentage view
        self.adapter = pstatsadapter.PStatsAdapter()
        self.CreateControls(config_parser)
        self.history = []  # set of (activated_node, selected_node) pairs...
        icon = self.LoadRSRIcon()
        if icon:
            self.SetIcon(icon)

    def CreateControls(self, config_parser):
        """Create our sub-controls"""
        self.CreateMenuBar()
        self.SetupToolBar()
        self.CreateStatusBar()
        self.leftSplitter = wx.SplitterWindow(
            self
        )
        self.rightSplitter = wx.SplitterWindow(
            self.leftSplitter
        )
        self.listControl = listviews.DataView(
            self.leftSplitter,
            columns=PROFILE_VIEW_COLUMNS,
            name='mainlist',
        )
        self.squareMap = squaremap.SquareMap(
            self.rightSplitter,
            padding=6,
            labels=True,
            adapter=self.adapter,
            square_style=True,
        )
        self.tabs = wx.Notebook(
            self.rightSplitter,
        )

        self.CreateSourceWindow(self.tabs)

        self.calleeListControl = listviews.DataView(
            self.tabs,
            columns=PROFILE_VIEW_COLUMNS,
            name='callee',
        )
        self.allCalleeListControl = listviews.DataView(
            self.tabs,
            columns=PROFILE_VIEW_COLUMNS,
            name='allcallee',
        )
        self.allCallerListControl = listviews.DataView(
            self.tabs,
            columns=PROFILE_VIEW_COLUMNS,
            name='allcaller',
        )
        self.callerListControl = listviews.DataView(
            self.tabs,
            columns=PROFILE_VIEW_COLUMNS,
            name='caller',
        )
        self.ProfileListControls = [
            self.listControl,
            self.calleeListControl,
            self.allCalleeListControl,
            self.callerListControl,
            self.allCallerListControl,
        ]
        self.tabs.AddPage(self.calleeListControl, _('Callees'), True)
        self.tabs.AddPage(self.allCalleeListControl, _('All Callees'), False)
        self.tabs.AddPage(self.callerListControl, _('Callers'), False)
        self.tabs.AddPage(self.allCallerListControl, _('All Callers'), False)
        self.tabs.AddPage(self.sourceCodeControl, _('Source Code'), False)
        # calculate size as proportional value for initial display...
        self.LoadState(config_parser)
        width, height = self.GetSize()
        rightsplit = 2 * (height // 3)
        leftsplit = width // 3
        self.rightSplitter.SplitHorizontally(self.squareMap, self.tabs,
                                             rightsplit)
        self.leftSplitter.SplitVertically(self.listControl, self.rightSplitter,
                                          leftsplit)
        self.squareMap.Bind(squaremap.EVT_SQUARE_HIGHLIGHTED,
                            self.OnSquareHighlightedMap)
        self.listControl.Bind(squaremap.EVT_SQUARE_SELECTED,
                              self.OnSquareSelectedList)
        self.squareMap.Bind(squaremap.EVT_SQUARE_SELECTED,
                            self.OnSquareSelectedMap)
        self.squareMap.Bind(squaremap.EVT_SQUARE_ACTIVATED,
                            self.OnNodeActivated)
        for control in self.ProfileListControls:
            control.Bind(squaremap.EVT_SQUARE_ACTIVATED, self.OnNodeActivated)
            control.Bind(squaremap.EVT_SQUARE_HIGHLIGHTED,
                         self.OnSquareHighlightedList)
        self.moreSquareViewItem.Check(self.squareMap.square_style)

    def CreateMenuBar(self):
        """Create our menu-bar for triggering operations"""
        menubar = wx.MenuBar()
        menu = wx.Menu()
        menu.Append(ID_OPEN, _('&Open Profile'), _('Open a cProfile file'))
        menu.AppendSeparator()
        menu.Append(ID_EXIT, _('&Close'), _('Close this Snakerunner window'))
        menubar.Append(menu, _('&File'))
        menu = wx.Menu()
#        self.packageMenuItem = menu.AppendCheckItem(
#            ID_PACKAGE_VIEW, _('&File View'),
#            _('View time spent by package/module')
#        )
        self.percentageMenuItem = menu.AppendCheckItem(
            ID_PERCENTAGE_VIEW, _('&Percentage View'),
            _('View time spent as percent of overall time')
        )
        self.rootViewItem = menu.Append(
            ID_ROOT_VIEW, _('&Root View (Home)'),
            _('View the root of the tree')
        )
        self.backViewItem = menu.Append(
            ID_BACK_VIEW, _('&Back'), _('Go back in your viewing history')
        )
        self.upViewItem = menu.Append(
            ID_UP_VIEW, _('&Up'),
            _('Go "up" to the parent of this node with the largest cumulative total')
        )
        self.moreSquareViewItem = menu.AppendCheckItem(
            ID_MORE_SQUARE, _('&Hierarchic Squares'),
            _('Toggle hierarchic squares in the square-map view')
        )

        # This stuff isn't really all that useful for profiling,
        # it's more about how to generate graphics to describe profiling...
        self.deeperViewItem = menu.Append(
            ID_DEEPER_VIEW, _('&Deeper'), _('View deeper squaremap views')
        )
        self.shallowerViewItem = menu.Append(
            ID_SHALLOWER_VIEW, _('&Shallower'), _(
                'View shallower squaremap views')
        )
#        wx.ToolTip.Enable(True)
        menubar.Append(menu, _('&View'))

        self.viewTypeMenu = wx.Menu()
        menubar.Append(self.viewTypeMenu, _('View &Type'))

        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, lambda evt: self.Close(True), id=ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnOpenFile, id=ID_OPEN)

        self.Bind(wx.EVT_MENU, self.OnPercentageView, id=ID_PERCENTAGE_VIEW)
        self.Bind(wx.EVT_MENU, self.OnUpView, id=ID_UP_VIEW)
        self.Bind(wx.EVT_MENU, self.OnDeeperView, id=ID_DEEPER_VIEW)
        self.Bind(wx.EVT_MENU, self.OnShallowerView, id=ID_SHALLOWER_VIEW)
        self.Bind(wx.EVT_MENU, self.OnRootView, id=ID_ROOT_VIEW)
        self.Bind(wx.EVT_MENU, self.OnBackView, id=ID_BACK_VIEW)
        self.Bind(wx.EVT_MENU, self.OnMoreSquareToggle, id=ID_MORE_SQUARE)

    def LoadRSRIcon(self):
        try:
            from snakerunner.resources import rsricon_png
            return getIcon(rsricon_png.data)
        except Exception:
            return None

    sourceCodeControl = None

    def CreateSourceWindow(self, tabs):
        """Create our source-view window for tabs"""
        if self.sourceCodeControl is None:
            self.sourceCodeControl = wx.py.editwindow.EditWindow(
                self.tabs, -1
            )
            self.sourceCodeControl.SetText("")
            self.sourceFileShown = None
            self.sourceCodeControl.setDisplayLineNumbers(True)

    def SetupToolBar(self):
        """Create the toolbar for common actions"""
        tb = self.CreateToolBar(self.TBFLAGS)
        tsize = (24, 24)
        tb.ToolBitmapSize = tsize
        open_bmp = wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR,
                                            tsize)
        tb.AddTool(ID_OPEN, "Open", open_bmp, wx.NullBitmap,
                   shortHelp="Open",
                   longHelp="Open a (c)Profile trace file")
        if not osx:
            tb.AddSeparator()
#        self.Bind(wx.EVT_TOOL, self.OnOpenFile, id=ID_OPEN)
        self.rootViewTool = tb.AddTool(
            ID_ROOT_VIEW, _("Root View"),
            wx.ArtProvider.GetBitmap(wx.ART_GO_HOME, wx.ART_TOOLBAR, tsize),
            shortHelp=_(
                "Display the root of the current view tree (home view)")
        )
        self.rootViewTool = tb.AddTool(
            ID_BACK_VIEW, _("Back"),
            wx.ArtProvider.GetBitmap(wx.ART_GO_BACK, wx.ART_TOOLBAR, tsize),
            shortHelp=_(
                "Back to the previously activated node in the call tree")
        )
        self.upViewTool = tb.AddTool(
            ID_UP_VIEW, _("Up"),
            wx.ArtProvider.GetBitmap(wx.ART_GO_UP, wx.ART_TOOLBAR, tsize),
            shortHelp=_(
                "Go one level up the call tree (highest-percentage parent)")
        )
        if not osx:
            tb.AddSeparator()
        # TODO: figure out why the control is sizing the label incorrectly on Linux
        self.percentageViewTool = wx.CheckBox(tb, -1, _("Percent    "))
        self.percentageViewTool.SetToolTip(wx.ToolTip(
            _("Toggle display of percentages in list views")))
        tb.AddControl(self.percentageViewTool)
        self.percentageViewTool.Bind(wx.EVT_CHECKBOX, self.OnPercentageView,
                                     id=self.percentageViewTool.GetId())

        self.viewTypeTool = wx.Choice(
            tb, -1, choices=getattr(self.loader, 'ROOTS', []))
        self.viewTypeTool.SetToolTip(wx.ToolTip(
            _("Switch between different hierarchic views of the data")))
        self.viewTypeTool.Bind(wx.EVT_CHOICE, self.OnViewTypeTool,
                               id=self.viewTypeTool.GetId())
        tb.AddControl(self.viewTypeTool)
        tb.Realize()

    def OnViewTypeTool(self, event):
        """When the user changes the selection, make that our selection"""
        new = self.viewTypeTool.GetStringSelection()
        if new != self.viewType:
            self.viewType = new
            self.OnRootView(event)

    def ConfigureViewTypeChoices(self, event=None):
        """Configure the set of View types in the toolbar (and menus)"""
        self.viewTypeTool.SetItems(getattr(self.loader, 'ROOTS', []))
        if self.loader and self.viewType in self.loader.ROOTS:
            self.viewTypeTool.SetSelection(
                self.loader.ROOTS.index(self.viewType))

        # configure the menu with the available choices...
        def chooser(typ):
            def Callback(event):
                if typ != self.viewType:
                    self.viewType = typ
                    self.OnRootView(event)
            return Callback
        # Clear all previous items
        for item in self.viewTypeMenu.GetMenuItems():
            self.viewTypeMenu.DestroyItem(item)
        if self.loader and self.loader.ROOTS:
            for root in self.loader.ROOTS:
                item = wx.MenuItem(
                    self.viewTypeMenu, -1, root.title(),
                    _("View hierarchy by %(name)s") % {
                        'name': root.title(),
                    },
                    kind=wx.ITEM_RADIO,
                )
                self.viewTypeMenu.Append(item)
                item.Check(root == self.viewType)
                self.Bind(wx.EVT_MENU, chooser(root), id=item.GetId())

    def OnOpenFile(self, event):
        """Request to open a new profile file"""
        dialog = wx.FileDialog(self, style=wx.FD_OPEN | wx.FD_MULTIPLE)
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            if self.loader:
                # we've already got a displayed data-set, open new window...
                frame = MainFrame()
                frame.Show(True)
                frame.load(*paths)
            else:
                self.load(*paths)

    def OnShallowerView(self, event):
        if not self.squareMap.max_depth:
            new_depth = self.squareMap.max_depth_seen or 0 - 1
        else:
            new_depth = self.squareMap.max_depth - 1
        self.squareMap.max_depth = max((1, new_depth))
        self.squareMap.Refresh()

    def OnDeeperView(self, event):
        if not self.squareMap.max_depth:
            new_depth = 1
        else:
            new_depth = self.squareMap.max_depth + 1
        self.squareMap.max_depth = max((self.squareMap.max_depth_seen or 0,
                                        new_depth))
        self.squareMap.Refresh()

    def OnPackageView(self, event):
        self.SetPackageView(not self.directoryView)

    def SetPackageView(self, directoryView):
        """Set whether to use directory/package based view"""
        self.directoryView = not self.directoryView
        self.packageMenuItem.Check(self.directoryView)
        self.packageViewTool.SetValue(self.directoryView)
        if self.loader:
            self.SetModel(self.loader)
        self.RecordHistory()

    def OnPercentageView(self, event):
        """Handle percentage-view event from menu/toolbar"""
        self.SetPercentageView(not self.percentageView)

    def SetPercentageView(self, percentageView):
        """Set whether to display percentage or absolute values"""
        self.percentageView = percentageView
        self.percentageMenuItem.Check(self.percentageView)
        self.percentageViewTool.SetValue(self.percentageView)
        total = self.adapter.value(self.loader.get_root(self.viewType))
        for control in self.ProfileListControls:
            control.SetPercentage(self.percentageView, total)
        self.adapter.SetPercentage(self.percentageView, total)

    def OnUpView(self, event):
        """Request to move up the hierarchy to highest-weight parent"""
        node = self.activated_node
        parents = []
        selected_parent = None

        if node:
            if hasattr(self.adapter, 'best_parent'):
                selected_parent = self.adapter.best_parent(node)
            else:
                parents = self.adapter.parents(node)
            if parents:
                if not selected_parent:
                    parents.sort(key=lambda a: self.adapter.value(node, a))
                    selected_parent = parents[-1]

                class event:
                    node = selected_parent
                self.OnNodeActivated(event)
            else:
                self.SetStatusText(_('No parents for the currently selected node: %(node_name)s')
                                   % dict(node_name=self.adapter.label(node)))
        else:
            self.SetStatusText(_('No currently selected node'))

    def OnBackView(self, event):
        """Request to move backward in the history"""
        self.historyIndex -= 1
        try:
            self.RestoreHistory(self.history[self.historyIndex])
        except IndexError:
            self.SetStatusText(_('No further history available'))

    def OnRootView(self, event):
        """Reset view to the root of the tree"""
        self.adapter, tree, rows = self.RootNode()
        self.squareMap.SetModel(tree, self.adapter)
        self.RecordHistory()
        self.ConfigureViewTypeChoices()

    def OnNodeActivated(self, event):
        """Double-click or enter on a node in some control..."""
        self.activated_node = self.selected_node = event.node
        self.squareMap.SetModel(event.node, self.adapter)
        self.squareMap.SetSelected(event.node)
        if self.SourceShowFile(event.node):
            if hasattr(event.node, 'lineno'):
                self.sourceCodeControl.GotoLine(event.node.lineno)
        self.RecordHistory()

    def SourceShowFile(self, node):
        """Show the given file in the source-code view (attempt it anyway)"""
        filename = self.adapter.filename(node)
        if filename and self.sourceFileShown != filename:
            try:
                data = open(filename).read()
            except Exception:
                # TODO: load from zips/eggs? What about .pyc issues?
                return None
            else:
                # self.sourceCodeControl.setText(data)
                self.sourceCodeControl.ClearAll()
                self.sourceCodeControl.AppendText(data)
        return filename

    def OnSquareHighlightedMap(self, event):
        self.SetStatusText(self.adapter.label(event.node))
        self.listControl.SetIndicated(event.node)
        text = self.squareMap.adapter.label(event.node)
        self.squareMap.SetToolTip(text)
        self.SetStatusText(text)

    def OnSquareHighlightedList(self, event):
        self.SetStatusText(self.adapter.label(event.node))
        self.squareMap.SetHighlight(event.node, propagate=False)

    def OnSquareSelectedList(self, event):
        self.SetStatusText(self.adapter.label(event.node))
        self.squareMap.SetSelected(event.node)
        self.OnSquareSelected(event)
        self.RecordHistory()

    def OnSquareSelectedMap(self, event):
        self.listControl.SetSelected(event.node)
        self.OnSquareSelected(event)
        self.RecordHistory()

    def OnSquareSelected(self, event):
        """Update all views to show selection children/parents"""
        self.selected_node = event.node
        self.calleeListControl.integrateRecords(
            self.adapter.children(event.node))
        self.callerListControl.integrateRecords(
            self.adapter.parents(event.node))
        # self.allCalleeListControl.integrateRecords(event.node.descendants())
        # self.allCallerListControl.integrateRecords(event.node.ancestors())

    def OnMoreSquareToggle(self, event):
        """Toggle the more-square view (better looking, but more likely to filter records)"""
        self.squareMap.square_style = not self.squareMap.square_style
        self.squareMap.Refresh()
        self.moreSquareViewItem.Check(self.squareMap.square_style)

    restoringHistory = False

    def RecordHistory(self):
        """Add the given node to the history-set"""
        if not self.restoringHistory:
            record = self.activated_node
            if self.historyIndex < -1:
                try:
                    del self.history[self.historyIndex+1:]
                except AttributeError:
                    pass
            if (not self.history) or record != self.history[-1]:
                self.history.append(record)
            del self.history[:-200]
            self.historyIndex = -1

    def RestoreHistory(self, record):
        self.restoringHistory = True
        try:
            activated = record

            class activated_event:
                node = activated

            if activated:
                self.OnNodeActivated(activated_event)
                self.squareMap.SetSelected(activated_event.node)
                self.listControl.SetSelected(activated_event.node)
        finally:
            self.restoringHistory = False

    def load(self, *filenames):
        """Load our dataset (iteratively)"""
        try:
            self.loader = pstatsloader.PStatsLoader(*filenames)
            self.ConfigureViewTypeChoices()
            self.SetModel(self.loader)
            self.viewType = self.loader.ROOTS[0]
            self.SetTitle(_("Run Snake Run: %(filenames)s")
                          % {'filenames': ', '.join(filenames)[:120]})
        except (IOError, OSError, ValueError, MemoryError) as err:
            self.SetStatusText(
                _('Failure during load of %(filenames)s: %(err)s'
                  ) % dict(
                    filenames=" ".join([repr(x) for x in filenames]),
                    err=err
                ))

    def SetModel(self, loader):
        """Set our overall model (a loader object) and populate sub-controls"""
        self.loader = loader
        self.adapter, tree, rows = self.RootNode()
        self.listControl.integrateRecords(list(rows.values()))
        self.activated_node = tree
        self.squareMap.SetModel(tree, self.adapter)
        self.RecordHistory()

    def RootNode(self):
        """Return our current root node and appropriate adapter for it"""
        tree = self.loader.get_root(self.viewType)
        adapter = self.loader.get_adapter(self.viewType)
        rows = self.loader.get_rows(self.viewType)

        adapter.SetPercentage(self.percentageView, adapter.value(tree))

        return adapter, tree, rows

    def SaveState(self, config_parser):
        """Retrieve window state to be restored on the next run..."""
        if not config_parser.has_section('window'):
            config_parser.add_section('window')
        if self.IsMaximized():
            config_parser.set('window', 'maximized', str(True))
        else:
            config_parser.set('window', 'maximized', str(False))
        size = self.GetSize()
        position = self.GetPosition()
        config_parser.set('window', 'width', str(size[0]))
        config_parser.set('window', 'height', str(size[1]))
        config_parser.set('window', 'x', str(position[0]))
        config_parser.set('window', 'y', str(position[1]))

        for control in self.ProfileListControls:
            control.SaveState(config_parser)

        return config_parser

    def LoadState(self, config_parser):
        """Set our window state from the given config_parser instance"""
        if not config_parser:
            return
        if (
            not config_parser.has_section('window') or (
                config_parser.has_option('window', 'maximized') and
                config_parser.getboolean('window', 'maximized')
            )
        ):
            self.Maximize(True)
        try:
            width, height, x, y = [
                config_parser.getint('window', key)
                for key in ['width', 'height', 'x', 'y']
            ]
            self.SetPosition((x, y))
            self.SetSize((width, height))
        except configparser.NoSectionError:
            # the file isn't written yet, so don't even warn...
            pass
        except Exception:
            # this is just convenience, if it breaks in *any* way, ignore it...
            log.error(
                "Unable to load window preferences, ignoring: %s", traceback.format_exc()
            )

        try:
            font_size = config_parser.getint('window', 'font_size')
        except Exception:
            pass  # use the default, by default
        else:
            font = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(font_size)
            for ctrl in self.ProfileListControls:
                ctrl.SetFont(font)

        for control in self.ProfileListControls:
            control.LoadState(config_parser)

        self.config = config_parser
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

    def OnCloseWindow(self, event=None):
        try:
            self.SaveState(self.config)
            config = config_file()
            temp = config + '~'
            self.config.write(open(temp, 'w'))
            os.rename(temp, config)
        except Exception:
            log.error("Unable to write window preferences, ignoring: %s",
                      traceback.format_exc())
        self.Destroy()


class RunSnakeRunApp(wx.App):
    """Basic application for holding the viewing Frame"""
    # handler = wx.PNGHandler()

    def OnInit(self):
        """Initialise the application"""
        # wx.Image.AddHandler(self.handler)
        frame = MainFrame(config_parser=load_config())
        frame.Show(True)
        self.SetTopWindow(frame)
        if sys.argv[1:]:
            wx.CallAfter(frame.load, *sys.argv[1:])
        return True


def getIcon(data):
    """Return the data from the resource as a wxIcon"""
    import io
    stream = io.StringIO(data)
    image = wx.Image(stream)
    icon = wx.Icon()
    icon.CopyFromBitmap(wx.Bitmap(image))
    return icon


def config_directory():
    directory = Path.home() / '.config' / 'Snakerunner'
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory


def config_file():
    directory = config_directory()
    return os.path.join(directory, 'runsnake.conf')


def load_config():
    config = configparser.ConfigParser()
    filename = config_file()
    if os.path.exists(filename):
        config.read(filename)
    return config


def main():
    """Mainloop for the application"""
    logging.basicConfig(level=logging.INFO)
    app = RunSnakeRunApp(0)
    app.MainLoop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
