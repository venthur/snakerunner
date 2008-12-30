#! /usr/bin/env python
import wx, sys, os
import  wx
import  wx.lib.newevent

SquareSelectionEvent, EVT_SQUARE_SELECTED = wx.lib.newevent.NewEvent()

class SquareMap( wx.Panel ):
    """Construct a nested-box trees structure view"""
    selected = None
    def __init__( 
        self,  parent=None, id=-1, pos=wx.DefaultPosition, 
        size=wx.DefaultSize, style=wx.TAB_TRAVERSAL|wx.NO_BORDER|wx.FULL_REPAINT_ON_RESIZE, 
        name='SquareMap', model = None,
    ):
        super( SquareMap, self ).__init__(
            parent, id, pos, size, style, name
        )
        self.model = model
        self.Bind( wx.EVT_PAINT, self.OnDraw )
        self.Bind( wx.EVT_MOTION, self.OnMouse )
        self.hot_map = []
#		self.Bind( wx.EVT_SIZE, self.OnResize )

    def OnMouse( self, event ):
        """Handle mouse-move event by selecting a given element"""
        node = self._OnMouse( event.GetPosition(), self.hot_map )
        if node != self.selected:
            self.Refresh()
        self.selected = node
        if node:
            wx.PostEvent( self, SquareSelectionEvent( node=node, point=event.GetPosition(), map=self ) )
    def _OnMouse( self, point, hot_map ):
        for rect,node,children in hot_map:
            if rect.Contains( point ):
                child = self._OnMouse( point, children )
                if child:
                    return child 
                return node
        return None

    def setModel( self, model ):
        self.model = model
        self.Refresh()
    def OnDraw( self, event ):
        dc = wx.PaintDC( self )
        self.hot_map = []
        if self.model:
            # draw the root box...
            color = wx.Color( 128,128,128 )
            brush = wx.Brush( color  )
            dc.SetBackground( brush )
            dc.Clear()
            w, h = dc.GetSize()
            self.drawBox( dc, self.model, 0,0,w,h, hot_map = self.hot_map )
    SCALE_CHILDREN = .95
    PADDING = 4
    def drawBox( self, dc, node, x,y,w,h, hot_map, depth=0 ):
        """Draw a model-node's box and all children nodes"""
        if node is self.selected:
            color = wx.Color( (depth * 5)%255, (255-(depth * 5))%255, 0 )
        else:
            color = wx.Color( (depth * 10)%255, (255-(depth * 10))%255, 255 )
        brush = wx.Brush( color  )
        dc.SetBrush( brush )
        dc.DrawRectangle( x,y,w,h )
#        dc.SetClippingRegion( x,y, w, h )
#        dc.DrawText( node.path, x,y,  )
#        dc.DestroyClippingRegion()
        children_hot_map = []
        hot_map.append( (wx.Rect( int(x),int(y),int(w),int(h)), node, children_hot_map ) )
        x += self.PADDING
        y += self.PADDING*5
        w -= self.PADDING*2
        h -= self.PADDING*6
        
        empty = self.empty( node )
        if empty:
            # is a fraction of the space which is empty...
            h = h * (1.0-empty)
        
        if w >1 and h> 1:
            children = self.children( node )
            if children:
                self.layout_children( dc, children, node, x,y,w,h, children_hot_map, depth+1 )
    def layout_children( self, dc, children, parent, x,y,w,h, hot_map, depth=0 ):
        """Layout the set of children in the given rectangle"""
        nodes = [ (self.value(node,parent),node) for node in children ]
        nodes.sort()
        total = self.children_sum( children,parent )
        if total:
            (firstSize,firstNode) = nodes[-1]
            rest = [node for (size,node) in nodes[:-1]]
            fraction = firstSize/float(total)
            if w >= h:
                new_w = int(w*fraction)
                if new_w:
                    self.drawBox( dc, firstNode, x,y, new_w, h, hot_map, depth+1 )
                w = w-new_w
                x += new_w 
            else:
                new_h = int(h*fraction)
                if new_h:
                    self.drawBox( dc, firstNode, x,y, w, new_h, hot_map, depth + 1 )
                h = h-new_h
                y += new_h 
            if rest:
                self.layout_children( dc, rest, parent, x,y,w,h, hot_map, depth )
    def children( self, node ):
        return node.children
    def value( self, node, parent=None ):
        return node.size
    def label( self, node ):
        return node.path
    def overall( self, node ):
        return sum( [self.value(value,node) for value in node.children] )
    def children_sum( self, children,node ):
        return sum( [self.value(value,node) for value in children] )
    def empty( self, node ):
        overall = self.overall( node )
        if overall:
            return (overall - self.children_sum( node.children, node))/float(overall)
        return 0

class TestApp(wx.App):
    """Basic application for holding the viewing Frame"""
    def OnInit(self):
        """Initialise the application"""
        wx.InitAllImageHandlers()
        self.frame = frame = wx.Frame( None,
        )
        frame.CreateStatusBar()
        
        model = model = self.get_model( sys.argv[1]) 
        self.sq = SquareMap( frame, model=model)
        EVT_SQUARE_SELECTED( self.sq, self.OnSquareSelected )
        frame.Show(True)
        self.SetTopWindow(frame)
        return True
    def get_model( self, path ):
        nodes = []
        for f in os.listdir( path ):
            full = os.path.join( path,f )
            if not os.path.islink( full ):
                if os.path.isfile( full ):
                    nodes.append( Node( full, os.stat( full ).st_size, () ) )
                elif os.path.isdir( full ):
                    nodes.append( self.get_model( full ))
        return Node( path, sum([x.size for x in nodes]), nodes )
    def OnSquareSelected( self, event ):
        self.frame.SetStatusText( self.sq.label( event.node ) )

class Node( object ):
    def __init__( self, path, size, children ):
        self.path = path
        self.size = size
        self.children = children 
    def __repr__( self ):
        return '%s( %r, %r, %r )'%( self.__class__.__name__, self.path, self.size, self.children )
        

usage = 'squaremap.py somedirectory'
        
def main():
    """Mainloop for the application"""
    if not sys.argv[1:]:
        print usage
    else:
        app = TestApp(0)
        app.MainLoop()

if __name__ == "__main__":
    main()
