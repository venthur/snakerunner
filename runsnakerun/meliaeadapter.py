#! /usr/bin/env python
"""Module to load meliae memory-profile dumps

Trees:

    * has-a
        * module root 
        * each held reference contributes a weighted cost to the parent 
        * hierarchy of held objects, so globals, classes, functions, and their children
        * held modules do not contribute to cost
        
        * module 
            * instance-tree

Planned:

    * is-a
        * class/type root 
            * instances contribute to their type 
                * summary-by-type 
            

"""
import wx, sys, os, logging
import wx.lib.newevent
log = logging.getLogger( __name__ )
import sys
from squaremap import squaremap
from runsnakerun import meliaeloader

RANKS = [
    (1024*1024*1024,'%0.1fGB'),
    (1024*1024,'%0.1fMB'),
    (1024,'%0.1fKB'),
    (0,'%iB'),
]

def mb( value ):
    for (unit,format) in RANKS:
        if abs(value) >= unit * 2:
            return format%( value / float (unit or 1))
    raise ValueError( "Number where abs(x) is not >= 0?: %s"%(value,))

class MeliaeAdapter( squaremap.DefaultAdapter ):
    """Default adapter class for adapting node-trees to SquareMap API"""
    def children( self, node ):
        """Retrieve the set of nodes which are children of this node"""
        return node['children']
    def value( self, node, parent=None ):
        """Return value used to compare size of this node"""
        # this is the *weighted* size/contribution of the node 
        result = int(node['totsize']/float( len(node.get('parents',())) or 1))
        return result 
    def label( self, node ):
        """Return textual description of this node"""
        return ":".join([
            n for n in [
                node.get(k) for k in ['type','name','value','module']
            ] + [mb(node['totsize'])] if n 
        ])
    def overall( self, node ):
        return node['totsize']
    def empty( self, node ):
        """Calculate overall size of the node including children and empty space"""
        return node['size']/float(node['totsize'])
    def parents( self, node ):
        """Retrieve/calculate the set of parents for the given node"""
        return node.get('parents',[])

    color_mapping = None
    def background_color(self, node, depth):
        """Create a (unique-ish) background color for each node"""
        if self.color_mapping is None:
            self.color_mapping = {}
        if node['type'] == 'type':
            key = node['name']
        else:
            key = node['type']
        color = self.color_mapping.get(key)
        if color is None:
            depth = len(self.color_mapping)
            red = (depth * 10) % 255
            green = 200 - ((depth * 5) % 200)
            blue = (depth * 25) % 200
            self.color_mapping[key] = color = wx.Colour(red, green, blue)
        return color

class TestApp(wx.App):
    """Basic application for holding the viewing Frame"""
    def OnInit(self):
        """Initialise the application"""
        wx.InitAllImageHandlers()
        self.frame = frame = wx.Frame( None,
        )
        frame.CreateStatusBar()

        model = model = self.get_model( sys.argv[1])
        self.sq = squaremap.SquareMap( frame, model=model, adapter = MeliaeAdapter())
        squaremap.EVT_SQUARE_HIGHLIGHTED( self.sq, self.OnSquareSelected )
        frame.Show(True)
        self.SetTopWindow(frame)
        return True
    def get_model( self, path ):
        return meliaeloader.load( path )
    def OnSquareSelected( self, event ):
        text = self.sq.adapter.label( event.node )
        self.frame.SetToolTipString( text )

usage = 'meliaeloader.py somefile'

def main():
    """Mainloop for the application"""
    if not sys.argv[1:]:
        print usage
    else:
        app = TestApp(0)
        app.MainLoop()

if __name__ == "__main__":
    main()